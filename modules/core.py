"""
Application de Gestion de Stock Complète
Produits, Clients, Fournisseurs, Achats, Ventes, Versements, Retours, Factures
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
from datetime import datetime, timedelta, date
import os
import sys
import random
import string
import json
import csv
import traceback
import webbrowser
import io
import re
import unicodedata
import tempfile
import subprocess
import shutil
import calendar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import prix_niveaux
# Désactiver les warnings de dépréciation
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import html_renderer as hr  


import logging
import os
import sys
def safe_float(value, default=0):
    """
    Convertit une valeur en float de manière sécurisée.
    Gère les chaînes vides, None, les virgules, etc.
    """
    if value is None:
        return default
    
    try:
        # Si c'est déjà un nombre
        if isinstance(value, (int, float)):
            return float(value)
        
        # Si c'est une chaîne
        if isinstance(value, str):
            text = value.strip()
            if text == '' or text == '-' or text == ' ':
                return default
            
            # Remplacer les virgules par des points
            text = text.replace(',', '.')
            
            # Garder uniquement les chiffres, points et signes moins
            import re
            text = re.sub(r'[^\d.\-]', '', text)
            
            if text == '' or text == '-' or text == '.':
                return default
            
            return float(text)
        
        # Autre type
        return float(value)
        
    except (ValueError, TypeError, AttributeError):
        return default
# ========== CONFIGURATION DES LOGS ==========
def setup_logging():
    """Configure le système de logs pour l'exe"""
    if getattr(sys, 'frozen', False):
        # En exe, on écrit dans un fichier
        exe_dir = os.path.dirname(sys.executable)
        log_dir = os.path.join(exe_dir, 'logs')
    else:
        # En développement, on écrit dans le dossier courant
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    
    # Créer le dossier logs s'il n'existe pas
    os.makedirs(log_dir, exist_ok=True)
    
    # Nom du fichier log avec la date
    log_file = os.path.join(log_dir, f'debug_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # logging.StreamHandler()  # Décommentez pour avoir aussi dans la console
        ]
    )
    
    # Écrire un message de démarrage
    logging.info("="*60)
    logging.info(f"DÉMARRAGE DE L'APPLICATION")
    logging.info(f"Chemin exe: {sys.executable if getattr(sys, 'frozen', False) else 'Script'}")
   # logging.info(f"DB Path: {DB_PATH}")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)
    
    return log_file

# Appeler au début du programme
LOG_FILE = setup_logging()
# ========== CHEMINS ==========
# ✅ Base de données UNIQUE : définie une seule fois dans api/db.py
# (fichier physique : api/gestion_stock.db). Ne PAS la redéfinir ici.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import DB_PATH  # noqa: E402


def get_db_path():
    """Retourne le chemin de la base de données unique (api/gestion_stock.db)"""
    return DB_PATH


