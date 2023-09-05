import pandas as pd
from datetime import timedelta
from pyomo.environ import SolverFactory
from pyomo.core import *
from utils import data_input, data_output
from utils.data_input import (
    InputData,
    BatterySpecs,
    Bulk,
    ControlMethod as CM,
)
from pyomo.opt import SolverStatus, TerminationCondition
from utils import data_output
import pyomo.kernel as pmo


# Constraints


def power_balance(model, t):
    return (
        model.P_load[t]
        + sum(model.P_ch_bat[n, t] for n in model.N)
        + model.P_exp[t] * model.x_exp[t]
        == sum(model.P_dis_bat[n, t] for n in model.N)
        + model.P_imp[t] * model.x_imp[t]
        + model.P_PV[t]
    )


def bat_charging(model, n, t):
    return model.SoC_bat[n, t + model.dT] == model.SoC_bat[n, t] + model.dT.seconds * (
        (model.P_ch_bat[n, t] / model.ch_eff_bat[n]) / model.cap_bat[n]
    ) - model.dT.seconds * (
        (model.P_dis_bat[n, t] * model.dis_eff_bat[n]) / model.cap_bat[n]
    )


def bat_init_SoC(model, n):
    return model.SoC_bat[n, model.start_time] == model.ini_SoC_bat[n]


def bat_max_ch_power(model, n, t):
    return model.P_ch_bat[n, t] <= float(model.P_ch_bat_max[n]) * model.x_ch[n, t]


def bat_max_dis_power(model, n, t):
    return model.P_dis_bat[n, t] <= float(model.P_dis_bat_max[n]) * model.x_dis[n, t]


def bat_min_SoC(model, n, t):
    return float(model.min_SoC_bat[n]) <= model.SoC_bat[n, t]


def bat_max_SoC(model, n, t):
    return model.SoC_bat[n, t] <= model.max_SoC_bat[n]


def import_export_lower_bound(model, t):
    if model.with_imp_exp_lower_b[t]:
        return (
            model.imp_exp_lower_b[t]
            <= model.P_imp[t] * model.x_imp[t] - model.P_exp[t] * model.x_exp[t]
        )
    else:
        return Constraint.Feasible


def import_export_upper_bound(model, t):
    if model.with_imp_exp_upper_b[t]:
        return (
            model.P_imp[t] * model.x_imp[t] - model.P_exp[t] * model.x_exp[t]
            <= model.imp_exp_upper_b[t]
        )
    else:
        return Constraint.Feasible


def bat_final_SoC(model, n):
    if model.final_SoC_bat[n] is not None:
        # Household battery should reach its maximum SoC at the end of the day
        if model.bat_type[n] == "hbes":
            return model.SoC_bat[n, model.day_end] == model.max_SoC_bat[n]
        else:
            return model.SoC_bat[n, model.end_time] == model.final_SoC_bat[n]
    else:
        return Constraint.Feasible


def bulk_energy(model):
    return (
        sum(
            sum(
                (
                    model.P_dis_bat[n, t] * model.dis_eff_bat[n]
                    - (model.P_ch_bat[n, t]) / model.ch_eff_bat[n]
                )
                * model.dT.seconds
                for t in model.T_bulk
            )
            for n in model.N
        )
        == -model.Bulk_Energy[0]
    )


def ch_dis_binary(model, n, t):
    return model.x_ch[n, t] + model.x_dis[n, t] <= 1


def imp_exp_binary(model, t):
    return model.x_imp[t] + model.x_exp[t] <= 1


def deficit_case_1(model, t):
    if model.P_net[t] >= 0:
        return model.P_imp[t] * model.x_imp[t] <= model.P_net[t]
    else:
        return Constraint.Feasible


def deficit_case_2(model, n, t):
    if model.P_net[t] >= 0:
        return model.P_ch_bat[n, t] <= 0
    else:
        return Constraint.Feasible


def surplus_case_1(model, t):
    if model.P_net[t] <= 0:
        return (
            sum((model.P_ch_bat[n, t]) / model.ch_eff_bat[n] for n in model.N)
            <= -model.P_net[t]
        )
    else:
        return Constraint.Feasible


def surplus_case_2(model, t):
    if model.P_net[t] <= 0:
        # Note for the future works: As we seperated P_imp and x_imp from each other, make sure we always use P_imp in all of our constraints.
        # From now on x_imp can be 1 and P_imp can be 0, therefore we MUST use P_imp in the constraints.
        return model.P_imp[t] * model.x_imp[t] <= 0
    else:
        return Constraint.Feasible


