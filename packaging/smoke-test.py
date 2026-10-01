"""Check that a packaged GUI survives startup, without writing real user settings.

This is a startup check, not an interactive UI or game-launch test.
Pass an executable path; use QT_QPA_PLATFORM=xcb under Xvfb to check Linux X11.
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    executable = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="bsl-smoke-") as temporary:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        env.update(HOME=temporary, XDG_CONFIG_HOME=temporary, XDG_DATA_HOME=temporary)
        # On Windows the application uses QSettings' registry backend; run this
        # only on a disposable CI account, not to isolate an existing user's settings.
        log = Path(temporary) / "startup.log"
        with log.open("w+") as output:
            process = subprocess.Popen([str(executable)], cwd=temporary, env=env,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                try:
                    code = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("Application survived the 10-second startup check.")
                else:
                    raise RuntimeError(f"Application exited during startup (code {code})")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                output.seek(0)
                print(output.read())


if __name__ == "__main__":
    main()
