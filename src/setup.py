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
    executables=exe
)