def penalty_for_imp(model, t):
    return model.P_imp[t] * model.x_imp[t] <= model.alpha_imp


def penalty_for_exp(model, t):
    return model.P_exp[t] * model.x_exp[t] <= model.alpha_exp


def hbes_avoid_diss(model, n, t):
    if model.bat_type[n] == "hbes":
        return model.P_dis_bat[n, t] <= 0
    else:
        return Constraint.Feasible


def pv_curtailment_constr(model, t):
    if model.pv_curtailment:
        return model.P_PV[t] <= model.P_PV_limit[t]
    else:
        return model.P_PV[t] == model.P_PV_limit[t]


# Objective: Minimize the power exchange with the grid (Minimum interaction with the grid)
def obj_rule(model):
    return (
        sum(
            model.P_exp[t] * model.x_exp[t] + model.P_imp[t] * model.x_imp[t]
            for t in model.T
        )
        + model.alpha_exp
        + model.alpha_imp
    )


def control(data: InputData):

    battery_specs = data_input.input_prep(data.battery_specs)
    
    if data.uc_name == CM.RULE_BASED:
        df_forecasts = data_input.generation_and_load_to_df(
            data.generation_and_load, start=data.uc_start, end=data.uc_end
        )

        imp_exp_limits = data_input.imp_exp_lim_to_df(
            data.import_export_limitation, data.generation_and_load
        )
        if isinstance(battery_specs, list):
            if len(battery_specs) == 1:
                battery_specs = battery_specs[0]
            else:
                raise RuntimeError(
                    "Rule based control can not deal with multiple flex nodes."
                )
        output_df = None
        delta_T = pd.to_timedelta(df_forecasts.P_load_kW.index.freq)
        for time, P_net in df_forecasts.iterrows():
            output = rule_based_logic(P_net, battery_specs, delta_T)
            if output_df is None:
                output_df = pd.DataFrame(columns=output.index, index=df_forecasts.index)
            output_df.loc[time] = output
            battery_specs.initial_SoC = (
                output.bat_energy_Ws / battery_specs.bat_capacity
            )
        if battery_specs.id is not None:
            output_df.rename(
                {"P_bat_kW": f"P_{battery_specs.id}_kW"}, inplace=True, axis=1
            )
            output_df.rename(
                {"SoC_bat": f"SoC_{battery_specs.id}_%"}, inplace=True, axis=1
            )
        else:
            output_df.rename({"P_bat_kW": "P_bat_1_kW"}, inplace=True, axis=1)
            output_df.rename({"SoC_bat": "SoC_bat_1_%"}, inplace=True, axis=1)
        output_df = output_df.drop(["bat_energy_Ws", "import_W", "export_W"], axis=1)

        return output_df, (SolverStatus.ok, TerminationCondition.optimal)
    
    if data.uc_name == CM.REAL_TIME:
        if isinstance(battery_specs, list):
            if len(battery_specs) == 1:
                #battery_specs = battery_specs[0]
                battery_specs_dict = data_input.battery_to_dict(battery_specs)
            else:
                raise RuntimeError(
                    "Near real time control can not deal with multiple flex nodes."
                )
        measurements_request_dict = data_input.measurements_request_to_dict(data.measurements_request)
        output_df = near_real_time_logic(measurements_request_dict, battery_specs_dict)

        return output_df, (SolverStatus.ok, TerminationCondition.optimal)


    if data.uc_name == CM.OPTIMIZER:
        df_forecasts = data_input.generation_and_load_to_df(
            data.generation_and_load, start=data.uc_start, end=data.uc_end
        )

        imp_exp_limits = data_input.imp_exp_lim_to_df(
            data.import_export_limitation, data.generation_and_load
        )
        df_battery_specs = data_input.battery_to_df(battery_specs)
        (
            import_export_profile,
            pv_profile,
            bat_p_supply_profiles,
            bat_soc_supply_profiles,
            imp_exp_upperb,
            imp_exp_lowerb,
            solver_status,
        ) = optimizer_logic(
            df_forecasts,
            df_battery_specs,
            data.day_end,
            data.bulk,
            imp_exp_limits,
            data.generation_and_load.pv_curtailment,
        )
        output_df = data_output.prep_optimizer_output(
            import_export_profile,
            pv_profile,
            bat_p_supply_profiles,
            bat_soc_supply_profiles,
            df_forecasts,
            imp_exp_upperb,
            imp_exp_lowerb,
        )
        return output_df, solver_status
    
