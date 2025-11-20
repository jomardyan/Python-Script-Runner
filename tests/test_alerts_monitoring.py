"""
Alerts and monitoring behaviors for ScriptRunner alerting utilities.
"""

import time

import pytest

from runner import Alert, AlertChannel, AlertManager


@pytest.fixture()
def alert_manager():
    manager = AlertManager()
    manager.alert_history.clear()
    return manager


class TestAlertConfiguration:
    def test_add_alert_tracks_rule(self, alert_manager):
        alert_manager.add_alert(
            name="high_cpu",
            condition="cpu_max > 80",
            channels=["console"],
            severity="WARNING",
        )

        assert len(alert_manager.alerts) == 1
        alert = alert_manager.alerts[0]
        assert alert.name == "high_cpu"
        assert alert.severity.value == "WARNING"
        assert alert.channels == [AlertChannel.STDOUT]

    def test_channel_aliases_default_to_stdout(self, alert_manager, caplog):
        alert_manager.add_alert(
            name="unknown_channel",
            condition="cpu_max > 10",
            channels=["pagerduty"],
        )

        assert alert_manager.alerts[0].channels == [AlertChannel.STDOUT]
        assert "Unknown alert channel" in caplog.text


class TestAlertEvaluation:
    def test_alert_trigger_records_history(self, alert_manager):
        alert_manager.add_alert(
            name="critical_cpu",
            condition="cpu_max > 50",
            channels=[AlertChannel.STDOUT],
            severity="CRITICAL",
        )

        metrics = {"cpu_max": 75.0, "memory_max_mb": 500.0}
        history = alert_manager.check_alerts(metrics)

        assert history, "Alert history should contain a triggered entry"
        entry = history[-1]
        assert entry["name"] == "critical_cpu"
        assert entry["severity"] == "CRITICAL"
        assert entry["metrics"] == metrics

    def test_throttle_blocks_retrigger_until_window_passed(self, alert_manager, monkeypatch):
        alert_manager.add_alert(
            name="flappy",
            condition="cpu_max > 10",
            channels=[AlertChannel.STDOUT],
            throttle_seconds=30,
        )

        metrics = {"cpu_max": 20}
        first_history = alert_manager.check_alerts(metrics)
        assert len(first_history) == 1

        # Immediately re-run should not append additional history
        second_history = alert_manager.check_alerts(metrics)
        assert len(second_history) == 1

        # Advance time past throttle window and ensure another trigger is recorded
        real_time = time.time
        monkeypatch.setattr(time, "time", lambda: real_time() + 35)
        final_history = alert_manager.check_alerts(metrics)
        assert len(final_history) == 2

    def test_bad_condition_does_not_raise(self, alert_manager, caplog):
        alert_manager.add_alert(
            name="bad_condition",
            condition="cpu_max >>",
            channels=[AlertChannel.STDOUT],
        )

        metrics = {"cpu_max": 30}
        history = alert_manager.check_alerts(metrics)

        assert history == []
        assert "condition evaluation failed" in caplog.text