def get_app_dir():
    """Dossier de l'application (dossier de l'exe, ou racine du projet en script)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return _PROJECT_ROOT


# profil_config.json reste à la racine de l'application (et non à côté de la base)
PROFIL_CONFIG_PATH = os.path.join(get_app_dir(), "profil_config.json")

# ========== FONCTION DE CENTRAGE ==========
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

# ========== COULEURS & STYLES ==========
from modules.theme import COLORS

CLR_BG      = COLORS["BG"]
CLR_CARD    = COLORS["CARD"]
CLR_TEXT    = COLORS["TEXT"]
CLR_MUTED   = COLORS["MUTED"]
CLR_ACCENT  = COLORS["ACCENT"]
CLR_GREEN   = COLORS["GREEN"]
CLR_RED     = COLORS["RED"]
CLR_ORANGE  = COLORS["ORANGE"]
CLR_BORDER  = COLORS["BORDER"]
CLR_SIDEBAR = COLORS["SIDEBAR"]
CLR_INPUT   = COLORS["INPUT"]
CLR_PURPLE  = "#8b5cf6"  


def _darken(hex_color):
    h = hex_color.lstrip("#")
    r,g,b = tuple(int(h[i:i+2],16) for i in (0,2,4))
    return "#{:02x}{:02x}{:02x}".format(max(r-20,0), max(g-20,0), max(b-20,0))
def format_montant(montant):
    """Formate un montant avec une largeur fixe pour éviter le débordement"""
    return f"{montant:>14,.2f} DA"  # 14 caractères de large minimum
def style_btn(btn, color=CLR_ACCENT, fg="white"):
    btn.configure(bg=color, fg=fg, relief="flat", cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6)
    btn.bind("<Enter>", lambda e: btn.config(bg=_darken(color)))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))

def lbl(parent, text, size=9, bold=False, italic=False, color=CLR_TEXT, **kw):
    """Crée un label avec style par défaut"""
    # Construire le style
    style = "normal"
    if bold and italic:
        style = "bold italic"
    elif bold:
        style = "bold"
    elif italic:
        style = "italic"
    
    # Si bg n'est pas dans kw, utiliser la couleur par défaut
    if 'bg' not in kw:
        kw['bg'] = parent["bg"] if hasattr(parent, "bg") else CLR_BG
    
    w = tk.Label(parent, text=text, fg=color, font=("Segoe UI", size, style), **kw)
    return w
def entry(parent, width=20, **kw):
    e = tk.Entry(parent, bg=CLR_INPUT, fg=CLR_TEXT, insertbackground=CLR_TEXT,
                 relief="flat", width=width,
                 highlightthickness=1, highlightbackground=CLR_BORDER,
                 highlightcolor=CLR_ACCENT, **kw)
    return e

def combo(parent, values, width=18, **kw):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
                    fieldbackground=CLR_INPUT, background=CLR_INPUT,
                    foreground=CLR_TEXT, arrowcolor=CLR_TEXT,
                    selectbackground=CLR_INPUT)
    c = ttk.Combobox(parent, values=values, width=width, style="Dark.TCombobox", **kw)
    return c

def make_tree(parent, columns, col_widths=None):
    """Crée un arbre avec le même style de fond que la « Grille des Prix »
    (fond clair par défaut du thème, sans style sombre appliqué)."""
    frame = tk.Frame(parent, bg=CLR_CARD)
    vsb = ttk.Scrollbar(frame, orient="vertical")
    hsb = ttk.Scrollbar(frame, orient="horizontal")

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.configure(command=tree.yview)
    hsb.configure(command=tree.xview)

    for i, col in enumerate(columns):
        w = col_widths[i] if col_widths and i < len(col_widths) else 120
        tree.heading(col, text=col)
        # CENTRER L'EN-TÊTE
        tree.heading(col, text=col, anchor="center")
        # CENTRER LES DONNÉES
        tree.column(col, width=w, minwidth=60, anchor="center")

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    return frame, tree

# ========== FONCTIONS UTILITAIRES ==========
def valider_date(date_str):
    """Vérifie que la date est au format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False

def parse_decimal(value):
    """Normaliser une saisie de montant/quantité en float."""
    text = str(value).strip().replace("\u00A0", " ")
    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    return float(text)

