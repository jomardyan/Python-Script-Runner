"""API path and environment security regressions; requires dashboard dependencies."""
import pytest
from unittest.mock import patch


class TestPathValidation:
    """Tests for _validate_script_path enhancements in the Web API."""

    def test_null_byte_in_path_rejected(self):
        """Paths containing null bytes must be rejected."""
        from WEBAPI.api import _validate_script_path
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_script_path("/some/path\x00.py")
        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.detail

    def test_symlink_rejected(self, tmp_path):
        """Symlinks must be rejected even if they point to a valid .py file."""
        from WEBAPI.api import _validate_script_path
        from fastapi import HTTPException

        # Create a real .py file and a symlink to it
        real_file = tmp_path / "real.py"
        real_file.write_text("print('hello')")
        link = tmp_path / "link.py"
        try:
            link.symlink_to(real_file)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                pytest.skip("Windows account lacks symbolic link creation privileges")
            raise

        # The symlink check happens before resolve(), so the symlink is
        # detected and rejected with a clear error message.
        with pytest.raises(HTTPException) as exc_info:
            _validate_script_path(str(link))
        assert exc_info.value.status_code == 400


class TestEnvVarFiltering:
    """Tests for dangerous environment variable filtering."""

    def test_dangerous_env_vars_stripped(self):
        """_validate_payload must strip dangerous env vars like PATH."""
        from WEBAPI.api import _validate_payload, RunRequest, _DANGEROUS_ENV_VARS
        from fastapi import HTTPException

        # Create a minimal valid payload (the script won't actually be
        # validated here because _validate_script_path will raise – we
        # mock it).
        payload = RunRequest(
            script_path="/dummy.py",
            env_vars={"PATH": "/evil", "MY_VAR": "safe", "LD_PRELOAD": "/bad.so"},
        )

        with patch("WEBAPI.api._validate_script_path"):
            result = _validate_payload(payload)

        assert "PATH" not in result.env_vars
        assert "LD_PRELOAD" not in result.env_vars
        assert result.env_vars["MY_VAR"] == "safe"

    def test_safe_env_vars_preserved(self):
        """Non-dangerous env vars must pass through unchanged."""
        from WEBAPI.api import _validate_payload, RunRequest
        from fastapi import HTTPException

        payload = RunRequest(
            script_path="/dummy.py",
            env_vars={"APP_MODE": "test", "DEBUG": "1"},
        )

        with patch("WEBAPI.api._validate_script_path"):
            result = _validate_payload(payload)

        assert result.env_vars == {"APP_MODE": "test", "DEBUG": "1"}
