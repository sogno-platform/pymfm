from datetime import datetime
import json
import pytz
import dateutil.parser


def write_output(output):
    data = {}
    Balancer_output = {}
    Balancer_output["version"] = "1.0"
    units = {}
    units["timestamp"] = "ISO8601"
    units["Pbat"] = "kW"
    Balancer_output["units"] = units
    data["Balancer_output"] = Balancer_output
    timestamp = dateutil.parser.parse(output["timestamp"])
    Balancer_output["timestamp"] = str(timestamp.replace(tzinfo=None))
    Balancer_output["values"] = output["Pbat_kW"]

    return json.dumps(data)

    # with open('output.json', 'w') as outfile:
    # json.dump(data, outfile, sort_keys=False, indent=4)
