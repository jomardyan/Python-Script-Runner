""""""

Alerts and Monitoring Tests - test_alerts_monitoring.pyAlerts and Monitoring Tests - test_alerts_monitoring.py



Comprehensive tests for alert management and system monitoring including:Comprehensive tests for alert management and system monitoring including:

- Alert rule configuration and validation- Alert rule configuration and validation

- Alert trigger conditions and evaluation- Alert trigger conditions and evaluation

- Notification system integration- Notification system integration

- Process monitoring metrics- Process monitoring metrics

- Real-time metric collection- Real-time metric collection

""""""



import pytestimport pytest

import osimport os

import sysimport sys

import tempfileimport tempfile

import timeimport time

from pathlib import Pathfrom pathlib import Path

from unittest.mock import Mock, patch, MagicMockfrom unittest.mock import Mock, patch, MagicMock



sys.path.insert(0, str(Path(__file__).parent.parent))sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import ScriptRunner, AlertManagerfrom runner import ScriptRunner, AlertManager, ProcessMonitor





@pytest.mark.unit@pytest.mark.unit

class TestAlertConfiguration:class TestAlertConfiguration:

    """Test alert configuration and setup"""    """Test alert configuration and setup"""

        

    def test_alert_manager_initialization(self):    def test_alert_manager_initialization(self):

        """Test AlertManager initialization"""        """Test AlertManager initialization"""

        manager = AlertManager()        manager = AlertManager()

        assert manager is not None        assert manager is not None

        

    def test_add_simple_alert(self):    def test_add_simple_alert(self):

        """Test adding a simple alert rule"""        """Test adding a simple alert rule"""

        manager = AlertManager()        manager = AlertManager()

                

        manager.add_alert(        manager.add_alert(

            name="high_cpu",            name="high_cpu",

            condition="cpu_max > 80",            condition="cpu_max > 80",

            channels=["console"],            severity="WARNING",

            severity="WARNING"            channels=["console"]

        )        )

        assert manager is not None        

            # Alert should be registered

    def test_add_multiple_alerts(self):        assert manager is not None

        """Test adding multiple alert rules"""    

        manager = AlertManager()    def test_add_multiple_alerts(self):

                """Test adding multiple alert rules"""

        manager.add_alert("cpu_alert", "cpu_max > 90", ["email"], severity="CRITICAL")        manager = AlertManager()

        manager.add_alert("mem_alert", "memory_max_mb > 1000", ["slack"], severity="WARNING")        

        manager.add_alert("time_alert", "execution_time_seconds > 300", ["console"], severity="INFO")        manager.add_alert("cpu_alert", "cpu_max > 90", ["email"], severity="CRITICAL")

                manager.add_alert("mem_alert", "memory_max_mb > 1000", ["slack"], severity="WARNING")

        assert manager is not None        manager.add_alert("time_alert", "execution_time_seconds > 300", ["console"], severity="INFO")

            

    def test_alert_with_multiple_channels(self):        assert manager is not None

        """Test alert with multiple notification channels"""    

        manager = AlertManager()    def test_alert_with_multiple_channels(self):

                """Test alert with multiple notification channels"""

        manager.add_alert(        manager = AlertManager()

            name="multi_channel",        

            condition="cpu_max > 85",        manager.add_alert(

            channels=["email", "slack", "console"],            name="multi_channel",

            severity="ERROR"            condition="cpu_max > 85",

        )            channels=["email", "slack", "console"],

                    severity="ERROR"

        assert manager is not None        )

        

        assert manager is not None

@pytest.mark.unit

