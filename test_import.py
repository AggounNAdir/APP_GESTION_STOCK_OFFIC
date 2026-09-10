import sys
import traceback
try:
    from modules.core import *
    from modules.app import App
    print("Imports OK")
except Exception:
    traceback.print_exc()
