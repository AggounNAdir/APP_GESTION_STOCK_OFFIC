"""
Fonctions utilitaires de l'application (conversion, centrage fenêtres, numéros séquentiels).
"""

import re
from datetime import datetime
import sqlite3
from config import DB_PATH

def safe_float(value, default=0):
    """
    Convertit une valeur en float de manière sécurisée.
    Gère les chaînes vides, None, les virgules, etc.
    """
    if value is None:
        return default
    
    try:
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            text = value.strip()
            if text == '' or text == '-' or text == ' ':
                return default
            
            text = text.replace(',', '.')
            text = re.sub(r'[^\d.\-]', '', text)
            
            if text == '' or text == '-' or text == '.':
                return default
            
            return float(text)
        
        return float(value)
        
    except (ValueError, TypeError, AttributeError):
        return default

def parse_decimal(value):
    """Alias pour safe_float ou parsing strict de décimaux"""
    return safe_float(value, 0.0)

def center_window(window, width=None, height=None):
    """Centre une fenêtre sur l'écran"""
    window.update_idletasks()
    
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")

def is_valid_date(date_str):
    """Vérifie si une chaîne est une date valide au format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False

def next_numero(prefix, table="bons_vente"):
    """Génère le prochain numéro séquentiel"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y%m")
    tables = {
        "BA": "bons_achat", "BV": "bons_vente", "FC": "factures",
        "VC": "versements_clients", "VF": "versements_fournisseurs",
        "RV": "retours_vente", "RA": "retours_achat"
    }
    tbl = tables.get(prefix, table)
    
    try:
        c.execute(f"SELECT numero FROM {tbl} WHERE numero LIKE ?", (f"{prefix}{today}%",))
        rows = c.fetchall()
    except Exception:
        conn.close()
        return f"{prefix}{today}0001"
    
    conn.close()
    
    max_n = 0
    for r in rows:
        num = r[0]
        try:
            suffix = num[len(prefix) + 6:]
            n = int(suffix)
            if n > max_n:
                max_n = n
        except (ValueError, AttributeError):
            continue
    return f"{prefix}{today}{max_n + 1:04d}"

def next_numero_tiers(prefix, tiers_id, table="bons_vente"):
    """Génère un numéro séquentiel par tiers (client ou fournisseur)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y%m")
    tables = {
        "BA": "bons_achat", "BV": "bons_vente",
    }
    tbl = tables.get(prefix, table)
    
    try:
        if tbl == "bons_vente":
            c.execute(f"SELECT numero FROM {tbl} WHERE client_id = ? AND numero LIKE ?", 
                      (tiers_id, f"{prefix}-%"))
        else:
            c.execute(f"SELECT numero FROM {tbl} WHERE fournisseur_id = ? AND numero LIKE ?", 
                      (tiers_id, f"{prefix}-%"))
        rows = c.fetchall()
    except Exception:
        conn.close()
        return f"{prefix}-{tiers_id}-{today}-0001"
    
    conn.close()
    
    max_num = 0
    for r in rows:
        num = r[0]
        try:
            parts = num.split("-")
            if parts:
                num = int(parts[-1])
                if num > max_num:
                    max_num = num
        except (ValueError, IndexError, TypeError):
            continue
    nouveau_num = max_num + 1
    return f"{prefix}-{tiers_id}-{today}-{nouveau_num:04d}"
