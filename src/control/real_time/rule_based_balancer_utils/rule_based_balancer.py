import dateutil.parser
import pandas as pd


# datetime parser
def getDateTimeFromString(string):
    d = dateutil.parser.parse(string)
    return d


# rule based control fuction
def _rule_based_control(input_dict, flex_specs):
    output = dict.fromkeys(
        [
            "timestamp",
            "Pbat_kW",
            "SOF_kWh",
            "import",
            "export",
            "Ptei_kW",
            "Expected_Ptei",
            "Pbat_kW_init",
        ]
    )
    output_datetime = getDateTimeFromString(input_dict["timestamp"]).isoformat()
    output["timestamp"] = output_datetime

    # initialize
    output["import"] = 0
    output["export"] = 0
    output["SOF_kWh"] = 0

    output["Pbat_kW"] = -input_dict["Preq_kW"] + input_dict["Pnet_meas_kW"]
    output["SOF_kWh"] = flex_specs["initial_SOF"] - (
        output["Pbat_kW"] * input_dict["delta_T"]
    )

    # discharging
    if output["Pbat_kW"] > 0:
        act_ptcb = output["Pbat_kW"]
        if abs(output["Pbat_kW"]) < flex_specs["Pf_dis_kW"]:
            pass

        else:
            output["import"] = output["Pbat_kW"] - flex_specs["Pf_dis_kW"]
            output["Pbat_kW"] = flex_specs["Pf_dis_kW"]
            output["SOF_kWh"] = flex_specs["initial_SOF"] - (
                flex_specs["Pf_dis_kW"] * input_dict["delta_T"]
            )

        if output["SOF_kWh"] >= flex_specs["min_SOF"]:
            pass

        else:
            output["import"] = output["import"] + (
                ((flex_specs["min_SOF"] - output["SOF_kWh"]) / input_dict["delta_T"])
            )
            output["Pbat_kW"] = act_ptcb - output["import"]
            output["SOF_kWh"] = flex_specs["min_SOF"]

        output["Pbat_kW"] = float(output["Pbat_kW"])

    # charging
    if output["Pbat_kW"] < 0:
        act_ptcb = output["Pbat_kW"]
        if abs(output["Pbat_kW"]) <= flex_specs["Pf_ch_kW"]:
            output["export"] = 0
            pass
        else:
            output["export"] = abs(output["Pbat_kW"]) - flex_specs["Pf_ch_kW"]
            output["Pbat_kW"] = -flex_specs["Pf_ch_kW"]
            output["SOF_kWh"] = flex_specs["initial_SOF"] + (
                flex_specs["Pf_ch_kW"] * input_dict["delta_T"]
            )
        if output["SOF_kWh"] <= flex_specs["max_SOF"]:
            pass
        else:
            output["export"] = output["export"] + (
                (output["SOF_kWh"] - flex_specs["max_SOF"]) / input_dict["delta_T"]
            )
            output["Pbat_kW"] = -(abs(act_ptcb) - (output["export"]))
            output["SOF_kWh"] = flex_specs["max_SOF"]
        output["Pbat_kW"] = float(output["Pbat_kW"])

    output["Ptei_kW"] = -input_dict["Pnet_meas_kW"]
    output["Expected_Ptei_kW"] = output["export"] - output["import"]

    # Considering current Pbat_kW
    output["Pbat_kW"] = output["Pbat_kW"] + input_dict["Pbat_init_kW"]
    if output["Pbat_kW"] < 0:
        if abs(output["Pbat_kW"]) <= flex_specs["Pf_ch_kW"]:
            pass
        else:
            output["Pbat_kW"] = -flex_specs["Pf_ch_kW"]

    else:
        if output["Pbat_kW"] <= flex_specs["Pf_dis_kW"]:
            pass
        else:
            output["Pbat_kW"] = flex_specs["Pf_dis_kW"]

    return output, output["SOF_kWh"]
