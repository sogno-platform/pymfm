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
            "Time",
            "Ptcb_kW",
            "SOF_kWh",
            "import",
            "export",
            "Ptei_kW",
            "Expected_Ptei",
            "Ptcb_kW_init",
        ]
    )
    output_datetime = getDateTimeFromString(input_dict["Time"]).isoformat()
    output["Time"] = output_datetime

    # initialize
    output["import"] = 0
    output["export"] = 0
    output["SOF_kWh"] = 0

    output["Ptcb_kW"] = -input_dict["Preq_kW"] + input_dict["Cal_iONS_kW"]
    output["SOF_kWh"] = flex_specs["initial_SOF"] - (
        output["Ptcb_kW"] * input_dict["delta_T"]
    )

    # discharging
    if output["Ptcb_kW"] > 0:
        act_ptcb = output["Ptcb_kW"]
        if abs(output["Ptcb_kW"]) < flex_specs["Pf_dis_kW"]:
            pass

        else:
            output["import"] = output["Ptcb_kW"] - flex_specs["Pf_dis_kW"]
            output["Ptcb_kW"] = flex_specs["Pf_dis_kW"]
            output["SOF_kWh"] = flex_specs["initial_SOF"] - (
                flex_specs["Pf_dis_kW"] * input_dict["delta_T"]
            )

        if output["SOF_kWh"] >= flex_specs["min_SOF"]:
            pass

        else:
            output["import"] = output["import"] + (
                ((flex_specs["min_SOF"] - output["SOF_kWh"]) / input_dict["delta_T"])
            )
            output["Ptcb_kW"] = act_ptcb - output["import"]
            output["SOF_kWh"] = flex_specs["min_SOF"]

        output["Ptcb_kW"] = float(output["Ptcb_kW"])

    # charging
    if output["Ptcb_kW"] < 0:
        act_ptcb = output["Ptcb_kW"]
        if abs(output["Ptcb_kW"]) <= flex_specs["Pf_ch_kW"]:
            output["export"] = 0
            pass
        else:
            output["export"] = abs(output["Ptcb_kW"]) - flex_specs["Pf_ch_kW"]
            output["Ptcb_kW"] = -flex_specs["Pf_ch_kW"]
            output["SOF_kWh"] = flex_specs["initial_SOF"] + (
                flex_specs["Pf_ch_kW"] * input_dict["delta_T"]
            )
        if output["SOF_kWh"] <= flex_specs["max_SOF"]:
            pass
        else:
            output["export"] = output["export"] + (
                (output["SOF_kWh"] - flex_specs["max_SOF"]) / input_dict["delta_T"]
            )
            output["Ptcb_kW"] = -(abs(act_ptcb) - (output["export"]))
            output["SOF_kWh"] = flex_specs["max_SOF"]
        output["Ptcb_kW"] = float(output["Ptcb_kW"])

    output["Ptei_kW"] = -input_dict["Cal_iONS_kW"]
    output["Expected_Ptei_kW"] = output["export"] - output["import"]

    # Considering current Ptcb_kW
    output["Ptcb_kW"] = output["Ptcb_kW"] + input_dict["Ptcb_Init_kW"]
    if output["Ptcb_kW"] < 0:
        if abs(output["Ptcb_kW"]) <= flex_specs["Pf_ch_kW"]:
            pass
        else:
            output["Ptcb_kW"] = -flex_specs["Pf_ch_kW"]

    else:
        if output["Ptcb_kW"] <= flex_specs["Pf_dis_kW"]:
            pass
        else:
            output["Ptcb_kW"] = flex_specs["Pf_dis_kW"]

    return output, output["SOF_kWh"]
