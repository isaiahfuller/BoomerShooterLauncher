"""
To build:
python setup.py build
AFAIK this still needs python 3.10
"""
import cx_Freeze

exe = [cx_Freeze.Executable("main.py", base="Win32GUI", targetName="BSL.exe")]  # <-- HERE

cx_Freeze.setup(
    name="BSL",
    version="1.1",
    options={"build_exe": {
        "packages": ["models", "views", "controllers", "repositories", "services"],
        "include_files": [("models/assets/iwadinfo.txt", "lib/models/assets/iwadinfo.txt")],
    }},
    executables=exe
)
