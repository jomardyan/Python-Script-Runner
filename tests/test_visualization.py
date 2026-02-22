#!/usr/bin/env python3
"""
Unit tests for ExecutionVisualizer class.

Tests the visualization functionality for script execution orchestration.
"""

import unittest
import sys
import os
from io import StringIO

# Add parent directory to path to import runner module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import ExecutionVisualizer, ScriptRunner


class TestExecutionVisualizer(unittest.TestCase):
    """Test cases for ExecutionVisualizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.visualizer = ExecutionVisualizer(enabled=True)
        self.output = StringIO()
        self.original_stdout = sys.stdout

    def tearDown(self):
        """Clean up after tests."""
        sys.stdout = self.original_stdout

    def test_visualizer_initialization(self):
        """Test visualizer initialization."""
        viz = ExecutionVisualizer(enabled=False)
        self.assertFalse(viz.enabled)
        self.assertIsNone(viz.start_time)
        self.assertEqual(viz.step_count, 0)

        viz = ExecutionVisualizer(enabled=True)
        self.assertTrue(viz.enabled)

    def test_show_header(self):
        """Test header display."""
        sys.stdout = self.output
        self.visualizer.show_header("test_script.py", ["arg1", "arg2"], 1)
        output = self.output.getvalue()

        self.assertIn("SCRIPT EXECUTION FLOW VISUALIZATION", output)
        self.assertIn("test_script.py", output)
        self.assertIn("arg1 arg2", output)
        self.assertIn("Attempt: #1", output)

    def test_show_step(self):
        """Test step display."""
        sys.stdout = self.output
        self.visualizer.start_time = 0  # Set fixed start time for testing
        self.visualizer.show_step("Test Stage", "Test description", "done")
        output = self.output.getvalue()

        self.assertIn("Step", output)
        self.assertIn("Test Stage", output)
        self.assertIn("Test description", output)
        self.assertIn("✓", output)  # done status symbol

    def test_show_step_with_details(self):
        """Test step display with details."""
        sys.stdout = self.output
        self.visualizer.start_time = 0
        details = {"key1": "value1", "key2": "value2"}
        self.visualizer.show_step("Test", "Description", "running", details)
        output = self.output.getvalue()

        self.assertIn("key1: value1", output)
        self.assertIn("key2: value2", output)

    def test_show_footer(self):
        """Test footer display."""
        sys.stdout = self.output
        self.visualizer.show_footer(1.234, True, 0)
        output = self.output.getvalue()

        self.assertIn("EXECUTION SUCCESS", output)
        self.assertIn("1.234", output)
        self.assertIn("Exit Code: 0", output)

    def test_disabled_visualizer_no_output(self):
        """Test that disabled visualizer produces no output."""
        viz = ExecutionVisualizer(enabled=False)
        sys.stdout = self.output

        viz.show_header("test.py")
        viz.show_step("Test", "Description")
        viz.show_footer(1.0, True, 0)

        output = self.output.getvalue()
        self.assertEqual(output, "")

    def test_visualizer_integration_with_runner(self):
        """Test visualizer integration with ScriptRunner."""
        # Create a simple test script
        test_script = "/tmp/test_viz_integration.py"
        with open(test_script, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('Test')\n")

        try:
            runner = ScriptRunner(test_script)
            runner.visualizer.enabled = True

            # Capture output
            sys.stdout = self.output

            result = runner.run_script()

            output = self.output.getvalue()

            # Verify visualization appears in output
            self.assertIn("SCRIPT EXECUTION FLOW VISUALIZATION", output)
            self.assertIn("Validation", output)
            self.assertIn("System Metrics", output)
            self.assertIn("Subprocess Launch", output)

            # Verify script executed successfully
            self.assertEqual(result['returncode'], 0)
            self.assertTrue(result['success'])

        finally:
            sys.stdout = self.original_stdout
            if os.path.exists(test_script):
                os.remove(test_script)


if __name__ == "__main__":
    unittest.main()
