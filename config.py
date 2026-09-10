"""
Configuration globale, constantes, couleurs, chemins et logs de l'application.
"""

import os
import sys
import logging
from datetime import datetime

# ========== CONFIGURATION DES LOGS ==========
def setup_logging():
    """Configure le système de logs pour l'exe ou le script"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        log_dir = os.path.join(exe_dir, 'logs')
    else:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'debug_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )
    
    logging.info("="*60)
    logging.info(f"DÉMARRAGE DE L'APPLICATION (MODE MODULAIRE)")
    logging.info(f"Chemin exe/script: {sys.executable if getattr(sys, 'frozen', False) else 'Script Python'}")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)
    
    return log_file

LOG_FILE = setup_logging()

# ========== CHEMINS ==========
def get_db_path():
    """Retourne le chemin correct de la base de données pour l'exe ou le script"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "gestion_stock.db")
    else:
        return "gestion_stock.db"

DB_PATH = get_db_path()

# ========== COULEURS & STYLES ==========
CLR_BG      = "#1e2736"
CLR_SIDEBAR = "#16202e"
CLR_CARD    = "#253146"
CLR_ACCENT  = "#3b82f6"
CLR_GREEN   = "#22c55e"
CLR_RED     = "#ef4444"
CLR_ORANGE  = "#f97316"
CLR_TEXT    = "#e2e8f0"
CLR_MUTED   = "#94a3b8"
CLR_INPUT   = "#2d3f57"