def near_real_time_logic(measurements_request_dict: dict, battery_specs_dict: dict):
    output = dict.fromkeys(
        [
            "timestamp",
            "Pbat_kW",
            "bat_Energy_kWh",
            "import",
            "export",
            "Ptei_kW",
            "Expected_Ptei",
        ]
        )
        
    output["timestamp"] = measurements_request_dict["timestamp"]
    # initialize
    output["import"] = 0
    output["export"] = 0
    output["bat_Energy_kWh"] = 0

    output["Pbat_kW"] = -measurements_request_dict["Preq_kW"] + measurements_request_dict["Pnet_meas_kW"]
    output["bat_Energy_kWh"] = battery_specs_dict["initial_Energy_kWh"] - (
        output["Pbat_kW"] * measurements_request_dict["delta_T"]
    )

    # discharging
    if output["Pbat_kW"] > 0:
        act_ptcb = output["Pbat_kW"]
        if abs(output["Pbat_kW"]) < battery_specs_dict["P_dis_max_kW"]:
            pass

        else:
            output["import"] = output["Pbat_kW"] - battery_specs_dict["P_dis_max_kW"]
            output["Pbat_kW"] = battery_specs_dict["P_dis_max_kW"]
            output["bat_Energy_kWh"] = battery_specs_dict["initial_Energy_kWh"] - (
                battery_specs_dict["P_dis_max_kW"] * measurements_request_dict["delta_T"]
            )

        if output["bat_Energy_kWh"] >= battery_specs_dict["min_Energy_kWh"]:
            pass

        else:
            output["import"] = output["import"] + (
                ((battery_specs_dict["min_Energy_kWh"] - output["bat_Energy_kWh"]) / measurements_request_dict["delta_T"])
            )
            output["Pbat_kW"] = act_ptcb - output["import"]
            output["bat_Energy_kWh"] = battery_specs_dict["min_Energy_kWh"]

        output["Pbat_kW"] = float(output["Pbat_kW"])

    # charging
    if output["Pbat_kW"] < 0:
        act_ptcb = output["Pbat_kW"]
        if abs(output["Pbat_kW"]) <= battery_specs_dict["P_ch_max_kW"]:
            output["export"] = 0
            pass
        else:
            output["export"] = abs(output["Pbat_kW"]) - battery_specs_dict["P_ch_max_kW"]
            output["Pbat_kW"] = -battery_specs_dict["P_ch_max_kW"]
            output["bat_Energy_kWh"] = battery_specs_dict["initial_Energy_kWh"] + (
                battery_specs_dict["P_ch_max_kW"] * measurements_request_dict["delta_T"]
            )
        if output["bat_Energy_kWh"] <= battery_specs_dict["max_Energy_kWh"]:
            pass
        else:
            output["export"] = output["export"] + (
                (output["bat_Energy_kWh"] - battery_specs_dict["max_Energy_kWh"]) / measurements_request_dict["delta_T"]
            )
            output["Pbat_kW"] = -(abs(act_ptcb) - (output["export"]))
            output["bat_Energy_kWh"] = battery_specs_dict["max_Energy_kWh"]
        output["Pbat_kW"] = float(output["Pbat_kW"])

    output["Ptei_kW"] = -measurements_request_dict["Pnet_meas_kW"]
    output["Expected_Ptei_kW"] = output["export"] - output["import"]

    # Considering current Pbat_kW
    output["Pbat_kW"] = output["Pbat_kW"] + measurements_request_dict["Pbat_init_kW"]
    if output["Pbat_kW"] < 0:
        if abs(output["Pbat_kW"]) <= battery_specs_dict["P_ch_max_kW"]:
            pass
        else:
            output["Pbat_kW"] = -battery_specs_dict["P_ch_max_kW"]

    else:
        if output["Pbat_kW"] <= battery_specs_dict["P_dis_max_kW"]:
            pass
        else:
            output["Pbat_kW"] = battery_specs_dict["P_dis_max_kW"]

    return output

