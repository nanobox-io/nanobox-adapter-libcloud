import typing
from flask import json


FlaskHeaders = typing.Union[typing.List[typing.Tuple[str, str]], typing.Dict[str, str]]
FlaskResponse = typing.Tuple[str, int, FlaskHeaders]


def success(data, status=200) -> FlaskResponse:
    return json.dumps(data, indent=2), status, [("Content-Type", "application/json")]


def failure(message, status=400) -> FlaskResponse:
    return json.dumps({"errors": ([message]\
           if hasattr(message, 'strip') else message if hasattr(message, 'split')\
           else repr(message))}, indent=2),\
           status,\
           [("Content-Type", "application/json")]
