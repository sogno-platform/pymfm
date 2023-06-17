import azure.functions as func
from balancer_utils.balancer_control import Balancer
from balancer_utils.data_output import Write_output


def main(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    output = Balancer().balancer_control(data)
    json_output = Write_output().write_json_output(output)
    return func.HttpResponse(body=json_output, mimetype="application/json")
