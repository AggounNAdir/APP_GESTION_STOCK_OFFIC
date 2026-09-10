import sys
import traceback
from modules.core import init_db
try:
    init_db()
    print("DB Init OK")
except Exception:
    traceback.print_exc()