class TestAlertEvaluation:

    """Test alert condition evaluation and triggering"""@pytest.mark.unit

    class TestAlertEvaluation:

    def test_alert_trigger_on_high_cpu(self):    """Test alert condition evaluation and triggering"""

        """Test alert triggers when CPU threshold exceeded"""    

        manager = AlertManager()    def test_alert_trigger_on_high_cpu(self):

                """Test alert triggers when CPU threshold exceeded"""

        manager.add_alert(        manager = AlertManager()

            name="high_cpu",        

            condition="cpu_max > 50",        manager.add_alert(

            channels=["console"],            name="high_cpu",

            severity="WARNING"            condition="cpu_max > 50",

        )            severity="WARNING",

                    channels=["console"]

        metrics = {        )

            'cpu_max': 75.0,        

            'cpu_avg': 60.0,        metrics = {

            'memory_max_mb': 500.0            'cpu_max': 75.0,

        }            'cpu_avg': 60.0,

                    'memory_max_mb': 500.0

        alerts = manager.check_alerts(metrics)        }

        assert len(alerts) > 0        

            alerts = manager.check_alerts(metrics)

    def test_alert_no_trigger_below_threshold(self):        assert len(alerts) > 0

        """Test alert doesn't trigger when below threshold"""    

        manager = AlertManager()    def test_alert_no_trigger_below_threshold(self):

                """Test alert doesn't trigger when below threshold"""

        manager.add_alert(        manager = AlertManager()

            name="high_cpu",        

            condition="cpu_max > 80",        manager.add_alert(

            channels=["console"],            name="high_cpu",

            severity="WARNING"            condition="cpu_max > 80",

        )            severity="WARNING",

                    channels=["console"]

        metrics = {        )

            'cpu_max': 45.0,        

            'cpu_avg': 30.0,        metrics = {

            'memory_max_mb': 300.0            'cpu_max': 45.0,

        }            'cpu_avg': 30.0,

                    'memory_max_mb': 300.0

        alerts = manager.check_alerts(metrics)        }

        assert len(alerts) == 0        

            alerts = manager.check_alerts(metrics)

    def test_alert_multiple_conditions(self):        assert len(alerts) == 0

        """Test alert with multiple conditions"""    

        manager = AlertManager()    def test_alert_multiple_conditions(self):

                """Test alert with multiple conditions"""

        manager.add_alert(        manager = AlertManager()

            name="resource_alert",        

            condition="cpu_max > 70 AND memory_max_mb > 400",        manager.add_alert(

            channels=["email"],            name="resource_alert",

            severity="ERROR"            condition="cpu_max > 70 AND memory_max_mb > 400",

        )            severity="ERROR",

                    channels=["email"]

        # Both conditions met        )

        metrics1 = {        

            'cpu_max': 85.0,        # Both conditions met

            'memory_max_mb': 500.0,        metrics1 = {

            'execution_time_seconds': 10.0            'cpu_max': 85.0,

        }            'memory_max_mb': 500.0,

        alerts1 = manager.check_alerts(metrics1)            'execution_time_seconds': 10.0

        assert len(alerts1) > 0        }

                alerts1 = manager.check_alerts(metrics1)

        # Only one condition met        assert len(alerts1) > 0

        metrics2 = {        

            'cpu_max': 85.0,        # Only one condition met

            'memory_max_mb': 300.0,        metrics2 = {

            'execution_time_seconds': 10.0            'cpu_max': 85.0,

        }            'memory_max_mb': 300.0,

        alerts2 = manager.check_alerts(metrics2)            'execution_time_seconds': 10.0

        assert len(alerts2) == 0        }

            alerts2 = manager.check_alerts(metrics2)

    def test_alert_severity_levels(self):        assert len(alerts2) == 0

        """Test alert severity levels"""    

        manager = AlertManager()    def test_alert_severity_levels(self):

                """Test alert severity levels"""

        severity_levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]        manager = AlertManager()

                

        for i, severity_level in enumerate(severity_levels):        severity_levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]

            manager.add_alert(        

                name=f"alert_{severity_level}",        for i, severity in enumerate(severity_levels):

                condition=f"cpu_max > {70 + i}",            manager.add_alert(

                channels=["console"],                name=f"alert_{severity}",

                severity=severity_level                condition=f"cpu_max > {70 + i}",

            )                severity=severity,

                        channels=["console"]

        assert manager is not None            )

        

        assert manager is not None

@pytest.mark.unit

