import sys
from cx_Freeze import setup, Executable

base = None

if sys.platform == 'win32':
    base = "Win32GUI"

executables = [Executable("sweat_capacity.py", base=base)]

setup(
    name = "Sweat Capacity PC Application",
    version = "0.1",
    description = "Sweat Capacity BLE Application",
    executables = executables
    )
    