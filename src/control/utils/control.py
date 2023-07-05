import pandas as pd
from datetime import timedelta
from pyomo.environ import SolverFactory
from pyomo.core import *
from utils import data_input, data_output
from utils.data_input import (
    InputData,
    BatterySpecs,
    Bulk,
    ImportExportLimitation,
    ControlMethod as CM,
)
from pyomo.opt import SolverStatus, TerminationCondition
from utils import data_output
import pyomo.kernel as pmo


def power_balance(model, t):
    return (
        model.P_tie[t] + sum(model.P_ch_bat[n, t] for n in model.N) + model.P_exp[t]
        == sum(model.P_dis_bat[n, t] for n in model.N) + model.P_imp[t]
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


def exp_limit(model, t):
    if model.with_export_limit[t]:
        return model.P_exp[t] <= model.export_limit[t] * model.x_exp[t]
    else:
        return model.P_exp[t] <= 100000000000 * model.x_exp[t]

def imp_limit(model, t):
    if model.with_import_limit[t]:
        return model.P_imp[t] <= model.import_limit[t] * model.x_imp[t]
    else:
        return model.P_imp[t] <= 100000000000 * model.x_imp[t]


def bat_final_SoC(model, n):
    if model.with_final_SoC[n]:
        return model.SoC_bat[n, model.end_time] == model.final_SoC_bat[n]
    # Household battery should reach its maximum SoC at the end of the day
    elif model.bat_type[n] == "hbes":
        return model.SoC_bat[n, model.day_end] == model.max_SoC_bat[n]
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


def pos_tot_imp_exp(model, t):
    if model.P_tie[t] >= 0:
        return model.P_imp[t] - model.P_exp[t] <= model.P_tie[t]
    else:
        return Constraint.Feasible


def neg_tot_imp_exp1(model, t):
    if model.P_tie[t] <= 0:
        return (
            sum((model.P_ch_bat[n, t]) / model.ch_eff_bat[n] for n in model.N)
            <= -model.P_tie[t]
        )
    else:
        return Constraint.Feasible


def neg_tot_imp_exp2(model, t):
    if model.P_tie[t] <= 0:
        # Note for the future works: As we seperated P_imp and x_imp from each other, make sure we always use P_imp in all of our constraints.
        # From now on x_imp can be 1 and P_imp can be 0, therefore we MUST use P_imp in the constraints.
        return model.P_imp[t] <= 0
    else:
        return Constraint.Feasible


def penalty_for_imp(model, t):
    return model.P_imp[t] <= model.alpha_imp


def penalty_for_exp(model, t):
    return model.P_exp[t] <= model.alpha_exp


def hbes_avoid_diss(model, n, t):
    if model.bat_type[n] == "hbes":
        return model.P_dis_bat[n, t] <= 0
    else:
        return Constraint.Feasible


# Objective: Minimize the power exchange with the grid (Minimum interaction with the grid)
def obj_rule(model):
    return (
        sum(model.P_exp[t] + model.P_imp[t] for t in model.T)
        + model.alpha_exp
        + model.alpha_imp
    )


def control(data: InputData):
    battery_specs = data_input.input_prep(data.battery_specs)
    df_forecasts = data_input.generation_and_load_to_df(
        data.generation_and_load, start=data.uc_start, end=data.uc_end
    )
    '''
    imp_exp_limits = data_input.imp_exp_to_df(
        data.import_export_limitation, start=data.uc_start, end=data.uc_end
    )
    '''
    imp_exp_limits = data_input.imp_exp_lim_to_df(data.import_export_limitation, data.generation_and_load)
    print(imp_exp_limits)
    if data.uc_name == CM.RULE_BASED:
        if isinstance(battery_specs, list):
            if len(battery_specs) == 1:
                battery_specs = battery_specs[0]
            else:
                raise RuntimeError(
                    "Rulebased control can not deal with multiple flex nodes"
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

    if data.uc_name == CM.OPTIMIZER:
        df_battery_specs = data_input.battery_to_df(battery_specs)
        (
            import_profile,
            pv_profile,
            bat_profiles,
            sof_profiles,
            solver_status,
        ) = optimizer_logic(
            df_forecasts.P_load_kW,
            df_battery_specs,
            data.day_end,
            data.bulk,
            imp_exp_limits,
        )
        output_df = data_output.prep_optimizer_output(
            import_profile,
            bat_profiles,
            sof_profiles,
            df_forecasts,
            df_battery_specs,
        )
        return output_df, solver_status


def rule_based_logic(P_net: pd.Series, battery_specs: BatterySpecs, delta_T: timedelta):
    # initialize
    output_ds = pd.Series(
        index=[
            "P_tie_kW",
            "expected_P_tie_kW",
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

    # output_ds.P_bat_kW = P_net.P_req_kw + P_net.P_net_kW
    # TODO: ask this to amir
    output_ds.P_bat_kW = P_net.P_load_kW - P_net.P_gen_kW

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

    output_ds.P_tie_kW = -P_net.P_load_kW + P_net.P_gen_kW
    output_ds.expected_P_tie_kW = (output_ds.export_W - output_ds.import_W) / 3600

    output_ds.SoC_bat = (output_ds.bat_energy_Ws / battery_specs.bat_capacity) * 100

    return output_ds


def optimizer_logic(
    ions: pd.Series,
    df_battery: pd.DataFrame,
    day_end,
    bulk_data: Bulk,
    imp_exp_limits: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, SolverStatus]:
    # Selected optimization solver
    # optimization_solver = SolverFactory("bonmin")
    optimization_solver = SolverFactory("gurobi")
    # optimization_solver = SolverFactory("ipopt")
    # optimization_solver = SolverFactory("scip")
    start_time = ions.index[0]
    end_time = ions.index[-1]
    delta_T = pd.to_timedelta(ions.index.freq)
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

    considered_ions_forecast = ions[
        opt_horizon
    ]  # Only the specified time instances in the ion forecast will be taken into account

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
    model.import_limit = imp_exp_limits.import_limit
    model.export_limit = imp_exp_limits.export_limit
    model.with_import_limit = imp_exp_limits.with_import_limit
    model.with_export_limit = imp_exp_limits.with_export_limit

    # Forecast parameters
    # Total import-export forecast
    model.P_tie = considered_ions_forecast
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
    # Boolean
    # True: There is a final state of charge to be reached for the battery n at the end of the optimization horizon
    # False: There is no final state of charge to be reached for the battery n at the end of the optimization horizon
    model.with_final_SoC = df_battery.with_final_SoC
    if model.with_final_SoC.any():
        # The value of the final state of charge to be reached for the battery n at the end of the optimization horizon
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
    model.exp_limit = Constraint(model.T, rule=exp_limit)
    model.imp_limit = Constraint(model.T, rule=imp_limit)
    model.ch_dis_binary = Constraint(model.N, model.T, rule=ch_dis_binary)
    model.imp_exp_binary = Constraint(model.T, rule=imp_exp_binary)
    model.penalty_for_imp = Constraint(model.T, rule=penalty_for_imp)
    model.penalty_for_exp = Constraint(model.T, rule=penalty_for_exp)
    model.pos_tot_imp_exp = Constraint(model.T, rule=pos_tot_imp_exp)
    model.neg_tot_imp_exp1 = Constraint(model.T, rule=neg_tot_imp_exp1)
    model.neg_tot_imp_exp2 = Constraint(model.T, rule=neg_tot_imp_exp2)
    model.hbes_avoid_diss = Constraint(model.N, model.T, rule=hbes_avoid_diss)

    model.obj = Objective(rule=obj_rule, sense=minimize)

    #####################################################################################################
    ##################################       OPTIMIZATION MODEL          ################################
    solver = optimization_solver.solve(model).solver
    #model.pprint()
    #####################################################################################################
    ##################################       POST PROCESSING             ################################
    bat_supply = pd.DataFrame(index=model.T, columns=df_battery.index)
    tie_supply = pd.DataFrame(index=model.T, columns=[""])
    bat_ch = pd.DataFrame(index=model.T, columns=df_battery.index)
    bat_dis = pd.DataFrame(index=model.T, columns=df_battery.index)
    soc_supply = pd.DataFrame(index=model.T_SoC_bat, columns=df_battery.index)
    x_ch = pd.DataFrame(index=model.T, columns=df_battery.index)
    x_dis = pd.DataFrame(index=model.T, columns=df_battery.index)

    for n in model.N:
        for t in model.T:
            bat_supply.loc[t, n] = value(
                model.x_dis[n, t] * model.P_dis_bat[n, t] / model.dis_eff_bat[n]
                - model.x_ch[n, t] * model.P_ch_bat[n, t] * model.ch_eff_bat[n]
            )

    for t in model.T:
        tie_supply.loc[t] = value(
            model.x_imp[t] * model.P_imp[t] - model.x_exp[t] * model.P_exp[t]
        )

    for col in df_battery.index:
        bat_ch[col] = model.P_ch_bat[col, :]()
        bat_dis[col] = model.P_dis_bat[col, :]()
        soc_supply[col] = model.SoC_bat[col, :]()

    pv_supply = pd.Series(model.P_PV[:](), index=model.T)

    return (
        tie_supply,
        pv_supply,
        bat_supply,
        soc_supply,
        (solver.status, solver.termination_condition),
    )
