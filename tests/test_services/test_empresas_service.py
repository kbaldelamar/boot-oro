import pytest

from services.empresas_service import EmpresasCasosBootService
from services.api_client import APIClient, APIResponse


class DummyClient:
    def __init__(self, response):
        self.response = response

    def get(self, endpoint):
        return self.response


class DummyResponse:
    def __init__(self, success=True, status_code=200, data=None, message="ok", error=None):
        self.success = success
        self.status_code = status_code
        self.data = data
        self.message = message
        self.error = error


def test_listar_empresas_success(monkeypatch):
    response = DummyResponse(success=True, status_code=200, data={"data": []})
    service = EmpresasCasosBootService(config=type("c", (), {"api_url_programacion_base": "http://x"}))
    service.api_client = DummyClient(response)
    result = service.listar_empresas()
    assert result["success"] is True
    assert result["data"] == []


def test_listar_empresas_error(monkeypatch):
    response = DummyResponse(success=False, status_code=500, data={}, message="bad")
    service = EmpresasCasosBootService(config=type("c", (), {"api_url_programacion_base": "http://x"}))
    service.api_client = DummyClient(response)
    result = service.listar_empresas()
    assert result["success"] is False
    assert result["status_code"] == 500
