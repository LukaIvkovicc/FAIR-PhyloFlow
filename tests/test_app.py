from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


@pytest.mark.parametrize(
    ("button", "command"),
    [("Check", "check"), ("Plan", "plan"), ("Run", "run"), ("Report", "report")],
)
def test_app_buttons_use_selected_config_and_report_success(button: str, command: str) -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    app.text_input[0].set_value("custom/project.yaml").run()
    result = subprocess.CompletedProcess([], 0, stdout="Generated output", stderr="")
    with patch("subprocess.run", return_value=result) as run:
        next(item for item in app.button if item.label == button).click().run()
    argv = ["fair-phyloflow", command, "custom/project.yaml"]
    if command == "run":
        argv.append("--no-execute")
    run.assert_called_once_with(argv, capture_output=True, text=True, timeout=600, check=False)
    assert not app.exception
    assert app.success[0].value == "Command completed successfully."
    assert app.code[0].value == "Generated output"


def test_app_shows_command_failure_and_diagnostics() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    result = subprocess.CompletedProcess([], 2, stdout="", stderr="Invalid configuration")
    with patch("subprocess.run", return_value=result):
        app.button[0].click().run()
    assert not app.exception
    assert app.error[0].value == "Command failed with exit code 2."
    assert "Invalid configuration" in app.code[0].value
    assert not app.success
