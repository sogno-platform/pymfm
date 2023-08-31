import json
import pandas as pd
import dateutil.parser
import rule_based_balancer_utils.rule_based_balancer as rbb
import rule_based_balancer_utils.data_prep as rf
import rule_based_balancer_utils.data_output as wo


def open_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def getDateTimeFromString(string):
    d = dateutil.parser.parse(string)
    return d


def main():
    filepath = "balancer_input_online.json"
    data = open_json(filepath)
    if (
        getDateTimeFromString(data["UC_start"])
        <= getDateTimeFromString(data["measurements_request"]["timestamp"])
        <= getDateTimeFromString(data["UC_end"])
    ):
        input_dict, flex_specs = rf.read_from_json(
            data["measurements_request"], data["flex_specs"]
        )

        output, SOF = rbb._rule_based_control(input_dict, flex_specs)
        json_output = wo.write_output(output)
        print(json_output)

    else:
        print("\nMeasurement is not in the range of UC start and UC end \n")


if __name__ == "__main__":
    main()