def normalize_barcode_input(value):
    """Normalisation des codes-barres: purement numériques."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc")
    text = unicodedata.normalize("NFKC", text)
    azerty_map = {
        '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
        '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'
    }
    if any(ch in azerty_map for ch in text):
        text = ''.join(azerty_map.get(ch, ch) for ch in text)
    digits_only = re.sub(r"[^0-9]", "", text)
    return digits_only

def next_numero(prefix, table="bons_vente"):
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().strftime("%Y%m")
    tables = {
        "BA": "bons_achat", "BV": "bons_vente", "FC": "factures",
        "VC": "versements_clients", "VF": "versements_fournisseurs",
        "RV": "retours_vente", "RA": "retours_achat"
    }
    tbl = tables.get(prefix, table)
    c.execute(f"SELECT numero FROM {tbl} WHERE numero LIKE ?", (f"{prefix}{today}%",))
    rows = c.fetchall()
    conn.close()
    max_n = 0
    for row in rows:
        try:
            n = int(row[0].replace(prefix, "").replace(today, ""))
            if n > max_n:
                max_n = n
        except (ValueError, AttributeError):
            continue
    return f"{prefix}{today}{max_n + 1:04d}"

def next_numero_tiers(prefix, tiers_id, table="bons_vente"):
    """Génère un numéro séquentiel par tiers (client ou fournisseur)"""
    conn = get_conn()
    c = conn.cursor()
    tables = {
        "BA": "bons_achat", "BV": "bons_vente",
    }
    tbl = tables.get(prefix, table)
    
    # Chercher les numéros existants pour ce tiers
    if tbl == "bons_vente":
        c.execute(f"SELECT numero FROM {tbl} WHERE client_id = ? AND numero LIKE ?", 
                  (tiers_id, f"{prefix}-%"))
    else:
        c.execute(f"SELECT numero FROM {tbl} WHERE fournisseur_id = ? AND numero LIKE ?", 
                  (tiers_id, f"{prefix}-%"))
    rows = c.fetchall()
    conn.close()
    
    max_n = 0
    for row in rows:
        try:
            # Format: BV-00042 → extraire le numéro après le dernier "-"
            n = int(row[0].split("-")[-1])
            if n > max_n:
                max_n = n
        except (ValueError, IndexError):
            continue
    
    return f"{prefix}-{tiers_id:05d}-{max_n + 1:04d}"
def generer_code_sequentiel(prefix, table, champ_code="code", longueur_num=3):
    current_year = datetime.now().strftime("%Y")
    conn = get_conn()
    try:
        pattern = f"{prefix}-{current_year}-%"
        results = conn.execute(
            f"SELECT {champ_code} FROM {table} WHERE {champ_code} LIKE ?",
            (pattern,)
        ).fetchall()
        max_num = 0
        for row in results:
            try:
                code_val = row[0]
                parts = code_val.split('-')
                if len(parts) >= 3:
                    num_str = parts[-1]
                    num = int(num_str)
                    if num > max_num:
                        max_num = num
            except (ValueError, IndexError, TypeError):
                continue
        nouveau_num = max_num + 1
        nouveau_code = f"{prefix}-{current_year}-{nouveau_num:0{longueur_num}d}"
        return nouveau_code
    finally:
        conn.close()

def generer_code_aleatoire(prefix, longueur=4):
    caracteres = string.ascii_uppercase + string.digits
    partie_aleatoire = ''.join(random.choices(caracteres, k=longueur))
    return f"{prefix}-{partie_aleatoire}"

def generer_code_unique(prefix, table, champ_code="code", mode="sequentiel"):
    if mode == "sequentiel":
        return generer_code_sequentiel(prefix, table, champ_code)
    else:
        conn = get_conn()
        try:
            code_unique = False
            max_attempts = 100
            attempts = 0
            code = None
            while not code_unique and attempts < max_attempts:
                code = generer_code_aleatoire(prefix)
                result = conn.execute(f"SELECT id FROM {table} WHERE {champ_code} = ?", (code,)).fetchone()
                if not result:
                    code_unique = code
                    break
                attempts += 1
            if not code_unique:
                code_unique = f"{prefix}-{int(datetime.now().timestamp())}"
            return code_unique
        finally:
            conn.close()

# ========== FONCTIONS D'EXPORT ==========
def export_to_csv(data, filename, headers):
    """Exporter des données vers un fichier CSV"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
        return True
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
        return False

def export_to_html(data, filename, title, headers):
    """Exporter des données vers un fichier HTML"""
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #3b82f6; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p>Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <table>
                <thead>
                    <tr>"""
        for header in headers:
            html_content += f"<th>{header}</th>"
        html_content += """
                    </tr>
                </thead>
                <tbody>"""
        for row in data:
            html_content += "<tr>"
            for cell in row:
                html_content += f"<td>{cell}</td>"
            html_content += "</tr>"
        html_content += """
                </tbody>
            </table>
        </body>
        </html>
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return True
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'export HTML: {str(e)}")
        return False

