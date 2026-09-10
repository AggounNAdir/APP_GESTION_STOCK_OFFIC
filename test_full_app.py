import sys
import traceback
from modules.core import init_db
try:
    init_db()
    from modules.app import App
    print("App load OK")
except Exception:
    traceback.print_exc()
