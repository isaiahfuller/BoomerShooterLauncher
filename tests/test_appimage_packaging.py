"""Check the Linux packaging entry point without downloading build tools."""

import os
from pathlib import Path
import platform
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(platform.system() != "Linux", reason="Linux packaging")


def test_apprun_preserves_arguments_working_directory_and_environment(tmp_path):
    appdir = tmp_path / "application with spaces.AppDir"
    appdir.mkdir()
    shutil.copyfile(ROOT / "packaging/linux/AppRun", appdir / "AppRun")
    executable = appdir / "boomershooterlauncher"
    executable.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$PWD" "$LD_LIBRARY_PATH" "$QT_PLUGIN_PATH" "$@"\n'
    )
    executable.chmod(0o755)
    working = tmp_path / "external game"
    working.mkdir()
    environment = dict(os.environ, LD_LIBRARY_PATH="/host/libraries", QT_PLUGIN_PATH="/host/plugins")
    result = subprocess.run(
        ["sh", str(appdir / "AppRun"), "argument with spaces", "--debug"],
        cwd=working, env=environment, text=True, capture_output=True, check=True,
    )
    assert result.stdout.splitlines() == [
        str(working), "/host/libraries", "/host/plugins", "argument with spaces", "--debug"
    ]


def test_packaging_requires_a_frozen_build(tmp_path):
    if platform.machine() != "x86_64":
        pytest.skip("Packaging targets x86_64")
    result = subprocess.run(
        ["bash", str(ROOT / "packaging/build-appimage.sh"), str(tmp_path / "missing")],
        cwd=tmp_path, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "Missing frozen executable" in result.stderr
