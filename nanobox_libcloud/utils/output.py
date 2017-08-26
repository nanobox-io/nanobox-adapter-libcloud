import json


def success(data, status=200):
    return json.dumps(data, indent=2), status, [["Content-Type", "application/json"]]

def failure(message, status=400):
    return json.dumps({"error": message}, indent=2), status, [["Content-Type", "application/json"]]
