import sys
import traceback
import tkinter as tk
from modules.core import init_db
try:
    init_db()
    from modules.app import App
    print("App import & DB init OK")
except Exception:
    traceback.print_exc()
