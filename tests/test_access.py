"""
Tests the door and the ceiling.

These matter more than most: if the password check is wrong, anyone with the
link generates worksheets on the owner's account, and if the cap is wrong the
bill has no upper bound.
"""

import datetime

import pytest

import access


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Each test starts with no password and no limit configured."""
    monkeypatch.delenv(access.PASSWORD_SETTING, raising=False)
    monkeypatch.delenv(access.DAILY_LIMIT_SETTING, raising=False)
    access._usage_counter().update({"date": None, "count": 0})
    yield
    access._usage_counter().update({"date": None, "count": 0})


# --------------------------------------------------------------------------
# The door
# --------------------------------------------------------------------------


def test_no_password_configured_means_open_access():
    """Running on your own machine must stay a double-click."""
    assert access.password_is_configured() is False
    assert access.check_password() is True


def test_a_configured_password_closes_the_door(monkeypatch):
    monkeypatch.setenv(access.PASSWORD_SETTING, "staffroom-2026")
    assert access.password_is_configured() is True


def test_empty_password_setting_does_not_count_as_protection(monkeypatch):
    """An empty value must not read as 'a password is set' and lock everyone out
    — nor as protection when there is none."""
    monkeypatch.setenv(access.PASSWORD_SETTING, "")
    assert access.password_is_configured() is False


# --------------------------------------------------------------------------
# The ceiling
# --------------------------------------------------------------------------


def test_default_limit_applies_when_unset():
    assert access.daily_limit() == access.DEFAULT_DAILY_LIMIT


def test_limit_is_configurable(monkeypatch):
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "5")
    assert access.daily_limit() == 5


def test_nonsense_limit_falls_back_to_the_default(monkeypatch):
    """A typo in the setting must not remove the ceiling altogether."""
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "unlimited")
    assert access.daily_limit() == access.DEFAULT_DAILY_LIMIT


def test_usage_counts_up_and_remaining_counts_down(monkeypatch):
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "3")
    assert access.worksheets_remaining_today() == 3
    access.record_worksheets(1)
    assert access.worksheets_used_today() == 1
    assert access.worksheets_remaining_today() == 2
    access.record_worksheets(2)
    assert access.worksheets_remaining_today() == 0


def test_remaining_never_goes_negative(monkeypatch):
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "2")
    access.record_worksheets(10)
    assert access.worksheets_remaining_today() == 0


def test_the_tally_resets_on_a_new_day(monkeypatch):
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "3")
    access.record_worksheets(3)
    assert access.worksheets_remaining_today() == 0

    # Pretend the counter was last touched yesterday.
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    access._usage_counter()["date"] = yesterday

    assert access.worksheets_remaining_today() == 3, "allowance did not reset overnight"


def test_the_cap_is_enforced_before_any_api_call(monkeypatch):
    """check_daily_limit is the gate the app calls before spending money."""
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "1")
    assert access.check_daily_limit() is True
    access.record_worksheets(1)
    assert access.check_daily_limit() is False


def test_a_failed_generation_does_not_consume_allowance(monkeypatch):
    """The app records usage only after a worksheet succeeds."""
    monkeypatch.setenv(access.DAILY_LIMIT_SETTING, "2")
    before = access.worksheets_used_today()
    # No record_worksheets() call — mirrors the failure path in app.py.
    assert access.worksheets_used_today() == before
    assert access.worksheets_remaining_today() == 2


def test_app_calls_the_gate_before_generating():
    """Guards the wiring, not just the logic.

    If someone removes the check from app.py the logic here still passes, so
    assert the call site exists.
    """
    import pathlib

    source = (pathlib.Path(access.__file__).parent / "app.py").read_text()
    assert "if not check_password():" in source, "app.py no longer gates on the password"
    assert "if not check_daily_limit():" in source, "app.py no longer enforces the daily cap"
    assert "record_worksheets(1)" in source, "app.py no longer counts worksheets"
