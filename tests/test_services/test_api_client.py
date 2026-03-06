import json
import pytest
import requests

from services.api_client import APIClient, APIResponse, HTTPMethod


class DummyResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise json.JSONDecodeError("msg", "doc", 0)
        return self._json


class DummySession:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc

    def request(self, method, url, **kwargs):
        if self.exc:
            raise self.exc
        return self.response


def test_parse_response_success():
    client = APIClient()
    resp = DummyResponse(200, json_data={"foo": "bar"})
    api_resp = client._parse_response(resp)
    assert api_resp.success is True
    assert api_resp.status_code == 200
    assert api_resp.data == {"foo": "bar"}
    assert api_resp.message == "Petición exitosa"


def test_parse_response_error_codes():
    client = APIClient()
    # 404 example
    resp = DummyResponse(404, json_data={})
    api_resp = client._parse_response(resp)
    assert api_resp.success is False
    assert api_resp.error.startswith("Error en la petición") or "No Encontrado" in api_resp.message

    resp500 = DummyResponse(500, json_data=None, text="oops")
    api_resp500 = client._parse_response(resp500)
    assert api_resp500.success is False
    assert "Error Interno" in api_resp500.message


def test_make_request_timeout():
    client = APIClient()
    client.session = DummySession(exc=requests.exceptions.Timeout())
    result = client._make_request(HTTPMethod.GET, "/whatever")
    assert result.status_code == 408
    assert result.success is False


def test_make_request_connection_error():
    client = APIClient()
    client.session = DummySession(exc=requests.exceptions.ConnectionError())
    result = client._make_request(HTTPMethod.GET, "/whatever")
    assert result.status_code == 503
    assert result.success is False


def test_get_uses_session():
    # verify that convenience methods call _make_request
    resp = DummyResponse(200, json_data={})
    client = APIClient()
    client.session = DummySession(response=resp)
    api_resp = client.get("/foo")
    assert isinstance(api_resp, APIResponse)
    assert api_resp.status_code == 200