def rule_based_logic(
    P_load_gen: pd.Series, battery_specs: BatterySpecs, delta_T: timedelta
):
    # initialize
    output_ds = pd.Series(
        index=[
            "P_net_kW",
            "expected_P_net_kW",
            "P_bat_kW",
            "SoC_bat",
            "bat_energy_Ws",
            "import_W",
            "export_W",
        ],
        dtype=float,
    )
    output_ds.import_W = 0
    output_ds.export_W = 0
    output_ds.bat_energy_Ws = 0

    # Convert timedelta to float in terms of seconds
    delta_time_in_sec = delta_T.total_seconds()

    output_ds.P_bat_kW = P_load_gen.P_load_kW - P_load_gen.P_gen_kW

    output_ds.bat_energy_Ws = battery_specs.initial_SoC * battery_specs.bat_capacity - (
        output_ds.P_bat_kW * delta_time_in_sec
    )

    # discharging
    if output_ds.P_bat_kW > 0:
        act_ptcb = output_ds.P_bat_kW
        if abs(output_ds.P_bat_kW) >= battery_specs.P_dis_max_kW:
            output_ds.import_W = output_ds.P_bat_kW - battery_specs.P_dis_max_kW
            output_ds.P_bat_kW = battery_specs.P_dis_max_kW
            output_ds.bat_energy_Ws = (
                battery_specs.initial_SoC * battery_specs.bat_capacity
                - (battery_specs.P_dis_max_kW * delta_time_in_sec)
            )

        if output_ds.bat_energy_Ws < battery_specs.min_SoC * battery_specs.bat_capacity:
            output_ds.import_W = output_ds.import_W + (
                (
                    battery_specs.min_SoC * battery_specs.bat_capacity
                    - output_ds.bat_energy_Ws
                )
                / delta_time_in_sec
            )
            output_ds.P_bat_kW = act_ptcb - output_ds.import_W
            output_ds.bat_energy_Ws = battery_specs.min_SoC * battery_specs.bat_capacity

    # charging
    if output_ds.P_bat_kW < 0:
        act_ptcb = output_ds.P_bat_kW
        if abs(output_ds.P_bat_kW) <= battery_specs.P_ch_max_kW:
            output_ds.export_W = 0
            pass
        else:
            output_ds.export_W = abs(output_ds.P_bat_kW) - battery_specs.P_ch_max_kW
            output_ds.P_bat_kW = -battery_specs.P_ch_max_kW
            output_ds.bat_energy_Ws = (
                battery_specs.initial_SoC * battery_specs.bat_capacity
                + (battery_specs.P_ch_max_kW * delta_time_in_sec)
            )
        if output_ds.bat_energy_Ws > battery_specs.max_SoC * battery_specs.bat_capacity:
            output_ds.export_W = output_ds.export_W + (
                (
                    output_ds.bat_energy_Ws
                    - battery_specs.max_SoC * battery_specs.bat_capacity
                )
                / delta_time_in_sec
            )
            output_ds.P_bat_kW = -(abs(act_ptcb) - (output_ds.export_W))
            output_ds.bat_energy_Ws = battery_specs.max_SoC * battery_specs.bat_capacity
        output_ds.P_bat_kW = float(output_ds.P_bat_kW)

    output_ds.P_net_kW = P_load_gen.P_load_kW - P_load_gen.P_gen_kW
    output_ds.expected_P_net_kW = (output_ds.export_W - output_ds.import_W) / 3600

    output_ds.SoC_bat = (output_ds.bat_energy_Ws / battery_specs.bat_capacity) * 100

    return output_ds