def print_preview(data, title, headers, footer_text=None):
    """Afficher un aperçu avant impression avec options PDF et imprimante"""
    preview = tk.Toplevel()
    preview.title(f"Aperçu - {title}")
    preview.geometry("900x700")
    preview.configure(bg=CLR_BG)
    preview.lift()
    preview.attributes('-topmost', True)
    preview.after(100, lambda: preview.attributes('-topmost', False))
    preview.focus_force()
    center_window(preview, 900, 700)
    
    main_frame = tk.Frame(preview, bg=CLR_BG)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    text_frame = tk.Frame(main_frame, bg=CLR_BG)
    text_frame.pack(fill="both", expand=True)
    
    text_widget = tk.Text(text_frame, wrap="none", font=("Courier", 9), bg="white", fg="black")
    scrollbar_y = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    scrollbar_x = tk.Scrollbar(text_frame, orient="horizontal", command=text_widget.xview)
    text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
    
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar_y.pack(side="right", fill="y")
    scrollbar_x.pack(side="bottom", fill="x")
    
    # Construire le contenu texte
    content = f"\n{'='*100}\n"
    content += f"{title:^100}\n"
    content += f"{'='*100}\n"
    content += f"Date d'édition: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    content += f"{'-'*100}\n\n"
    
    # Construction du tableau avec largeur fixe
    col_widths = []
    for header in headers:
        col_widths.append(max(len(str(header)), 15))  # Largeur minimale
    
    # En-têtes
    header_line = ""
    for i, header in enumerate(headers):
        header_line += f"{str(header):<{col_widths[i]}}"
    content += header_line + "\n"
    content += "-" * sum(col_widths) + "\n"
    
    # Données
    for row in data:
        line = ""
        for i, cell in enumerate(row):
            line += f"{str(cell):<{col_widths[i]}}"
        content += line + "\n"
    
    content += f"\n{'-'*sum(col_widths)}\n"
    content += f"Total lignes: {len(data)}\n"
    if footer_text:
        content += f"{footer_text}\n"
    
    text_widget.insert("1.0", content)
    text_widget.configure(state="disabled")
    
    btn_frame = tk.Frame(preview, bg=CLR_BG)
    btn_frame.pack(fill="x", padx=10, pady=10)
    
    def print_to_printer():
        """Impression avec mise en page HTML pour un meilleur rendu"""
        try:
            # Construction du HTML avec styles d'impression
            html_content = build_print_html(data, title, headers, footer_text)
            
            # Ouvrir dans le navigateur pour impression
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            # Ouvrir dans le navigateur
            webbrowser.open(temp_file.name)
            
            messagebox.showinfo(
                "Impression", 
                "📄 Le document s'ouvre dans votre navigateur.\n\n"
                "Pour imprimer :\n"
                "• Ctrl+P (Windows/Linux)\n"
                "• Cmd+P (Mac)\n\n"
                "L'en-tête du tableau sera en blanc avec texte noir gras."
            )
            
            # Supprimer le fichier après un délai
            preview.after(30000, lambda: os.unlink(temp_file.name))
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'impression: {str(e)}")
    
    def build_print_html(data, title, headers, footer_text=None):
        """Construire le HTML pour l'impression avec styles"""
        # Largeurs des colonnes
        col_widths = []
        for header in headers:
            col_widths.append(max(len(str(header)), 15))
        
        # Construire le tableau HTML
        table_html = "<table>\n"
        
        # En-tête avec fond blanc et texte noir gras
        table_html += "    <thead>\n"
        table_html += "        <tr>\n"
        for i, header in enumerate(headers):
            table_html += f'            <th style="background-color: #ffffff !important; color: #000000 !important; font-weight: bold !important; border: 1px solid #000000; padding: 8px; text-align: left;">{header}</th>\n'
        table_html += "        </tr>\n"
        table_html += "    </thead>\n"
        
        # Corps du tableau
        table_html += "    <tbody>\n"
        for row in data:
            table_html += "        <tr>\n"
            for i, cell in enumerate(row):
                table_html += f'            <td style="border: 1px solid #cccccc; padding: 6px; text-align: left;">{cell}</td>\n'
            table_html += "        </tr>\n"
        table_html += "    </tbody>\n"
        table_html += "</table>\n"
        
        # Construction complète du HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                /* Styles pour l'écran */
                body {{
                    font-family: 'Courier New', monospace;
                    margin: 20px;
                    background-color: #ffffff;
                    color: #000000;
                }}
                h1 {{
                    color: #333333;
                    text-align: center;
                    font-size: 18px;
                }}
                .header-info {{
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 12px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    font-size: 11px;
                }}
                
                /* ✅ STYLES D'IMPRESSION */
                @media print {{
                    body {{
                        margin: 15px;
                        font-size: 10px;
                    }}
                    h1 {{
                        font-size: 16px;
                        color: #000000 !important;
                    }}
                    
                    /* En-têtes de tableau : fond blanc, texte noir gras */
                    th {{
                        background-color: #ffffff !important;
                        color: #000000 !important;
                        font-weight: bold !important;
                        border: 1px solid #000000 !important;
                        padding: 6px !important;
                    }}
                    
                    /* Corps du tableau */
                    td {{
                        border: 1px solid #999999 !important;
                        padding: 4px !important;
                        color: #000000 !important;
                    }}
                    
                    /* Éviter les coupures de page */
                    table {{
                        page-break-inside: auto;
                    }}
                    tr {{
                        page-break-inside: avoid;
                        page-break-after: auto;
                    }}
                    thead {{
                        display: table-header-group;
                    }}
                    
                    /* Désactiver tous les fonds colorés */
                    * {{
                        background-color: #ffffff !important;
                        color: #000000 !important;
                    }}
                    
                    /* Footer */
                    .footer {{
                        margin-top: 20px;
                        font-size: 9px;
                        text-align: center;
                        color: #000000 !important;
                    }}
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="header-info">
                Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
            <hr>
            
            {table_html}
            
            <div class="footer">
                <hr>
                Total lignes: {len(data)}
                {f'<br>{footer_text}' if footer_text else ''}
            </div>
        </body>
        </html>
        """
        return html_content
    
    def export_to_html_file():
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialfile=f"{title.replace(' ', '_')}.html"
        )
        if filename:
            html_content = build_print_html(data, title, headers, footer_text)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            messagebox.showinfo("Succès", f"Fichier HTML créé: {filename}")
            if messagebox.askyesno("Ouverture", "Voulez-vous ouvrir le fichier ?"):
                webbrowser.open(filename)
    
    def export_csv_from_preview():
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{title.replace(' ', '_')}.csv"
        )
        if filename:
            export_to_csv(data, filename, headers)
            messagebox.showinfo("Succès", f"Fichier CSV créé: {filename}")
    
    btn_line1 = tk.Frame(btn_frame, bg=CLR_BG)
    btn_line1.pack(pady=5)
    
    tk.Button(btn_line1, text="🖨 Imprimer sur imprimante", command=print_to_printer,
             bg=CLR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
             padx=15, pady=8, cursor="hand2").pack(side="left", padx=10)
    
    btn_line2 = tk.Frame(btn_frame, bg=CLR_BG)
    btn_line2.pack(pady=5)
    
    tk.Button(btn_line2, text="🌐 Exporter en HTML", command=export_to_html_file,
             bg=CLR_ORANGE, fg="white", font=("Segoe UI", 10, "bold"),
             padx=15, pady=8, cursor="hand2").pack(side="left", padx=10)
    
    tk.Button(btn_line2, text="💾 Exporter CSV", command=export_csv_from_preview,
             bg=CLR_GREEN, fg="white", font=("Segoe UI", 10, "bold"),
             padx=15, pady=8, cursor="hand2").pack(side="left", padx=10)
    
    tk.Button(btn_line2, text="❌ Fermer", command=preview.destroy,
             bg=CLR_RED, fg="white", font=("Segoe UI", 10, "bold"),
             padx=15, pady=8, cursor="hand2").pack(side="left", padx=10)

# ========== PROFILS ENTREPRISE ==========
def get_profil_by_type(type_document):
    """Retourne le profil configuré pour le type de document."""
    config_file = PROFIL_CONFIG_PATH
    profil_code = None
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                profil_key = config.get(type_document, "")
                if profil_key and " - " in profil_key:
                    profil_code = profil_key.split(" - ")[0]
        except Exception:
            pass
    conn = get_conn()
    try:
        if profil_code:
            profil = conn.execute(
                "SELECT * FROM profils_entreprise WHERE code = ?",
                (profil_code,)
            ).fetchone()
            if profil:
                return dict(profil)
        profil = conn.execute(
            "SELECT * FROM profils_entreprise WHERE est_defaut = 1 LIMIT 1"
        ).fetchone()
        return dict(profil) if profil else None
    finally:
        conn.close()

def get_active_profil():
    """Retourne le profil actif par défaut (pour compatibilité)"""
    conn = get_conn()
    profil = conn.execute(
        "SELECT * FROM profils_entreprise WHERE est_defaut = 1 LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(profil) if profil else None
# Ajouter cette fonction après les imports (vers ligne 200)

def get_bon_type(numero):
    """
    Détermine le type d'un bon à partir de son numéro
    Retourne: 'vente', 'achat', 'solde_initial', 'avoir', 'normal'
    """
    if numero.startswith('SI-C-'):
        return 'solde_initial_client'
    elif numero.startswith('SI-F-'):
        return 'solde_initial_fournisseur'
    elif numero.startswith('AVOIR-C-'):
        return 'avoir_client'
    elif numero.startswith('AVOIR-F-'):
        return 'avoir_fournisseur'
    elif numero.startswith('BV-'):
        return 'vente'
    elif numero.startswith('BA-'):
        return 'achat'
    else:
        return 'normal'
# ========== BASE DE DONNÉES ==========
# ✅ Création des tables ET connexion : UNE SEULE implémentation, dans api/
#    (api/schema.py pour le schéma, api/db.py pour get_conn / init_db).
#    Ne PAS recréer de tables ici : les ajouter dans api/schema.py.
from api.db import get_conn  # noqa: E402,F401  (ré-exporté : from modules.core import get_conn)
from api.db import init_db as _init_db_unique  # noqa: E402


def init_db():
    """Initialise la base unique (api/schema.py). N'interrompt pas l'application
    si l'initialisation échoue : l'erreur est journalisée (voir dossier logs/)."""
    try:
        _init_db_unique()
    except Exception as e:
        logging.error(f"Erreur lors de l'initialisation de la base: {e}")
        print(f"Erreur lors de l'initialisation: {e}")


def calculer_pmp(conn, produit_id, nouvelle_quantite, nouveau_prix_achat,
                 stock_actuel_override=None, cout_actuel_override=None):
    """
    ✅ AMÉLIORÉE : Calcule le nouveau PMP avec gestion des cas extrêmes
    """
    if stock_actuel_override is not None:
        stock_actuel = float(stock_actuel_override)
        cout_actuel = float(cout_actuel_override or 0)
    else:
        cursor = conn.execute(
            "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
            (produit_id,)
        )
        produit = cursor.fetchone()
        if not produit:
            return nouveau_prix_achat, nouvelle_quantite * nouveau_prix_achat
        stock_actuel = float(produit["stock_actuel"] or 0)
        cout_actuel = float(produit["cout_total_stock"] or 0)
    
    # ✅ Si le stock actuel est 0, le nouveau PMP = prix d'achat
    if stock_actuel <= 0:
        nouveau_cout_total = nouvelle_quantite * nouveau_prix_achat
        nouveau_stock_total = nouvelle_quantite
        if nouveau_stock_total > 0:
            nouveau_pmp = nouveau_cout_total / nouveau_stock_total
        else:
            nouveau_pmp = nouveau_prix_achat
    else:
        nouveau_cout_total = cout_actuel + (nouvelle_quantite * nouveau_prix_achat)
        nouveau_stock_total = stock_actuel + nouvelle_quantite
        
        if nouveau_stock_total > 0:
            nouveau_pmp = nouveau_cout_total / nouveau_stock_total
        else:
            nouveau_pmp = nouveau_prix_achat
    
    return nouveau_pmp, nouveau_cout_total

def recalculer_cout_stock_apres_sortie(conn, produit_id, quantite_sortie):
    """
    Recalcule le coût du stock après une sortie (vente, sortie de stock).
    ✅ Règle comptable / ERP : La sortie de stock diminue le stock et la valeur totale au PMP,
    mais NE CHANGE PAS le PMP unitaire des pièces restantes.
    """
    produit = conn.execute(
        "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
        (produit_id,)
    ).fetchone()
    
    if not produit:
        return
    
    stock_actuel = float(produit["stock_actuel"] or 0)
    cout_actuel = float(produit["cout_total_stock"] or 0)
    pmp = float(produit["prix_moyen_pondere"] or 0)
    
    if pmp <= 0 and stock_actuel > 0:
        pmp = cout_actuel / stock_actuel
    
    # Sortie au PMP
    nouveau_stock = stock_actuel - quantite_sortie
    reduction = quantite_sortie * pmp
    nouveau_cout = max(0.0, cout_actuel - reduction)
    
    # Le PMP unitaire reste inchangé tant qu'il reste du stock ou en négatif
    nouveau_pmp = pmp
    
    conn.execute(
        "UPDATE produits SET stock_actuel = ?, prix_moyen_pondere = ?, cout_total_stock = ? WHERE id=?",
        (nouveau_stock, nouveau_pmp, nouveau_cout, produit_id)
    )
def entree_stock_annulation_vente(conn, produit_id, quantite):
    """
    Réintègre du stock suite à l'annulation/suppression d'une vente,
    ou à un retour client.
    ✅ CORRECTION : Utiliser le PMP actuel pour réintégrer au bon coût
    """
    produit = conn.execute(
        "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
        (produit_id,)
    ).fetchone()
    
    if not produit:
        return
    
    stock_actuel = produit["stock_actuel"] or 0
    cout_actuel = produit["cout_total_stock"] or 0
    pmp_actuel = produit["prix_moyen_pondere"] or 0
    
    # ✅ CORRECTION : Si PMP = 0, utiliser le prix d'achat moyen
    if pmp_actuel <= 0 and stock_actuel > 0:
        pmp_actuel = cout_actuel / stock_actuel
    
    # ✅ Si pas de PMP et pas de stock, utiliser 0
    if pmp_actuel <= 0:
        pmp_actuel = 0
    
    # ✅ Réintégrer au PMP actuel (coût réel du stock)
    nouveau_stock = stock_actuel + quantite
    nouveau_cout = cout_actuel + (quantite * pmp_actuel)
    
    if nouveau_stock > 0:
        nouveau_pmp = nouveau_cout / nouveau_stock
    else:
        nouveau_pmp = 0
    
    conn.execute(
        "UPDATE produits SET stock_actuel = ?, prix_moyen_pondere = ?, cout_total_stock = ? WHERE id=?",
        (nouveau_stock, nouveau_pmp, nouveau_cout, produit_id)
    )
def recalculer_pmp_apres_sortie_complete(conn, produit_id):
    """
    ✅ CORRECTION : Recalcule le PMP après une sortie complète
    """
    produit = conn.execute(
        "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
        (produit_id,)
    ).fetchone()
    
    if not produit:
        return
    
    stock_actuel = produit["stock_actuel"] or 0
    cout_actuel = produit["cout_total_stock"] or 0
    
    if stock_actuel > 0 and cout_actuel > 0:
        nouveau_pmp = cout_actuel / stock_actuel
    else:
        nouveau_pmp = 0
        if stock_actuel == 0:
            conn.execute(
                "UPDATE produits SET cout_total_stock = 0 WHERE id=?",
                (produit_id,)
            )
    
    conn.execute(
        "UPDATE produits SET prix_moyen_pondere = ? WHERE id=?",
        (nouveau_pmp, produit_id)
    )
def inverser_stock_achat(conn, lignes):
    """
    Annule l'effet stock/PMP d'un bon d'achat.
    ✅ CORRECTION : on retire le coût EXACT de ce lot d'achat
    (quantite * prix_unitaire de la ligne, ou son "total"), au lieu d'une
    proportion du coût total du stock actuel. L'ancienne méthode faussait
    le PMP dès que d'autres mouvements de stock avaient eu lieu entre-temps.
    """
    for l in lignes:
        produit = conn.execute(
            "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
            (l["produit_id"],)
        ).fetchone()

        if not produit:
            continue

        stock_actuel = produit["stock_actuel"] or 0
        cout_actuel = produit["cout_total_stock"] or 0

        # Coût exact du lot acheté (tel qu'enregistré sur la ligne d'achat)
        try:
            cout_ligne = float(l["total"])
        except (KeyError, TypeError, IndexError):
            cout_ligne = l["quantite"] * l["prix_unitaire"]

        nouvelle_quantite = max(0.0, stock_actuel - l["quantite"])
        nouveau_cout = max(0.0, cout_actuel - cout_ligne)

        if nouvelle_quantite > 0 and nouveau_cout > 0:
            nouveau_pmp = nouveau_cout / nouvelle_quantite
        else:
            nouveau_pmp = 0
            nouveau_cout = 0

        conn.execute(
            "UPDATE produits SET stock_actuel = ?, prix_moyen_pondere = ?, cout_total_stock = ? WHERE id=?",
            (nouvelle_quantite, nouveau_pmp, nouveau_cout, l["produit_id"])
        )