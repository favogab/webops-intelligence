
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_monitoring_interval(monkeypatch):
    monkeypatch.delenv("MONITORING_INTERVAL_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.monitoring_interval_seconds == 60


def test_valid_monitoring_interval(monkeypatch):
    monkeypatch.setenv("MONITORING_INTERVAL_SECONDS", "120")

    settings = Settings(_env_file=None)

    assert settings.monitoring_interval_seconds == 120


def test_invalid_monitoring_interval(monkeypatch):
    monkeypatch.setenv("MONITORING_INTERVAL_SECONDS", "5")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_monitoring_interval_type(monkeypatch):
    monkeypatch.setenv("MONITORING_INTERVAL_SECONDS", "not-a-number")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)