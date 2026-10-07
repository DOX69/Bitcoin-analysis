"""The cron console script must import forecast without the checkout on sys.path."""

import subprocess
import sys


def test_installed_forecast_is_importable_without_current_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import forecast.pipeline; import forecast.jobs"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