class TestMonitoring:

    """Test process monitoring and metric collection"""@pytest.mark.unit

    class TestMonitoring:

    def test_monitor_cpu_usage(self, tmp_path):    """Test process monitoring and metric collection"""

        """Test CPU usage monitoring"""    

        script_file = tmp_path / "cpu_work.py"    def test_monitor_cpu_usage(self, tmp_path):

        script_file.write_text("""        """Test CPU usage monitoring"""

import time        script_file = tmp_path / "cpu_work.py"

start = time.time()        script_file.write_text("""

while time.time() - start < 0.1:import time

    _ = [x**2 for x in range(5000)]start = time.time()

print("CPU work completed")while time.time() - start < 0.1:

""")    _ = [x**2 for x in range(5000)]

        print("CPU work completed")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        assert result['metrics']['cpu_max'] > 0        result = runner.run_script()

        assert result['metrics']['cpu_avg'] >= 0        

        assert isinstance(result['metrics']['cpu_max'], (int, float))        assert result['metrics']['cpu_max'] > 0

            assert result['metrics']['cpu_avg'] >= 0

    def test_monitor_memory_usage(self, tmp_path):        assert isinstance(result['metrics']['cpu_max'], (int, float))

        """Test memory usage monitoring"""    

        script_file = tmp_path / "mem_work.py"    def test_monitor_memory_usage(self, tmp_path):

        script_file.write_text("""        """Test memory usage monitoring"""

data = [list(range(1000)) for _ in range(500)]        script_file = tmp_path / "mem_work.py"

print(f"Allocated {len(data)} lists with total size")        script_file.write_text("""

""")data = [list(range(1000)) for _ in range(500)]

        print(f"Allocated {len(data)} lists with total size")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        assert result['metrics']['memory_max_mb'] > 0        result = runner.run_script()

        assert result['metrics']['memory_avg_mb'] >= 0        

        assert isinstance(result['metrics']['memory_max_mb'], (int, float))        assert result['metrics']['memory_max_mb'] > 0

            assert result['metrics']['memory_avg_mb'] >= 0

    def test_monitor_thread_count(self, tmp_path):        assert isinstance(result['metrics']['memory_max_mb'], (int, float))

        """Test thread count monitoring"""    

        script_file = tmp_path / "threads.py"    def test_monitor_thread_count(self, tmp_path):

        script_file.write_text("""        """Test thread count monitoring"""

import threading        script_file = tmp_path / "threads.py"

import time        script_file.write_text("""

import threading

def dummy_thread():import time

    time.sleep(0.05)

def dummy_thread():

threads = [threading.Thread(target=dummy_thread) for _ in range(3)]    time.sleep(0.05)

for t in threads:

    t.start()threads = [threading.Thread(target=dummy_thread) for _ in range(3)]

for t in threads:for t in threads:

    t.join()    t.start()

print("All threads completed")for t in threads:

""")    t.join()

        print("All threads completed")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        assert 'num_threads' in result['metrics']        result = runner.run_script()

            

    def test_monitor_execution_time(self, tmp_path):        assert 'num_threads' in result['metrics']

        """Test execution time measurement"""    

        script_file = tmp_path / "timed.py"    def test_monitor_execution_time(self, tmp_path):

        script_file.write_text("""        """Test execution time measurement"""

import time        script_file = tmp_path / "timed.py"

time.sleep(0.1)        script_file.write_text("""

print("Done")import time

""")time.sleep(0.1)

        print("Done")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        exec_time = result['metrics']['execution_time_seconds']        result = runner.run_script()

        assert exec_time >= 0.1        

        assert exec_time < 1.0        exec_time = result['metrics']['execution_time_seconds']

        assert exec_time >= 0.1

        assert exec_time < 1.0  # Should not take too long

@pytest.mark.unit

class TestMetricsAggregation:

    """Test metrics aggregation and statistics"""@pytest.mark.unit

    class TestMetricsAggregation:

    def test_cpu_statistics(self, tmp_path):    """Test metrics aggregation and statistics"""

        """Test CPU metric statistics"""    

        script_file = tmp_path / "cpu_test.py"    def test_cpu_statistics(self, tmp_path):

        script_file.write_text("""        """Test CPU metric statistics"""

import time        script_file = tmp_path / "cpu_test.py"

import math        script_file.write_text("""

start = time.time()import time

while time.time() - start < 0.2:import math

    _ = [math.sqrt(x) for x in range(10000)]start = time.time()

print("CPU test done")while time.time() - start < 0.2:

""")    _ = [math.sqrt(x) for x in range(10000)]

        print("CPU test done")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        metrics = result['metrics']        result = runner.run_script()

        assert metrics['cpu_max'] >= metrics['cpu_avg']        

        if 'cpu_min' in metrics:        metrics = result['metrics']

            assert metrics['cpu_min'] <= metrics['cpu_avg']        assert metrics['cpu_max'] >= metrics['cpu_avg']

            if 'cpu_min' in metrics:

    def test_memory_statistics(self, tmp_path):            assert metrics['cpu_min'] <= metrics['cpu_avg']

        """Test memory metric statistics"""    

        script_file = tmp_path / "mem_test.py"    def test_memory_statistics(self, tmp_path):

        script_file.write_text("""        """Test memory metric statistics"""

import time        script_file = tmp_path / "mem_test.py"

data = []        script_file.write_text("""

for i in range(10):import time

    data.append([0] * 10000)data = []

    time.sleep(0.01)for i in range(10):

print(f"Allocated {len(data)} arrays")    data.append([0] * 10000)

""")    time.sleep(0.01)

        print(f"Allocated {len(data)} arrays")

        runner = ScriptRunner(str(script_file))""")

        result = runner.run_script()        

                runner = ScriptRunner(str(script_file))

        metrics = result['metrics']        result = runner.run_script()

        assert metrics['memory_max_mb'] >= metrics['memory_avg_mb']        

        if 'memory_min_mb' in metrics:        metrics = result['metrics']

            assert metrics['memory_min_mb'] <= metrics['memory_avg_mb']        assert metrics['memory_max_mb'] >= metrics['memory_avg_mb']

        if 'memory_min_mb' in metrics:

            assert metrics['memory_min_mb'] <= metrics['memory_avg_mb']

@pytest.mark.unit

class TestNotificationChannels:

    """Test notification channel configuration"""@pytest.mark.unit

    class TestNotificationChannels:

    def test_console_notification(self):    """Test notification channel configuration"""

        """Test console notification channel"""    

        manager = AlertManager()    def test_console_notification(self):

                """Test console notification channel"""

        manager.add_alert(        manager = AlertManager()

            name="console_test",        

            condition="cpu_max > 50",        manager.add_alert(

            channels=["console"],            name="console_test",

            severity="WARNING"            condition="cpu_max > 50",

        )            severity="WARNING",

                    channels=["console"]

        assert manager is not None        )

            

    @patch('smtplib.SMTP')        assert manager is not None

    def test_email_channel_configuration(self, mock_smtp):    

        """Test email notification channel setup"""    @patch('smtplib.SMTP')

        manager = AlertManager()    def test_email_channel_configuration(self, mock_smtp):

                """Test email notification channel setup"""

        manager.add_alert(        manager = AlertManager()

            name="email_test",        

            condition="memory_max_mb > 500",        manager.add_alert(

            channels=["email"],            name="email_test",

            severity="ERROR"            condition="memory_max_mb > 500",

        )            severity="ERROR",

                    channels=["email"]

        assert manager is not None        )

            

    def test_multiple_channel_configuration(self):        assert manager is not None

        """Test configuration with multiple channels"""    

        manager = AlertManager()    def test_multiple_channel_configuration(self):

                """Test configuration with multiple channels"""

        manager.add_alert(        manager = AlertManager()

            name="multi_notify",        

            condition="execution_time_seconds > 60",        manager.add_alert(

            channels=["console", "email", "slack"],            name="multi_notify",

            severity="ERROR"            condition="execution_time_seconds > 60",

        )            severity="ERROR",

                    channels=["console", "email", "slack"]

        assert manager is not None        )

        

        assert manager is not None

@pytest.mark.unit

class TestAlertConditionParsing:

    """Test alert condition parsing and validation"""@pytest.mark.unit

    class TestAlertConditionParsing:

    def test_simple_condition_parsing(self):    """Test alert condition parsing and validation"""

        """Test parsing simple conditions"""    

        manager = AlertManager()    def test_simple_condition_parsing(self):

                """Test parsing simple conditions"""

        conditions = [        manager = AlertManager()

            "cpu_max > 80",        

            "memory_max_mb > 1000",        conditions = [

            "execution_time_seconds > 300"            "cpu_max > 80",

        ]            "memory_max_mb > 1000",

                    "execution_time_seconds > 300"

        for condition in conditions:        ]

            manager.add_alert(        

                name=f"alert_{condition.replace(' ', '_').replace('>', 'gt')}",        for condition in conditions:

                condition=condition,            manager.add_alert(

                channels=["console"],                name=f"alert_{condition}",

                severity="WARNING"                condition=condition,

            )                severity="WARNING",

                        channels=["console"]

        assert manager is not None            )

            

    def test_complex_condition_parsing(self):        assert manager is not None

        """Test parsing complex conditions"""    

        manager = AlertManager()    def test_complex_condition_parsing(self):

                """Test parsing complex conditions"""

        complex_conditions = [        manager = AlertManager()

            "cpu_max > 80 AND memory_max_mb > 500",        

            "execution_time_seconds > 300 OR cpu_max > 95",        complex_conditions = [

            "cpu_max > 75 AND memory_max_mb > 400 AND execution_time_seconds > 120"            "cpu_max > 80 AND memory_max_mb > 500",

        ]            "execution_time_seconds > 300 OR cpu_max > 95",

                    "cpu_max > 75 AND memory_max_mb > 400 AND execution_time_seconds > 120"

        for i, condition in enumerate(complex_conditions):        ]

            manager.add_alert(        

                name=f"complex_alert_{i}",        for i, condition in enumerate(complex_conditions):

                condition=condition,            manager.add_alert(

                channels=["console"],                name=f"complex_alert_{i}",

                severity="ERROR"                condition=condition,

            )                severity="ERROR",

                        channels=["console"]

        assert manager is not None            )

        

        assert manager is not None

if __name__ == "__main__":

    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
