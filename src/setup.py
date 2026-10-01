"""
To build:
python setup.py build
"""
import sys

import cx_Freeze

target_name = "boomershooterlauncher" if sys.platform.startswith("linux") else "BSL.exe"
exe = [cx_Freeze.Executable("src/main.py", base="gui", target_name=target_name)]  # <-- HERE

cx_Freeze.setup(
    name="BSL",
    version="1.1",
    options={"build_exe": {
        "packages": ["models", "views", "controllers", "repositories", "services"],
        "include_files": [("src/models/assets/iwadinfo.txt", "lib/models/assets/iwadinfo.txt")],
    }},
    executables=exe
)
