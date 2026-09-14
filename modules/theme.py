import json
import os

THEMES = {
    "clair": {
        "name": "Clair",
        "emoji": "☀️",
        "BG": "#F4F7F6", "CARD": "#FFFFFF", "TEXT": "#2D3436",
        "MUTED": "#636E72", "ACCENT": "#0984E3", "GREEN": "#00B894",
        "RED": "#D63031", "ORANGE": "#E17055", "BORDER": "#DFE6E9",
        "SIDEBAR": "#E4E7E6", "INPUT": "#FFFFFF"
    },
    "sombre": {
        "name": "Sombre",
        "emoji": "🌙",
        "BG": "#1e2736", "CARD": "#253146", "TEXT": "#e2e8f0",
        "MUTED": "#94a3b8", "ACCENT": "#3b82f6", "GREEN": "#22c55e",
        "RED": "#ef4444", "ORANGE": "#f97316", "BORDER": "#334155",
        "SIDEBAR": "#16202e", "INPUT": "#2d3f57"
    },
    "bleu_nuit": {
        "name": "Bleu Nuit",
        "emoji": "🌃",
        "BG": "#0F172A", "CARD": "#1E293B", "TEXT": "#F1F5F9",
        "MUTED": "#94A3B8", "ACCENT": "#38BDF8", "GREEN": "#34D399",
        "RED": "#FB7185", "ORANGE": "#FBBF24", "BORDER": "#334155",
        "SIDEBAR": "#0B1120", "INPUT": "#1E293B"
    },
    "emeraude": {
        "name": "Émeraude",
        "emoji": "🌿",
        "BG": "#ECFDF5", "CARD": "#FFFFFF", "TEXT": "#064E3B",
        "MUTED": "#6B7280", "ACCENT": "#059669", "GREEN": "#10B981",
        "RED": "#DC2626", "ORANGE": "#D97706", "BORDER": "#D1FAE5",
        "SIDEBAR": "#D1FAE5", "INPUT": "#FFFFFF"
    }
}

THEME_KEYS = list(THEMES.keys())

def load_theme():
    """Charge le thème depuis le fichier config.json ou retourne le thème sombre par défaut"""
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                theme_name = config.get("theme", "sombre")
                return THEMES.get(theme_name, THEMES["sombre"])
    except:
        pass
    return THEMES["sombre"]

def save_theme(theme_name):
    """Sauvegarde le nom du thème dans config.json"""
    try:
        config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        config["theme"] = theme_name
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

def get_current_theme_name():
    """Retourne le nom du thème actuellement configuré"""
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                return config.get("theme", "sombre")
    except:
        pass
    return "sombre"

COLORS = load_theme()