def optimizer_logic(
    P_load_gen: pd.Series,
    df_battery: pd.DataFrame,
    day_end,
    bulk_data: Bulk,
    imp_exp_limits: pd.DataFrame,
    pv_curtailment: Boolean,
) -> tuple[pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, SolverStatus]:
    # Selected optimization solver
    # optimization_solver = SolverFactory("bonmin")
    optimization_solver = SolverFactory("gurobi")
    # optimization_solver = SolverFactory("ipopt")
    # optimization_solver = SolverFactory("scip")
    load = P_load_gen.P_load_kW
    generation = P_load_gen.P_gen_kW
    start_time = load.index[0]
    end_time = load.index[-1]
    delta_T = pd.to_timedelta(load.index.freq)
    # XXX it is a bit weird to that the end time is not the time of the end
    # but the start of the last interval
    opt_horizon = pd.date_range(
        start_time, end_time + delta_T, freq=delta_T, inclusive="left"
    )
    sof_horizon = pd.date_range(
        start_time, end_time + delta_T, freq=delta_T, inclusive="both"
    )
    if bulk_data is not None:
        bulk_horizon = pd.date_range(
            bulk_data.bulk_start, bulk_data.bulk_end, freq=delta_T, inclusive="both"
        )

    considered_load_forecast = load[
        opt_horizon
    ]  # Only the specified time instances in the load forecast will be taken into account
    considered_generation_forecast = generation[
        opt_horizon
    ]  # Only the specified time instances in the generation forecast will be taken into account

    #####################################################################################################
    ##################################       OPTIMIZATION MODEL          #################################
    model = ConcreteModel()

    # Index sets
    # Index set with aggregated battery identifiers
    model.N = list(df_battery.index)
    # Index set with optimization horizon time step identifiers
    # XXX Not sure why generating a tuple here makes a difference but it does
    model.T = tuple(opt_horizon)
    # Index set with battery horizon time step identifiers
    model.T_SoC_bat = tuple(sof_horizon)
    # Index set with bulk horizon time step identifiers
    if bulk_data is not None:
        model.T_bulk = tuple(bulk_horizon)

    # Parameters
    # TimeDelta in one time step
    model.dT = delta_T
    model.start_time = start_time
    model.end_time = end_time
    model.day_end = day_end
    # Import-export limits for every each timestamp enabling the microgrid to go full islanding (if both are zero)
    model.imp_exp_upper_b = imp_exp_limits.upper_bound
    model.imp_exp_lower_b = imp_exp_limits.lower_bound
    model.with_imp_exp_upper_b = imp_exp_limits.with_upper_bound
    model.with_imp_exp_lower_b = imp_exp_limits.with_lower_bound

    # Forecast parameters
    # Total import-export forecast
    model.P_net = considered_load_forecast - considered_generation_forecast
    # Load
    model.P_load = considered_load_forecast
    # Generation limits
    model.P_PV_limit = considered_generation_forecast
    # Battery parameters
    # Type of the battery
    # cbes: comunity battery energy storage, hbes: household battery energy storage
    model.bat_type = df_battery.bat_type
    # Minimum allowable state of charge of the battery n
    model.min_SoC_bat = df_battery.min_SoC
    # Maximum allowable state of charge of the battery n
    model.max_SoC_bat = df_battery.max_SoC
    # State of charge value of battery n at the beginning of the optimization horizon
    model.ini_SoC_bat = df_battery.initial_SoC
    # The value of the final state of charge (if given) to be reached for the battery n at the end of the optimization horizon
    model.final_SoC_bat = df_battery.final_SoC
    # Capacity of the battery n (kWsec)
    model.cap_bat = df_battery.bat_capacity
    # Maximum charging power of the battery n (KW)
    model.P_ch_bat_max = df_battery.P_ch_max_kW
    # Maximum discharging power of the battery n (KW)
    model.P_dis_bat_max = df_battery.P_dis_max_kW
    # Charging efficiency of the battery n
    model.ch_eff_bat = df_battery.ch_efficiency
    # Discharging efficiency of the battery n
    model.dis_eff_bat = df_battery.dis_efficiency
    # Bulk parameters (bulk energy)
    if bulk_data is not None:
        # Bulk energy of battery assets (kWsec)
        model.Bulk_Energy = pd.Series([bulk_data.bulk_energy_kwh]) * 3600
    if pv_curtailment is not None:
        model.pv_curtailment = pv_curtailment
    else:
        model.pv_curtailment = False

    # Variables
    # Power output of PV in timestamp t
    model.P_PV = Var(model.T, within=NonNegativeReals)
    # Power demand of the community in timestamp t
    model.P_dem = Var(model.T, within=NonNegativeReals)
    # PV power feeding the load in timestamp t
    model.P_PV_dem = Var(model.T, within=NonNegativeReals)
    # State of charge of the battery n in timestamp t
    model.SoC_bat = Var(model.N, model.T_SoC_bat, within=NonNegativeReals)
    # Charge power of the battery n in timestamp t
    model.P_ch_bat = Var(model.N, model.T, within=NonNegativeReals)
    # Discharge power of the battery n in timestamp t
    model.P_dis_bat = Var(model.N, model.T, within=NonNegativeReals)
    # Export power to the grid in timestamp t
    model.P_exp = Var(model.T, within=NonNegativeReals)
    # Import power from the grid in timestamp t
    model.P_imp = Var(model.T, within=NonNegativeReals)
    # Penalty variable for import (maximum value of P_imp over time)
    model.alpha_imp = Var(within=NonNegativeReals)
    # Penalty variable for export (maximum value of P_exp over time)
    model.alpha_exp = Var(within=NonNegativeReals)

    # Binary variables
    # Binary variable having 1 if battery n is charged at timestamp t
    model.x_ch = Var(model.N, model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n is discharged at timestamp t
    model.x_dis = Var(model.N, model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n imports power at timestamp t
    model.x_imp = Var(model.T, within=pmo.Binary)
    # Binary variable having 1 if battery n exports power at timestamp t
    model.x_exp = Var(model.T, within=pmo.Binary)

    model.power_balance = Constraint(model.T, rule=power_balance)
    model.bat_charging = Constraint(model.N, model.T, rule=bat_charging)
    model.bat_init_SoC = Constraint(model.N, rule=bat_init_SoC)
    model.bat_final_SoC = Constraint(model.N, rule=bat_final_SoC)
    if bulk_data is not None:
        model.bulk_energy = Constraint(rule=bulk_energy)
    model.bat_max_ch_power = Constraint(model.N, model.T, rule=bat_max_ch_power)
    model.bat_max_dis_power = Constraint(model.N, model.T, rule=bat_max_dis_power)
    model.bat_min_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_min_SoC)
    model.bat_max_SoC = Constraint(model.N, model.T_SoC_bat, rule=bat_max_SoC)
    model.import_export_upper_bound = Constraint(
        model.T, rule=import_export_upper_bound
    )
    model.import_export_lower_bound = Constraint(
        model.T, rule=import_export_lower_bound
    )
    model.ch_dis_binary = Constraint(model.N, model.T, rule=ch_dis_binary)
    model.imp_exp_binary = Constraint(model.T, rule=imp_exp_binary)
    model.penalty_for_imp = Constraint(model.T, rule=penalty_for_imp)
    model.penalty_for_exp = Constraint(model.T, rule=penalty_for_exp)
    model.deficit_case_1 = Constraint(model.T, rule=deficit_case_1)
    model.deficit_case_2 = Constraint(model.N, model.T, rule=deficit_case_2)
    model.surplus_case_1 = Constraint(model.T, rule=surplus_case_1)
    model.surplus_case_2 = Constraint(model.T, rule=surplus_case_2)
    model.hbes_avoid_diss = Constraint(model.N, model.T, rule=hbes_avoid_diss)
    model.pv_curtailment_constr = Constraint(model.T, rule=pv_curtailment_constr)

    model.obj = Objective(rule=obj_rule, sense=minimize)

    #####################################################################################################
    ##################################       OPTIMIZATION MODEL          ################################
    solver = optimization_solver.solve(model).solver
    #####################################################################################################
    ##################################       POST PROCESSING             ################################
    bat_p_supply_profiles = pd.DataFrame(index=model.T, columns=df_battery.index)
    import_export_profile = pd.DataFrame(index=model.T, columns=[""])
    import_limits = pd.DataFrame(index=model.T, columns=[""])
    export_limits = pd.DataFrame(index=model.T, columns=[""])
    bat_ch = pd.DataFrame(index=model.T, columns=df_battery.index)
    bat_dis = pd.DataFrame(index=model.T, columns=df_battery.index)
    bat_soc_supply_profiles = pd.DataFrame(
        index=model.T_SoC_bat, columns=df_battery.index
    )

    for n in model.N:
        for t in model.T:
            bat_p_supply_profiles.loc[t, n] = value(
                model.x_dis[n, t] * model.P_dis_bat[n, t] / model.dis_eff_bat[n]
                - model.x_ch[n, t] * model.P_ch_bat[n, t] * model.ch_eff_bat[n]
            )

    for t in model.T:
        import_export_profile.loc[t] = value(
            model.x_imp[t] * model.P_imp[t] - model.x_exp[t] * model.P_exp[t]
        )
        #import_export_profile.loc[t] = model.imp_exp_upper_b[t]

    for col in df_battery.index:
        bat_ch[col] = model.P_ch_bat[col, :]()
        bat_dis[col] = model.P_dis_bat[col, :]()
        bat_soc_supply_profiles[col] = model.SoC_bat[col, :]()

    pv_profile = pd.Series(model.P_PV[:](), index=model.T)

    return (
        import_export_profile,
        pv_profile,
        bat_p_supply_profiles,
        bat_soc_supply_profiles,
        model.imp_exp_upper_b,
        model.imp_exp_lower_b,
        (solver.status, solver.termination_condition),
    )
