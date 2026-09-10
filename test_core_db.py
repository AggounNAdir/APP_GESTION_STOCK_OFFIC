import sys
import traceback
from modules.core import init_db
try:
    init_db()
    print("Core DB init OK")
except Exception:
    traceback.print_exc()
