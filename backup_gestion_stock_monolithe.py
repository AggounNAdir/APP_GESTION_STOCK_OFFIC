
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
from modules.situationpage import SituationPage


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
def get_db_path():
    """Retourne le chemin correct de la base de données pour l'exe ou le script"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "gestion_stock.db")
    else:
        return "gestion_stock.db"

DB_PATH = get_db_path()

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
CLR_BORDER  = "#334155"
CLR_PURPLE = "#8b5cf6"  

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
    style = ttk.Style()
    style.configure("Dark.Treeview",
                    background=CLR_CARD, foreground=CLR_TEXT,
                    fieldbackground=CLR_CARD, rowheight=26,
                    font=("Segoe UI", 9))
    style.configure("Dark.Treeview.Heading",
                    background=CLR_SIDEBAR, foreground=CLR_ACCENT,
                    font=("Segoe UI", 9, "bold"), relief="flat")
    style.map("Dark.Treeview", background=[("selected", CLR_ACCENT)])

    frame = tk.Frame(parent, bg=CLR_CARD)
    vsb = ttk.Scrollbar(frame, orient="vertical")
    hsb = ttk.Scrollbar(frame, orient="horizontal")

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        style="Dark.Treeview",
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
    config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
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
def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        c = conn.cursor()
        c.executescript("""
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS produits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            barcode     TEXT UNIQUE,
            designation TEXT NOT NULL,
            unite       TEXT DEFAULT 'Pcs',
            facteur_conversion REAL DEFAULT 1,
            prix_achat  REAL DEFAULT 0,
            prix_vente  REAL DEFAULT 0,
            stock_actuel REAL DEFAULT 0,
            stock_min   REAL DEFAULT 0,
            actif       INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS prix_speciaux_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            produit_id INTEGER NOT NULL,
            prix_special REAL NOT NULL,
            date_debut TEXT,
            date_fin TEXT,
            actif INTEGER DEFAULT 1,
            date_modification TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id),
            UNIQUE(client_id, produit_id)
        );
        CREATE TABLE IF NOT EXISTS clients (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            code    TEXT UNIQUE NOT NULL,
            nom     TEXT NOT NULL,
            adresse TEXT,
            tel     TEXT,
            email   TEXT,
            solde   REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fournisseurs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            code    TEXT UNIQUE NOT NULL,
            nom     TEXT NOT NULL,
            adresse TEXT,
            tel     TEXT,
            email   TEXT,
            solde   REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bons_achat (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT UNIQUE NOT NULL,
            date_bon        TEXT NOT NULL,
            fournisseur_id  INTEGER NOT NULL,
            total           REAL DEFAULT 0,
            statut          TEXT DEFAULT 'Validé',
            date_creation   TEXT,
            date_livraison  TEXT,
            num_facture_fournisseur TEXT,
            num_bl_fournisseur TEXT,
            ancien_solde    REAL DEFAULT 0,
            nouveau_solde   REAL DEFAULT 0,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        );

        CREATE TABLE IF NOT EXISTS lignes_achat (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bon_id      INTEGER NOT NULL,
            produit_id  INTEGER NOT NULL,
            quantite    REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            total       REAL NOT NULL,
            FOREIGN KEY(bon_id) REFERENCES bons_achat(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id)
        );

        CREATE TABLE IF NOT EXISTS bons_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            date_bon    TEXT NOT NULL,
            client_id   INTEGER NOT NULL,
            total       REAL DEFAULT 0,
            statut      TEXT DEFAULT 'Validé',
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS lignes_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bon_id      INTEGER NOT NULL,
            produit_id  INTEGER NOT NULL,
            quantite    REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            total       REAL NOT NULL,
            FOREIGN KEY(bon_id) REFERENCES bons_vente(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id)
        );

        CREATE TABLE IF NOT EXISTS factures (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT UNIQUE NOT NULL,
            date_facture    TEXT NOT NULL,
            bon_vente_id    INTEGER NOT NULL,
            client_id       INTEGER NOT NULL,
            total_ht        REAL DEFAULT 0,
            tva             REAL DEFAULT 19,
            total_ttc       REAL DEFAULT 0,
            statut          TEXT DEFAULT 'Émise',
            date_echeance   TEXT,
            observations    TEXT,
            FOREIGN KEY(bon_vente_id) REFERENCES bons_vente(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS versements_clients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            date_vers   TEXT NOT NULL,
            client_id   INTEGER NOT NULL,
            montant     REAL NOT NULL,
            mode        TEXT DEFAULT 'Espèces',
            reference   TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS versements_fournisseurs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT UNIQUE NOT NULL,
            date_vers       TEXT NOT NULL,
            fournisseur_id  INTEGER NOT NULL,
            montant         REAL NOT NULL,
            mode            TEXT DEFAULT 'Espèces',
            reference       TEXT,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        );

        CREATE TABLE IF NOT EXISTS retours_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            date_retour TEXT NOT NULL,
            bon_vente_id INTEGER,
            client_id   INTEGER NOT NULL,
            total       REAL DEFAULT 0,
            motif       TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS lignes_retour_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            retour_id   INTEGER NOT NULL,
            produit_id  INTEGER NOT NULL,
            quantite    REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            total       REAL NOT NULL,
            FOREIGN KEY(retour_id) REFERENCES retours_vente(id)
        );

        CREATE TABLE IF NOT EXISTS retours_achat (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT UNIQUE NOT NULL,
            date_retour     TEXT NOT NULL,
            bon_achat_id    INTEGER,
            fournisseur_id  INTEGER NOT NULL,
            total           REAL DEFAULT 0,
            motif           TEXT,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        );

        CREATE TABLE IF NOT EXISTS lignes_retour_achat (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            retour_id   INTEGER NOT NULL,
            produit_id  INTEGER NOT NULL,
            quantite    REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            total       REAL NOT NULL,
            FOREIGN KEY(retour_id) REFERENCES retours_achat(id)
        );
        
        CREATE TABLE IF NOT EXISTS remises (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id    INTEGER,
            type        TEXT,
            valeur      REAL,
            motif       TEXT,
            total_avant REAL,
            total_apres REAL,
            date_remise TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vente_id) REFERENCES bons_vente(id)
        );
        
        CREATE TABLE IF NOT EXISTS historique_prix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL,
            date_achat TEXT NOT NULL,
            quantite REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            prix_moyen_apres REAL,
            FOREIGN KEY(produit_id) REFERENCES produits(id)
        );
        
        CREATE TABLE IF NOT EXISTS profils_entreprise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            type_profil TEXT DEFAULT 'simple',
            adresse TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            site_web TEXT DEFAULT '',
            ville TEXT DEFAULT '',
            nif TEXT DEFAULT '',
            nis TEXT DEFAULT '',
            nrc TEXT DEFAULT '',
            art_imp TEXT DEFAULT '',
            registre_commerce TEXT DEFAULT '',
            capitale_social TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            actif INTEGER DEFAULT 1,
            est_defaut INTEGER DEFAULT 0,
            date_creation TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS facture_tva_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facture_id INTEGER NOT NULL,
            taux_tva REAL NOT NULL,
            total_ht REAL NOT NULL,
            total_tva REAL NOT NULL,
            FOREIGN KEY(facture_id) REFERENCES factures(id)
        );
        """)
        # Dans init_db(), après CREATE TABLE produits
        c.execute("PRAGMA table_info(produits)")
        cols = [row[1] for row in c.fetchall()]
        if "barcode" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN barcode TEXT")
            print("✅ Colonne 'barcode' ajoutée")
        # ✅ AJOUTER LA COLONNE produit_id À LA TABLE remises
        c.execute("PRAGMA table_info(remises)")
        remises_cols = [row[1] for row in c.fetchall()]
        if "produit_id" not in remises_cols:
            c.execute("ALTER TABLE remises ADD COLUMN produit_id INTEGER")
            c.execute("ALTER TABLE remises ADD COLUMN achat_id INTEGER")
            c.execute("ALTER TABLE remises ADD COLUMN reference TEXT")
            print("✅ Colonnes ajoutées à la table remises")
        # ✅ AJOUTER LES COLONNES POUR CLIENTS
        c.execute("PRAGMA table_info(clients)")
        clients_cols = [row[1] for row in c.fetchall()]
        
        if "nif" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN nif TEXT")
        if "nis" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN nis TEXT")
        if "nrc" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN nrc TEXT")
        if "art_imp" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN art_imp TEXT")
        if "registre_commerce" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN registre_commerce TEXT")
        if "capitale_social" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN capitale_social TEXT")
        if "ville" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN ville TEXT")
        
        # ✅ MIGRATION lignes_achat : colonnes TVA
        c.execute("PRAGMA table_info(lignes_achat)")
        la_cols = [row[1] for row in c.fetchall()]
        if "tva_taux" not in la_cols:
            c.execute("ALTER TABLE lignes_achat ADD COLUMN tva_taux REAL DEFAULT 0")
            c.execute("""UPDATE lignes_achat SET tva_taux = (
                SELECT COALESCE(p.tva, 19) FROM produits p WHERE p.id = lignes_achat.produit_id
            )""")
        if "total_ht" not in la_cols:
            c.execute("ALTER TABLE lignes_achat ADD COLUMN total_ht REAL DEFAULT 0")
            c.execute("UPDATE lignes_achat SET total_ht = total")
        if "total_ttc" not in la_cols:
            c.execute("ALTER TABLE lignes_achat ADD COLUMN total_ttc REAL DEFAULT 0")
            c.execute("UPDATE lignes_achat SET total_ttc = total_ht * (1 + tva_taux / 100.0)")
        # ✅ AJOUTER LES COLONNES POUR FOURNISSEURS
        c.execute("PRAGMA table_info(fournisseurs)")
        fourn_cols = [row[1] for row in c.fetchall()]
        
        if "code" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN code TEXT")
            # Mettre à jour les codes existants si besoin
            c.execute("UPDATE fournisseurs SET code = 'FRN-' || id WHERE code IS NULL OR code = ''")
            print("✅ Colonne 'code' ajoutée à la table fournisseurs")
        if "nis" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN nis TEXT")
        if "nrc" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN nrc TEXT")
        if "art_imp" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN art_imp TEXT")
        if "registre_commerce" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN registre_commerce TEXT")
        if "capitale_social" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN capitale_social TEXT")
        if "ville" not in fourn_cols:
            c.execute("ALTER TABLE fournisseurs ADD COLUMN ville TEXT")
        
        c.execute("PRAGMA table_info(prix_speciaux_clients)")
        psc_cols = [row[1] for row in c.fetchall()]
        if "date_modification" not in psc_cols:
            c.execute("ALTER TABLE prix_speciaux_clients ADD COLUMN date_modification TEXT")
        
        # Vérifier et ajouter la colonne niveau_prix à la table clients
        c.execute("PRAGMA table_info(clients)")
        clients_cols = [row[1] for row in c.fetchall()]
        
        if "niveau_prix" not in clients_cols:
            c.execute("ALTER TABLE clients ADD COLUMN niveau_prix TEXT DEFAULT 'detail'")
            print("✅ Colonne 'niveau_prix' ajoutée à la table clients")
        c.execute("""
            CREATE TABLE IF NOT EXISTS clients_niveau_prix (
                client_id   INTEGER PRIMARY KEY,
                niveau      TEXT DEFAULT 'detail',
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)
        # Vérifier et ajouter les colonnes pour le PMP
        c.execute("PRAGMA table_info(produits)")
        cols = [row[1] for row in c.fetchall()]
         # === AJOUTER LES COLONNES PRIX MULTI-NIVEAUX ICI ===
        if "prix_super_gros" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN prix_super_gros REAL DEFAULT 0")
            c.execute("UPDATE produits SET prix_super_gros = prix_vente")
        
        if "prix_gros" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN prix_gros REAL DEFAULT 0")
            c.execute("UPDATE produits SET prix_gros = prix_vente")
        
        if "prix_detail" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN prix_detail REAL DEFAULT 0")
            c.execute("UPDATE produits SET prix_detail = prix_vente")
        
        if "prix_special" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN prix_special REAL DEFAULT 0")
            c.execute("UPDATE produits SET prix_special = prix_vente")
        if "prix_moyen_pondere" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN prix_moyen_pondere REAL DEFAULT 0")
        
        if "cout_total_stock" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN cout_total_stock REAL DEFAULT 0")
        if "tva" not in cols:
            c.execute("ALTER TABLE produits ADD COLUMN tva REAL DEFAULT 19")
        # Ajouter le client COMPTOIR s'il n'existe pas
        c.execute("SELECT id FROM clients WHERE nom = 'COMPTOIR'")
        if not c.fetchone():
            c.execute("""INSERT INTO clients(code, nom, adresse, tel, email, solde) 
                        VALUES(?, ?, ?, ?, ?, ?)""", 
                        ("CLT-COMPTOIR", "COMPTOIR", "", "", "", 0))
        c.execute("PRAGMA table_info(bons_achat)")
        ba_cols = [row[1] for row in c.fetchall()]
        if "observations" not in ba_cols:
            c.execute("ALTER TABLE bons_achat ADD COLUMN observations TEXT")
            print("✅ Colonne 'observations' ajoutée à la table bons_achat")
        
        # ✅ AJOUTER AUSSI POUR bons_vente (optionnel)
        c.execute("PRAGMA table_info(bons_vente)")
        bv_cols = [row[1] for row in c.fetchall()]
        if "observations" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN observations TEXT")
            print("✅ Colonne 'observations' ajoutée à la table bons_vente")
        
                      
        
        conn.commit()
    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")
        conn.rollback()
    finally:
        conn.close()
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

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
    """✅ CORRECTION : Recalcule le coût du stock après une sortie"""
    produit = conn.execute(
        "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
        (produit_id,)
    ).fetchone()
    
    if not produit:
        return
    
    stock_actuel = produit["stock_actuel"] or 0
    cout_actuel = produit["cout_total_stock"] or 0
    pmp = produit["prix_moyen_pondere"] or 0
    
    # ✅ Si PMP = 0 mais stock > 0, recalculer
    if pmp <= 0 and stock_actuel > 0:
        pmp = cout_actuel / stock_actuel
    
    # ✅ Sortie au PMP
    reduction = quantite_sortie * pmp
    nouveau_cout = max(0.0, cout_actuel - reduction)
    nouveau_stock = max(0.0, stock_actuel - quantite_sortie)
    
    if nouveau_stock > 0:
        nouveau_pmp = nouveau_cout / nouveau_stock
    else:
        nouveau_pmp = 0
    
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
    """✅ CORRECTION : Annule l'effet stock/PMP d'un bon d'achat"""
    for l in lignes:
        # Récupérer l'état actuel du stock
        produit = conn.execute(
            "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
            (l["produit_id"],)
        ).fetchone()
        
        if not produit:
            continue
        
        stock_actuel = produit["stock_actuel"] or 0
        cout_actuel = produit["cout_total_stock"] or 0
        
        # ✅ Sortie du stock (annulation de l'entrée)
        nouvelle_quantite = max(0.0, stock_actuel - l["quantite"])
        
        # ✅ Recalcul du coût proportionnellement
        if stock_actuel > 0 and cout_actuel > 0:
            # Retirer la part proportionnelle du coût
            proportion = l["quantite"] / stock_actuel
            if proportion > 1:
                proportion = 1
            nouveau_cout = cout_actuel * (1 - proportion)
        else:
            nouveau_cout = 0
        
        # ✅ Mettre à jour le produit
        if nouvelle_quantite > 0 and nouveau_cout > 0:
            nouveau_pmp = nouveau_cout / nouvelle_quantite
        else:
            nouveau_pmp = 0
            nouveau_cout = 0
        
        conn.execute(
            "UPDATE produits SET stock_actuel = ?, prix_moyen_pondere = ?, cout_total_stock = ? WHERE id=?",
            (nouvelle_quantite, nouveau_pmp, nouveau_cout, l["produit_id"])
        )

class PrixSpeciauxClientDialog(tk.Toplevel):
    """Dialogue pour gérer les prix spéciaux d'un client spécifique"""
    
    def __init__(self, parent, client_id, client_nom):
        super().__init__(parent)
        self.client_id = client_id
        self.client_nom = client_nom
        self.title(f"Prix Spéciaux - {client_nom}")
        self.configure(bg=CLR_BG)
        self.geometry("900x600")
        self._build()
        self.refresh()
        center_window(self, 900, 600)
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"💰 PRIX SPÉCIAUX POUR {self.client_nom}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Sélection du produit
        select_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        select_frame.pack(fill="x", pady=10)
        
        lbl(select_frame, "Produit:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        produits = conn.execute("SELECT id, code, designation, prix_vente FROM produits WHERE actif = 1 ORDER BY designation").fetchall()
        conn.close()
        
        self.produits_map = {f"{p['code']} - {p['designation']}": dict(p) for p in produits}
        self.produit_var = tk.StringVar()
        produit_combo = combo(select_frame, list(self.produits_map.keys()), width=40, textvariable=self.produit_var)
        produit_combo.pack(side="left", padx=10)
        
        lbl(select_frame, "Prix spécial:", 9, True, CLR_MUTED).pack(side="left", padx=(20,5))
        self.prix_special_var = tk.StringVar()
        entry(select_frame, width=12, textvariable=self.prix_special_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        lbl(select_frame, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        tk.Button(select_frame, text="➕ AJOUTER/MODIFIER", command=self.ajouter_prix_special,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=20)
        
        # Tableau des prix spéciaux existants
        table_frame = tk.LabelFrame(main_frame, text="Prix spéciaux existants", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ["Code", "Produit", "Prix standard", "Prix spécial", "Remise", "Actions"]
        widths = [100, 250, 100, 100, 80, 100]
        tf, self.tree = make_tree(table_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="🗑 Supprimer", command=self.supprimer_prix_special,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                 bg=CLR_BORDER, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 9),
                 padx=12, pady=6, cursor="hand2").pack(side="right", padx=5)
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        prix_speciaux = conn.execute("""
            SELECT psc.*, pr.code, pr.designation,
                   COALESCE(NULLIF(pr.prix_vente, 0), pr.prix_detail, 0) as prix_standard
            FROM prix_speciaux_clients psc
            JOIN produits pr ON psc.produit_id = pr.id
            WHERE psc.client_id = ? AND psc.actif = 1""", (self.client_id,)).fetchall()
        conn.close()
        
        for ps in prix_speciaux:
            prix_std = ps["prix_standard"] or 0
            remise = ((prix_std - ps["prix_special"]) / prix_std * 100) if prix_std > 0 else 0
            self.tree.insert("", "end", iid=ps["id"], values=(
                ps["code"], ps["designation"],
                f"{prix_std:.2f} DA",
                f"{ps['prix_special']:.2f} DA",
                f"{remise:.1f}%",
                "✏ Modifier"
            ))
    
    def ajouter_prix_special(self):
        produit_key = self.produit_var.get()
        if not produit_key or produit_key not in self.produits_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit")
            return
        
        try:
            prix_special = parse_decimal(self.prix_special_var.get())
            if prix_special <= 0:
                messagebox.showerror("Erreur", "Prix spécial invalide")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Prix spécial invalide")
            return
        
        produit = self.produits_map[produit_key]
        
        conn = get_conn()
        try:
            # Vérifier si un prix spécial existe déjà
            existing = conn.execute("""
                SELECT id FROM prix_speciaux_clients 
                WHERE client_id = ? AND produit_id = ?
            """, (self.client_id, produit["id"])).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE prix_speciaux_clients 
                    SET prix_special = ?,
                        date_modification = datetime('now')
                    WHERE id = ?
                """, (prix_special, existing["id"]))
                messagebox.showinfo("Succès", "Prix spécial mis à jour")
            else:
                conn.execute("""
                    INSERT INTO prix_speciaux_clients(client_id, produit_id, prix_special)
                    VALUES(?, ?, ?)
                """, (self.client_id, produit["id"], prix_special))
                messagebox.showinfo("Succès", "Prix spécial ajouté")
            
            conn.commit()
            self.refresh()
            self.prix_special_var.set("")
            self.produit_var.set("")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def supprimer_prix_special(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un prix spécial à supprimer")
            return
        
        if messagebox.askyesno("Confirmation", "Supprimer ce prix spécial ?"):
            conn = get_conn()
            try:
                conn.execute("UPDATE prix_speciaux_clients SET actif = 0 WHERE id = ?", (sel[0],))
                conn.commit()
                messagebox.showinfo("Succès", "Prix spécial supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                conn.rollback()
            finally:
                conn.close()


class DatePicker(tk.Toplevel):
    """Fenêtre de sélection de date avec calendrier"""
    
    def __init__(self, parent, date_var, title="Sélectionner une date"):
        super().__init__(parent)
        self.parent = parent
        self.date_var = date_var
        self.title(title)
        self.configure(bg=CLR_BG)
        self.geometry("320x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Date actuelle
        current_date = self.date_var.get()
        if current_date and self._validate_date(current_date):
            self.selected_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        else:
            self.selected_date = date.today()
        
        self.year = self.selected_date.year
        self.month = self.selected_date.month
        
        self._build()
        self._draw_calendar()
        center_window(self, 320, 350)
    
    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def _build(self):
        # Frame principal
        main_frame = tk.Frame(self, bg=CLR_BG, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # Navigation
        nav_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=5, pady=5)
        nav_frame.pack(fill="x", pady=(0, 10))
        
        # Bouton Mois précédent
        btn_prev = tk.Button(nav_frame, text="◄", command=self.prev_month,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=8, pady=4,
                            cursor="hand2")
        btn_prev.pack(side="left")
        
        # Affichage mois/année
        self.month_year_label = tk.Label(nav_frame, text="", 
                                         bg=CLR_CARD, fg=CLR_TEXT,
                                         font=("Segoe UI", 12, "bold"))
        self.month_year_label.pack(side="left", expand=True)
        
        # Bouton Mois suivant
        btn_next = tk.Button(nav_frame, text="►", command=self.next_month,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=8, pady=4,
                            cursor="hand2")
        btn_next.pack(side="right")
        
        # Cadre du calendrier
        self.calendar_frame = tk.Frame(main_frame, bg=CLR_CARD)
        self.calendar_frame.pack(fill="both", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="Aujourd'hui", command=self.select_today,
                 bg=CLR_GREEN, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Effacer", command=self.clear_date,
                 bg=CLR_ORANGE, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Valider", command=self.select_date,
                 bg=CLR_ACCENT, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="right", padx=5)
        
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="right", padx=5)
    
    def _draw_calendar(self):
        # Nettoyer le cadre
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        # Mettre à jour le label mois/année
        month_name = calendar.month_name[self.month]
        self.month_year_label.config(text=f"{month_name} {self.year}")
        
        # Jours de la semaine
        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        for i, day in enumerate(days):
            lbl = tk.Label(self.calendar_frame, text=day, 
                          bg=CLR_CARD, fg=CLR_ACCENT,
                          font=("Segoe UI", 8, "bold"), width=4)
            lbl.grid(row=0, column=i, padx=2, pady=2)
        
        # Calendrier
        cal = calendar.monthcalendar(self.year, self.month)
        
        # Couleur pour les dates sélectionnées
        today = date.today()
        
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(self.calendar_frame, text="", 
                                  bg=CLR_CARD, width=4)
                else:
                    current_date = date(self.year, self.month, day)
                    
                    # Déterminer la couleur
                    bg_color = CLR_INPUT
                    fg_color = CLR_TEXT
                    
                    if current_date == self.selected_date:
                        bg_color = CLR_ACCENT
                        fg_color = "white"
                    elif current_date == today:
                        bg_color = CLR_ORANGE
                        fg_color = "white"
                    
                    lbl = tk.Label(self.calendar_frame, text=str(day),
                                  bg=bg_color, fg=fg_color,
                                  font=("Segoe UI", 10), width=4,
                                  relief="flat", cursor="hand2")
                    lbl.bind("<Button-1>", lambda e, d=current_date: self.on_day_click(d))
                
                lbl.grid(row=row_idx+1, column=col_idx, padx=2, pady=2)
    
    def on_day_click(self, date_obj):
        self.selected_date = date_obj
        self._draw_calendar()
    
    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._draw_calendar()
    
    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._draw_calendar()
    
    def select_today(self):
        self.selected_date = date.today()
        self.year = self.selected_date.year
        self.month = self.selected_date.month
        self._draw_calendar()
    
    def clear_date(self):
        self.date_var.set("")
        self.destroy()
    
    def select_date(self):
        self.date_var.set(self.selected_date.strftime("%Y-%m-%d"))
        self.destroy()


class DateEntry(tk.Frame):
    """Widget combiné : champ de texte + bouton calendrier"""
    
    def __init__(self, parent, date_var, width=12, label_text="", **kw):
        super().__init__(parent, bg=parent["bg"] if hasattr(parent, "bg") else CLR_BG)
        
        self.date_var = date_var
        
        # Label si spécifié
        if label_text:
            lbl(self, label_text, 9, False, CLR_MUTED).pack(side="left", padx=(0,5))
        
        # Champ de texte
        self.entry = tk.Entry(self, bg=CLR_INPUT, fg=CLR_TEXT, 
                              insertbackground=CLR_TEXT,
                              relief="flat", width=width,
                              highlightthickness=1, 
                              highlightbackground=CLR_BORDER,
                              highlightcolor=CLR_ACCENT,
                              textvariable=date_var,
                              readonlybackground=CLR_INPUT,
                              state="readonly", **kw)
        self.entry.pack(side="left", padx=(0,5))
        self.entry.bind("<FocusOut>", self.on_focus_out)
        
        # Bouton calendrier
        btn_cal = tk.Button(self, text="📅", command=self.show_calendar,
                           bg=CLR_ACCENT, fg="white", relief="flat",
                           font=("Segoe UI", 9), padx=4, pady=2,
                           cursor="hand2")
        btn_cal.pack(side="left")
        
        # Bouton Effacer
        btn_clear = tk.Button(self, text="✕", command=self.clear_date,
                             bg=CLR_RED, fg="white", relief="flat",
                             font=("Segoe UI", 9), padx=4, pady=2,
                             cursor="hand2")
        btn_clear.pack(side="left", padx=(2,0))
    
    def show_calendar(self):
        DatePicker(self, self.date_var)
    
    def clear_date(self):
        self.date_var.set("")
    
    def on_focus_out(self, event):
        """Valider la date saisie manuellement"""
        date_str = self.date_var.get().strip()
        if date_str:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # Si la date est invalide, effacer
                self.date_var.set("")     
class StatistiquesAchatsPage(tk.Frame):
    """Page de statistiques des achats avec filtres par fournisseur, produit et période"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "📊 Statistiques des Achats par Fournisseur & Produit", 16, True).pack(side="left")
        
        # ========== FILTRES ==========
        filter_frame = tk.LabelFrame(self, text="🔍 Filtres", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, 
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        filter_frame.pack(fill="x", padx=20, pady=10)
        
        # Ligne 1: Fournisseur
        row1 = tk.Frame(filter_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        
        lbl(row1, "🏭 Fournisseur:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        fournisseurs = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
        conn.close()
        
        self.fournisseurs_map = {f["nom"]: f["id"] for f in fournisseurs}
        fournisseur_liste = ["Tous"] + list(self.fournisseurs_map.keys())
        
        self.fournisseur_var = tk.StringVar(value="Tous")
        fournisseur_combo = combo(row1, fournisseur_liste, width=25, textvariable=self.fournisseur_var)
        fournisseur_combo.pack(side="left", padx=10)
        fournisseur_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Ligne 2: Produit
        row2 = tk.Frame(filter_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        
        lbl(row2, "📦 Produit:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        produits = conn.execute("""
            SELECT id, code, designation, unite, facteur_conversion, tva
            FROM produits WHERE actif = 1 ORDER BY designation
        """).fetchall()
        conn.close()
        
        self.produits_map = {f"{p['code']} - {p['designation']}": dict(p) for p in produits}
        produit_liste = ["Tous"] + list(self.produits_map.keys())
        
        self.produit_var = tk.StringVar(value="Tous")
        produit_combo = combo(row2, produit_liste, width=35, textvariable=self.produit_var)
        produit_combo.pack(side="left", padx=10)
        produit_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Ligne 3: Période
        row3 = tk.Frame(filter_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        
        lbl(row3, "📅 Du:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.date_debut_var = tk.StringVar(value=date.today().replace(day=1).strftime("%Y-%m-%d"))
        entry(row3, width=12, textvariable=self.date_debut_var).pack(side="left", padx=5)
        
        lbl(row3, "Au:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        entry(row3, width=12, textvariable=self.date_fin_var).pack(side="left", padx=5)
        
        tk.Button(row3, text="📊 Appliquer", command=self.refresh,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=20)
        
        # Ligne 4: Options d'affichage
        row4 = tk.Frame(filter_frame, bg=CLR_CARD)
        row4.pack(fill="x", pady=5)
        
        lbl(row4, "📊 Affichage:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.affichage_var = tk.StringVar(value="Par Fournisseur")
        affichage_combo = combo(row4, ["Par Fournisseur", "Par Produit", "Détail Fournisseur-Produit"], 
                               width=20, textvariable=self.affichage_var)
        affichage_combo.pack(side="left", padx=10)
        affichage_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        lbl(row4, "📦 Unités:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
        self.unite_var = tk.StringVar(value="cartons")
        unite_combo = combo(row4, ["cartons", "unités", "les deux"], width=10, 
                           textvariable=self.unite_var)
        unite_combo.pack(side="left", padx=10)
        unite_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Boutons d'action
        btn_frame = tk.Frame(filter_frame, bg=CLR_CARD)
        btn_frame.pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_stats,
                 bg=CLR_ACCENT, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="📥 Exporter CSV", command=self.export_stats_csv,
                 bg=CLR_ORANGE, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="📄 Exporter HTML", command=self.export_stats_html,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        # ========== TABLEAU DES RÉSULTATS ==========
        cols = ["Fournisseur", "Produit", "TVA", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        widths = [180, 180, 50, 100, 100, 120, 120, 80]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ========== RÉCAPITULATIF ==========
        recap_frame = tk.Frame(self, bg=CLR_CARD, padx=15, pady=10)
        recap_frame.pack(fill="x", padx=20, pady=10)
        
        lbl(recap_frame, "📊 RÉCAPITULATIF DES ACHATS", 11, True, CLR_ACCENT).pack(anchor="w", pady=(0,5))
        tk.Frame(recap_frame, bg=CLR_BORDER, height=1).pack(fill="x", pady=5)
        
        totals_frame = tk.Frame(recap_frame, bg=CLR_CARD)
        totals_frame.pack(fill="x", pady=5)
        
        lbl(totals_frame, "Total Cartons:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_cartons_var = tk.StringVar(value="0.00")
        tk.Label(totals_frame, textvariable=self.total_cartons_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0,20))
        
        lbl(totals_frame, "Total Unités:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_unites_var = tk.StringVar(value="0.00")
        tk.Label(totals_frame, textvariable=self.total_unites_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0,20))
        
        lbl(totals_frame, "Total Achats HT:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_ca_var = tk.StringVar(value="0.00 DA")
        tk.Label(totals_frame, textvariable=self.total_ca_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(totals_frame, "Lignes:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.nb_lignes_var = tk.StringVar(value="0")
        tk.Label(totals_frame, textvariable=self.nb_lignes_var, bg=CLR_CARD, 
                fg=CLR_TEXT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0,20))
    
    def get_stats(self):
        """Récupère les statistiques des achats selon les filtres"""
        conn = get_conn()
        
        fournisseur_filter = self.fournisseur_var.get()
        produit_filter = self.produit_var.get()
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        query = """
            SELECT 
                f.id as fournisseur_id,
                f.nom as fournisseur_nom,
                p.id as produit_id,
                p.code as produit_code,
                p.designation as produit_designation,
                p.unite as produit_unite,
                p.facteur_conversion,
                p.tva as produit_tva,
                COUNT(DISTINCT ba.id) as nb_bons,
                COALESCE(SUM(la.quantite), 0) as total_unites,
                COALESCE(SUM(la.quantite / NULLIF(p.facteur_conversion, 0)), 0) as total_cartons,
                COALESCE(SUM(la.total), 0) as total_ht
            FROM bons_achat ba
            JOIN fournisseurs f ON ba.fournisseur_id = f.id
            JOIN lignes_achat la ON ba.id = la.bon_id
            JOIN produits p ON la.produit_id = p.id
            WHERE ba.statut = 'Validé'
        """
        
        params = []
        
        if fournisseur_filter != "Tous" and fournisseur_filter in self.fournisseurs_map:
            query += " AND f.id = ?"
            params.append(self.fournisseurs_map[fournisseur_filter])
        
        if produit_filter != "Tous" and produit_filter in self.produits_map:
            query += " AND p.id = ?"
            params.append(self.produits_map[produit_filter]["id"])
        
        if date_debut and date_fin:
            query += " AND ba.date_bon BETWEEN ? AND ?"
            params.extend([date_debut, date_fin])
        
        query += """ GROUP BY f.id, f.nom, p.id, p.code, p.designation, p.unite, p.facteur_conversion, p.tva
                    ORDER BY f.nom, total_cartons DESC"""
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        return rows
    
    def refresh(self):
        """Rafraîchit l'affichage selon le mode sélectionné"""
        self.tree.delete(*self.tree.get_children())
        
        rows = self.get_stats()
        
        if not rows:
            self.total_cartons_var.set("0.00")
            self.total_unites_var.set("0.00")
            self.total_ca_var.set("0.00 DA")
            self.nb_lignes_var.set("0")
            return
        
        # ✅ Convertir les rows en dictionnaires modifiables
        rows = [dict(row) for row in rows]
        
        mode = self.affichage_var.get()
        unite_mode = self.unite_var.get()
        
        total_cartons = 0
        total_unites = 0
        total_ca = 0
        
        if mode == "Par Fournisseur":
            fournisseurs_data = {}
            for r in rows:
                fournisseur_id = r["fournisseur_id"]
                if fournisseur_id not in fournisseurs_data:
                    fournisseurs_data[fournisseur_id] = {
                        "fournisseur_nom": r["fournisseur_nom"],
                        "total_cartons": 0,
                        "total_unites": 0,
                        "total_ht": 0,
                        "total_ttc": 0,
                        "nb_bons": 0,
                        "produits": []
                    }
                
                tva_taux = r.get("produit_tva") or 0
                ttc_produit = r["total_ht"] * (1 + tva_taux / 100)
                
                fournisseurs_data[fournisseur_id]["total_cartons"] += r["total_cartons"]
                fournisseurs_data[fournisseur_id]["total_unites"] += r["total_unites"]
                fournisseurs_data[fournisseur_id]["total_ht"] += r["total_ht"]
                fournisseurs_data[fournisseur_id]["total_ttc"] += ttc_produit
                fournisseurs_data[fournisseur_id]["nb_bons"] += r["nb_bons"]
                
                r_dict = {
                    "produit_id": r["produit_id"],
                    "produit_designation": r["produit_designation"],
                    "total_cartons": r["total_cartons"],
                    "total_unites": r["total_unites"],
                    "total_ht": r["total_ht"],
                    "ttc": ttc_produit,
                    "tva_taux": tva_taux,
                    "nb_bons": r["nb_bons"]
                }
                fournisseurs_data[fournisseur_id]["produits"].append(r_dict)
            
            for fournisseur_id, data in fournisseurs_data.items():
                total_cartons += data["total_cartons"]
                total_unites += data["total_unites"]
                total_ca += data["total_ht"]
                
                qte_cartons = f"{data['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{data['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                
                self.tree.insert("", "end", iid=f"fournisseur_{fournisseur_id}", values=(
                    data["fournisseur_nom"],
                    f"{len(data['produits'])} produits",
                    "",
                    qte_cartons,
                    qte_unites,
                    f"{data['total_ht']:,.2f} DA",
                    f"{data['total_ttc']:,.2f} DA",
                    ""
                ), tags=("fournisseur_row",))
                
                for r_dict in data["produits"]:
                    qte_cartons_prod = f"{r_dict['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                    qte_unites_prod = f"{r_dict['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                    
                    pct = (r_dict['total_ht'] / data['total_ht'] * 100) if data['total_ht'] > 0 else 0
                    tva_affichage = f"{r_dict['tva_taux']:.0f}%"
                    
                    self.tree.insert("", "end", iid=f"fournisseur_{fournisseur_id}_prod_{r_dict['produit_id']}", values=(
                        "  └ " + r_dict["produit_designation"],
                        f"{r_dict['nb_bons']} bons",
                        tva_affichage,
                        qte_cartons_prod,
                        qte_unites_prod,
                        f"{r_dict['total_ht']:,.2f} DA",
                        f"{r_dict['ttc']:,.2f} DA",
                        f"{pct:.1f}%"
                    ), tags=("detail_row",))
            
            self.tree.tag_configure("fournisseur_row", foreground=CLR_ACCENT, font=("Segoe UI", 9, "bold"))
            self.tree.tag_configure("detail_row", foreground=CLR_TEXT)
            
        elif mode == "Par Produit":
            produits_data = {}
            for r in rows:
                produit_id = r["produit_id"]
                if produit_id not in produits_data:
                    tva_taux = r.get("produit_tva") or 0
                    produits_data[produit_id] = {
                        "produit_designation": r["produit_designation"],
                        "produit_code": r["produit_code"],
                        "total_cartons": 0,
                        "total_unites": 0,
                        "total_ht": 0,
                        "total_ttc": 0,
                        "nb_bons": 0,
                        "tva_taux": tva_taux,
                        "fournisseurs": []
                    }
                
                ttc_produit = r["total_ht"] * (1 + produits_data[produit_id]["tva_taux"] / 100)
                produits_data[produit_id]["total_cartons"] += r["total_cartons"]
                produits_data[produit_id]["total_unites"] += r["total_unites"]
                produits_data[produit_id]["total_ht"] += r["total_ht"]
                produits_data[produit_id]["total_ttc"] += ttc_produit
                produits_data[produit_id]["nb_bons"] += r["nb_bons"]
                
                r_dict = {
                    "fournisseur_id": r["fournisseur_id"],
                    "fournisseur_nom": r["fournisseur_nom"],
                    "total_cartons": r["total_cartons"],
                    "total_unites": r["total_unites"],
                    "total_ht": r["total_ht"],
                    "ttc": ttc_produit,
                    "nb_bons": r["nb_bons"]
                }
                produits_data[produit_id]["fournisseurs"].append(r_dict)
            
            for produit_id, data in produits_data.items():
                total_cartons += data["total_cartons"]
                total_unites += data["total_unites"]
                total_ca += data["total_ht"]
                
                qte_cartons = f"{data['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{data['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                tva_affichage = f"{data['tva_taux']:.0f}%"
                
                self.tree.insert("", "end", iid=f"produit_{produit_id}", values=(
                    data["produit_designation"],
                    f"{len(data['fournisseurs'])} fournisseurs",
                    tva_affichage,
                    qte_cartons,
                    qte_unites,
                    f"{data['total_ht']:,.2f} DA",
                    f"{data['total_ttc']:,.2f} DA",
                    ""
                ), tags=("produit_row",))
                
                for r_dict in data["fournisseurs"]:
                    qte_cartons_fourn = f"{r_dict['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                    qte_unites_fourn = f"{r_dict['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                    
                    pct = (r_dict['total_ht'] / data['total_ht'] * 100) if data['total_ht'] > 0 else 0
                    
                    self.tree.insert("", "end", iid=f"produit_{produit_id}_fourn_{r_dict['fournisseur_id']}", values=(
                        "  └ " + r_dict["fournisseur_nom"],
                        f"{r_dict['nb_bons']} bons",
                        "",
                        qte_cartons_fourn,
                        qte_unites_fourn,
                        f"{r_dict['total_ht']:,.2f} DA",
                        f"{r_dict['ttc']:,.2f} DA",
                        f"{pct:.1f}%"
                    ), tags=("detail_row",))
            
            self.tree.tag_configure("produit_row", foreground=CLR_GREEN, font=("Segoe UI", 9, "bold"))
            self.tree.tag_configure("detail_row", foreground=CLR_TEXT)
            
        else:  # Détail Fournisseur-Produit
            for r in rows:
                total_cartons += r["total_cartons"]
                total_unites += r["total_unites"]
                total_ca += r["total_ht"]
                
                tva_taux = r.get("produit_tva") or 0
                ttc = r["total_ht"] * (1 + tva_taux / 100)
                
                qte_cartons = f"{r['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{r['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                tva_affichage = f"{tva_taux:.0f}%"
                
                self.tree.insert("", "end", iid=f"detail_{r['fournisseur_id']}_{r['produit_id']}", values=(
                    r["fournisseur_nom"],
                    r["produit_designation"],
                    tva_affichage,
                    qte_cartons,
                    qte_unites,
                    f"{r['total_ht']:,.2f} DA",
                    f"{ttc:,.2f} DA",
                    ""
                ))
        
        self.total_cartons_var.set(f"{total_cartons:.2f}")
        self.total_unites_var.set(f"{total_unites:.2f}")
        self.total_ca_var.set(f"{total_ca:,.2f} DA")
        self.nb_lignes_var.set(str(len(self.tree.get_children())))
    
    def print_stats(self):
        """Imprime les statistiques"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        headers = ["Fournisseur", "Produit", "TVA", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        fournisseur_filter = self.fournisseur_var.get()
        produit_filter = self.produit_var.get()
        mode = self.affichage_var.get()
        
        title = f"STATISTIQUES DES ACHATS - {mode}"
        if fournisseur_filter != "Tous":
            title += f" - Fournisseur: {fournisseur_filter}"
        if produit_filter != "Tous":
            title += f" - Produit: {produit_filter}"
        
        data.append(["", "", "", "", "", "", "", ""])
        data.append(["TOTAL", "", "", 
                    self.total_cartons_var.get(), 
                    self.total_unites_var.get(),
                    "", self.total_ca_var.get(), ""])
        
        print_preview(data, title, headers)
    
    def export_stats_csv(self):
        """Exporte les statistiques en CSV"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        headers = ["Fournisseur", "Produit", "TVA", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="statistiques_achats.csv"
        )
        
        if filename:
            data.append(["", "", "", "", "", "", "", ""])
            data.append(["TOTAL", "", "", 
                        self.total_cartons_var.get(), 
                        self.total_unites_var.get(),
                        "", self.total_ca_var.get(), ""])
            
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    def export_stats_html(self):
        """Exporte les statistiques en HTML"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        headers = ["Fournisseur", "Produit", "TVA", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        fournisseur_filter = self.fournisseur_var.get()
        produit_filter = self.produit_var.get()
        mode = self.affichage_var.get()
        
        title = f"STATISTIQUES DES ACHATS - {mode}"
        if fournisseur_filter != "Tous":
            title += f" - Fournisseur: {fournisseur_filter}"
        if produit_filter != "Tous":
            title += f" - Produit: {produit_filter}"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="statistiques_achats.html"
        )
        
        if filename:
            data.append(["", "", "", "", "", "", "", ""])
            data.append(["TOTAL", "", "", 
                        self.total_cartons_var.get(), 
                        self.total_unites_var.get(),
                        "", self.total_ca_var.get(), ""])
            
            if export_to_html(data, filename, title, headers):
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)                   
# ========== PAGE STATISTIQUES VENTES - VERSION AMÉLIORÉE ==========

class StatistiquesVentesPage(tk.Frame):
    """Page de statistiques des ventes avec filtres par client, produit et période"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # ✅ CONTENEUR PRINCIPAL AVEC SCROLL
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True)
        
        # ✅ CANVAS + SCROLLBAR
        canvas = tk.Canvas(main_container, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        
        # ✅ Redimensionner le canvas quand la fenêtre change
        def _configure_canvas(event):
            canvas.itemconfig(1, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ✅ Raccourci clavier pour la molette
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # ============================================================
        # ✅ TOUT LE CONTENU DANS scrollable_frame
        # ============================================================
        content = scrollable_frame
        
        # En-tête
        hdr = tk.Frame(content, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "📊 Statistiques des Ventes par Client & Produit", 16, True).pack(side="left")
        
        # ========== FILTRES ==========
        filter_frame = tk.LabelFrame(content, text="🔍 Filtres", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, 
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        filter_frame.pack(fill="x", padx=20, pady=10)
        
        # Ligne 1: Client
        row1 = tk.Frame(filter_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        
        lbl(row1, "👤 Client:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        clients = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
        conn.close()
        
        self.clients_map = {c["nom"]: c["id"] for c in clients}
        client_liste = ["Tous"] + list(self.clients_map.keys())
        
        self.client_var = tk.StringVar(value="Tous")
        client_combo = combo(row1, client_liste, width=25, textvariable=self.client_var)
        client_combo.pack(side="left", padx=10)
        client_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Ligne 2: Produit
        row2 = tk.Frame(filter_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        
        lbl(row2, "📦 Produit:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        produits = conn.execute("""
            SELECT id, code, designation, unite, facteur_conversion 
            FROM produits WHERE actif = 1 ORDER BY designation
        """).fetchall()
        conn.close()
        
        self.produits_map = {f"{p['code']} - {p['designation']}": dict(p) for p in produits}
        produit_liste = ["Tous"] + list(self.produits_map.keys())
        
        self.produit_var = tk.StringVar(value="Tous")
        produit_combo = combo(row2, produit_liste, width=35, textvariable=self.produit_var)
        produit_combo.pack(side="left", padx=10)
        produit_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Ligne 3: Période
        row3 = tk.Frame(filter_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        
        lbl(row3, "📅 Du:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.date_debut_var = tk.StringVar(value=date.today().replace(day=1).strftime("%Y-%m-%d"))
        entry(row3, width=12, textvariable=self.date_debut_var).pack(side="left", padx=5)
        
        lbl(row3, "Au:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        entry(row3, width=12, textvariable=self.date_fin_var).pack(side="left", padx=5)
        
        tk.Button(row3, text="📊 Appliquer", command=self.refresh,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=20)
        
        # Ligne 4: Options d'affichage
        row4 = tk.Frame(filter_frame, bg=CLR_CARD)
        row4.pack(fill="x", pady=5)
        
        lbl(row4, "📊 Affichage:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.affichage_var = tk.StringVar(value="Par Client")
        affichage_combo = combo(row4, ["Par Client", "Par Produit", "Détail Client-Produit"], 
                               width=20, textvariable=self.affichage_var)
        affichage_combo.pack(side="left", padx=10)
        affichage_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        lbl(row4, "📦 Unités:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
        self.unite_var = tk.StringVar(value="cartons")
        unite_combo = combo(row4, ["cartons", "unités", "les deux"], width=10, 
                           textvariable=self.unite_var)
        unite_combo.pack(side="left", padx=10)
        unite_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Boutons d'action
        btn_frame = tk.Frame(filter_frame, bg=CLR_CARD)
        btn_frame.pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_stats,
                 bg=CLR_ACCENT, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="📥 Exporter CSV", command=self.export_stats_csv,
                 bg=CLR_ORANGE, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="📄 Exporter HTML", command=self.export_stats_html,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                 cursor="hand2").pack(side="left", padx=5)
        
        # ========== TABLEAU DES RÉSULTATS ==========
        # Colonnes variables selon le mode d'affichage
        cols = ["Client", "Produit", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA", "Actions"]
        widths = [150, 180, 100, 100, 120, 120, 80, 100]
        tf, self.tree = make_tree(content, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ========== RÉCAPITULATIF ==========
        recap_frame = tk.Frame(content, bg=CLR_CARD, padx=15, pady=10)
        recap_frame.pack(fill="x", padx=20, pady=10)
        
        lbl(recap_frame, "📊 RÉCAPITULATIF", 11, True, CLR_ACCENT).pack(anchor="w", pady=(0,5))
        tk.Frame(recap_frame, bg=CLR_BORDER, height=1).pack(fill="x", pady=5)
        
        # ✅ Utiliser un tableau avec 2 lignes pour un meilleur affichage
        totals_grid = tk.Frame(recap_frame, bg=CLR_CARD)
        totals_grid.pack(fill="x", pady=5)
        
        totals_grid.grid_columnconfigure(0, weight=1)
        totals_grid.grid_columnconfigure(1, weight=1)
        
        # LIGNE 1: Cartons et Unités
        frame_ligne1 = tk.Frame(totals_grid, bg=CLR_CARD)
        frame_ligne1.grid(row=0, column=0, columnspan=2, sticky="ew", pady=3)
        
        lbl(frame_ligne1, "📦 Total Cartons:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_cartons_var = tk.StringVar(value="0.00")
        tk.Label(frame_ligne1, textvariable=self.total_cartons_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0,40))
        
        lbl(frame_ligne1, "📦 Total Unités:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_unites_var = tk.StringVar(value="0.00")
        tk.Label(frame_ligne1, textvariable=self.total_unites_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0,10))
        
        # LIGNE 2: CA et Lignes
        frame_ligne2 = tk.Frame(totals_grid, bg=CLR_CARD)
        frame_ligne2.grid(row=1, column=0, columnspan=2, sticky="ew", pady=3)
        
        lbl(frame_ligne2, "💰 CA Total:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_ca_var = tk.StringVar(value="0.00 DA")
        tk.Label(frame_ligne2, textvariable=self.total_ca_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0,40))
        
        lbl(frame_ligne2, "📋 Lignes:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.nb_lignes_var = tk.StringVar(value="0")
        tk.Label(frame_ligne2, textvariable=self.nb_lignes_var, bg=CLR_CARD, 
                fg=CLR_TEXT, font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0,10))
        
        # ✅ Ajouter un espace en bas pour le scroll
        tk.Frame(content, bg=CLR_BG, height=20).pack()
    
    def get_stats(self):
        """Récupère les statistiques des ventes selon les filtres"""
        conn = get_conn()
        
        client_filter = self.client_var.get()
        produit_filter = self.produit_var.get()
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        # Construction de la requête
        query = """
            SELECT 
                c.id as client_id,
                c.nom as client_nom,
                p.id as produit_id,
                p.code as produit_code,
                p.designation as produit_designation,
                p.unite as produit_unite,
                p.facteur_conversion,
                p.prix_vente,
                p.prix_detail,
                p.prix_gros,
                p.prix_super_gros,
                COUNT(DISTINCT bv.id) as nb_bons,
                COALESCE(SUM(lv.quantite), 0) as total_unites,
                COALESCE(SUM(lv.quantite / NULLIF(p.facteur_conversion, 0)), 0) as total_cartons,
                COALESCE(SUM(lv.total), 0) as total_ht
            FROM bons_vente bv
            JOIN clients c ON bv.client_id = c.id
            JOIN lignes_vente lv ON bv.id = lv.bon_id
            JOIN produits p ON lv.produit_id = p.id
            WHERE bv.statut = 'Validé'
        """
        
        params = []
        
        # Filtre client
        if client_filter != "Tous" and client_filter in self.clients_map:
            query += " AND c.id = ?"
            params.append(self.clients_map[client_filter])
        
        # Filtre produit
        if produit_filter != "Tous" and produit_filter in self.produits_map:
            query += " AND p.id = ?"
            params.append(self.produits_map[produit_filter]["id"])
        
        # Filtre dates
        if date_debut and date_fin:
            query += " AND bv.date_bon BETWEEN ? AND ?"
            params.extend([date_debut, date_fin])
        
        query += " GROUP BY c.id, c.nom, p.id, p.code, p.designation, p.unite, p.facteur_conversion, p.prix_vente, p.prix_detail, p.prix_gros, p.prix_super_gros"
        query += " ORDER BY c.nom, total_cartons DESC"
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        return rows
    
    def refresh(self):
        """Rafraîchit l'affichage selon le mode sélectionné"""
        self.tree.delete(*self.tree.get_children())
        
        rows = self.get_stats()
        
        if not rows:
            self.total_cartons_var.set("0.00")
            self.total_unites_var.set("0.00")
            self.total_ca_var.set("0.00 DA")
            self.nb_lignes_var.set("0")
            return
        
        # ✅ Convertir les rows en dictionnaires modifiables
        rows = [dict(row) for row in rows]
        
        mode = self.affichage_var.get()
        unite_mode = self.unite_var.get()
        
        total_cartons = 0
        total_unites = 0
        total_ca = 0
        
        # ✅ Récupérer les taux de TVA réels par produit
        conn = get_conn()
        tva_produits = {}
        for r in rows:
            if r["produit_id"] not in tva_produits:
                p = conn.execute("SELECT tva FROM produits WHERE id=?", (r["produit_id"],)).fetchone()
                tva_produits[r["produit_id"]] = p["tva"] if p and p["tva"] else 0
        conn.close()
        
        if mode == "Par Client":
            clients_data = {}
            for r in rows:
                client_id = r["client_id"]
                if client_id not in clients_data:
                    clients_data[client_id] = {
                        "client_nom": r["client_nom"],
                        "client_id": client_id,
                        "total_cartons": 0,
                        "total_unites": 0,
                        "total_ht": 0,
                        "total_ttc": 0,
                        "nb_bons": 0,
                        "produits": []
                    }
                # ✅ Calculer le TTC réel avec le taux de TVA du produit
                tva_taux = tva_produits.get(r["produit_id"], 0)
                ttc_produit = r["total_ht"] * (1 + tva_taux / 100)
                
                clients_data[client_id]["total_cartons"] += r["total_cartons"]
                clients_data[client_id]["total_unites"] += r["total_unites"]
                clients_data[client_id]["total_ht"] += r["total_ht"]
                clients_data[client_id]["total_ttc"] += ttc_produit
                clients_data[client_id]["nb_bons"] += r["nb_bons"]
                
                # ✅ Stocker les données dans un dictionnaire pour les sous-lignes
                r_dict = {
                    "produit_id": r["produit_id"],
                    "produit_designation": r["produit_designation"],
                    "total_cartons": r["total_cartons"],
                    "total_unites": r["total_unites"],
                    "total_ht": r["total_ht"],
                    "ttc": ttc_produit,
                    "tva_taux": tva_taux,
                    "nb_bons": r["nb_bons"],
                    "prix_vente": r.get("prix_vente", 0),
                    "prix_detail": r.get("prix_detail", 0),
                    "prix_gros": r.get("prix_gros", 0),
                    "prix_super_gros": r.get("prix_super_gros", 0)
                }
                clients_data[client_id]["produits"].append(r_dict)
            
            for client_id, data in clients_data.items():
                total_cartons += data["total_cartons"]
                total_unites += data["total_unites"]
                total_ca += data["total_ht"]
                
                qte_cartons = f"{data['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{data['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                
                # ✅ Ajouter un bouton "Détail" dans la colonne Actions
                self.tree.insert("", "end", iid=f"client_{client_id}", values=(
                    data["client_nom"],
                    f"{len(data['produits'])} produits",
                    qte_cartons,
                    qte_unites,
                    f"{data['total_ht']:,.2f} DA",
                    f"{data['total_ttc']:,.2f} DA",
                    "",
                    "🔍 Détail"
                ), tags=("client_row", client_id))
                
                for r_dict in data["produits"]:
                    qte_cartons_prod = f"{r_dict['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                    qte_unites_prod = f"{r_dict['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                    
                    pct = (r_dict['total_ht'] / data['total_ht'] * 100) if data['total_ht'] > 0 else 0
                    
                    tva_affichage = f"TVA {r_dict['tva_taux']:.0f}%"
                    
                    self.tree.insert("", "end", iid=f"client_{client_id}_prod_{r_dict['produit_id']}", values=(
                        "  └ " + r_dict["produit_designation"] + f" ({tva_affichage})",
                        f"{r_dict['nb_bons']} bons",
                        qte_cartons_prod,
                        qte_unites_prod,
                        f"{r_dict['total_ht']:,.2f} DA",
                        f"{r_dict['ttc']:,.2f} DA",
                        f"{pct:.1f}%",
                        ""
                    ), tags=("detail_row",))
            
            self.tree.tag_configure("client_row", foreground=CLR_ACCENT, font=("Segoe UI", 9, "bold"))
            self.tree.tag_configure("detail_row", foreground=CLR_TEXT)
            
        elif mode == "Par Produit":
            produits_data = {}
            for r in rows:
                produit_id = r["produit_id"]
                if produit_id not in produits_data:
                    tva_taux = tva_produits.get(produit_id, 0)
                    produits_data[produit_id] = {
                        "produit_designation": r["produit_designation"],
                        "produit_code": r["produit_code"],
                        "total_cartons": 0,
                        "total_unites": 0,
                        "total_ht": 0,
                        "total_ttc": 0,
                        "nb_bons": 0,
                        "tva_taux": tva_taux,
                        "clients": []
                    }
                
                ttc_produit = r["total_ht"] * (1 + produits_data[produit_id]["tva_taux"] / 100)
                produits_data[produit_id]["total_cartons"] += r["total_cartons"]
                produits_data[produit_id]["total_unites"] += r["total_unites"]
                produits_data[produit_id]["total_ht"] += r["total_ht"]
                produits_data[produit_id]["total_ttc"] += ttc_produit
                produits_data[produit_id]["nb_bons"] += r["nb_bons"]
                
                r_dict = {
                    "client_id": r["client_id"],
                    "client_nom": r["client_nom"],
                    "total_cartons": r["total_cartons"],
                    "total_unites": r["total_unites"],
                    "total_ht": r["total_ht"],
                    "ttc": ttc_produit,
                    "tva_taux": produits_data[produit_id]["tva_taux"],
                    "nb_bons": r["nb_bons"]
                }
                produits_data[produit_id]["clients"].append(r_dict)
            
            for produit_id, data in produits_data.items():
                total_cartons += data["total_cartons"]
                total_unites += data["total_unites"]
                total_ca += data["total_ht"]
                
                qte_cartons = f"{data['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{data['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                
                tva_affichage = f"TVA {data['tva_taux']:.0f}%"
                
                self.tree.insert("", "end", iid=f"produit_{produit_id}", values=(
                    data["produit_designation"] + f" ({tva_affichage})",
                    f"{len(data['clients'])} clients",
                    qte_cartons,
                    qte_unites,
                    f"{data['total_ht']:,.2f} DA",
                    f"{data['total_ttc']:,.2f} DA",
                    "",
                    ""
                ), tags=("produit_row",))
                
                for r_dict in data["clients"]:
                    qte_cartons_client = f"{r_dict['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                    qte_unites_client = f"{r_dict['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                    
                    pct = (r_dict['total_ht'] / data['total_ht'] * 100) if data['total_ht'] > 0 else 0
                    
                    self.tree.insert("", "end", iid=f"produit_{produit_id}_client_{r_dict['client_id']}", values=(
                        "  └ " + r_dict["client_nom"],
                        f"{r_dict['nb_bons']} bons",
                        qte_cartons_client,
                        qte_unites_client,
                        f"{r_dict['total_ht']:,.2f} DA",
                        f"{r_dict['ttc']:,.2f} DA",
                        f"{pct:.1f}%",
                        ""
                    ), tags=("detail_row",))
            
            self.tree.tag_configure("produit_row", foreground=CLR_GREEN, font=("Segoe UI", 9, "bold"))
            self.tree.tag_configure("detail_row", foreground=CLR_TEXT)
            
        else:  # Détail Client-Produit
            for r in rows:
                total_cartons += r["total_cartons"]
                total_unites += r["total_unites"]
                total_ca += r["total_ht"]
                
                tva_taux = tva_produits.get(r["produit_id"], 0)
                ttc = r["total_ht"] * (1 + tva_taux / 100)
                
                qte_cartons = f"{r['total_cartons']:.2f}" if unite_mode in ["cartons", "les deux"] else "-"
                qte_unites = f"{r['total_unites']:.2f}" if unite_mode in ["unités", "les deux"] else "-"
                
                tva_affichage = f"TVA {tva_taux:.0f}%"
                
                self.tree.insert("", "end", iid=f"detail_{r['client_id']}_{r['produit_id']}", values=(
                    r["client_nom"],
                    r["produit_designation"] + f" ({tva_affichage})",
                    qte_cartons,
                    qte_unites,
                    f"{r['total_ht']:,.2f} DA",
                    f"{ttc:,.2f} DA",
                    "",
                    ""
                ))
        
        self.total_cartons_var.set(f"{total_cartons:.2f}")
        self.total_unites_var.set(f"{total_unites:.2f}")
        self.total_ca_var.set(f"{total_ca:,.2f} DA")
        self.nb_lignes_var.set(str(len(self.tree.get_children())))
        
        # ✅ Bind du double-clic sur les lignes clients
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # ✅ Bind du clic sur le bouton "Détail"
        self.tree.bind("<ButtonRelease-1>", self.on_click_detail)
    
    def on_double_click(self, event):
        """Gestion du double-clic sur une ligne"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.selection()
            if item:
                self.show_detail(item[0])
    
    def on_click_detail(self, event):
        """Gestion du clic sur le bouton Détail"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.selection()
            if item and column == "#8":  # Colonne Actions (8ème colonne)
                self.show_detail(item[0])
    
    def show_detail(self, item_id):
        """Affiche le détail des produits achetés par un client"""
        # Vérifier si c'est une ligne client
        if not item_id.startswith("client_"):
            return
        
        try:
            # Extraire l'ID du client
            client_id = int(item_id.split("_")[1])
            
            # Récupérer le nom du client
            conn = get_conn()
            client = conn.execute("SELECT nom FROM clients WHERE id=?", (client_id,)).fetchone()
            conn.close()
            
            if not client:
                messagebox.showerror("Erreur", "Client non trouvé")
                return
            
            # Ouvrir la fenêtre de détail
            DetailVenteClientDialog(self, client_id, client["nom"])
            
        except (ValueError, IndexError):
            messagebox.showerror("Erreur", "Impossible d'ouvrir le détail")
    
    def print_stats(self):
        """Imprime les statistiques"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        headers = ["Client", "Produit", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        client_filter = self.client_var.get()
        produit_filter = self.produit_var.get()
        mode = self.affichage_var.get()
        
        title = f"STATISTIQUES DES VENTES - {mode}"
        if client_filter != "Tous":
            title += f" - Client: {client_filter}"
        if produit_filter != "Tous":
            title += f" - Produit: {produit_filter}"
        
        # Ajouter les totaux
        data.append(["", "", "", "", "", "", ""])
        data.append(["TOTAL", "", 
                    self.total_cartons_var.get(), 
                    self.total_unites_var.get(),
                    "", self.total_ca_var.get(), ""])
        
        print_preview(data, title, headers)
    
    def export_stats_csv(self):
        """Exporte les statistiques en CSV"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        headers = ["Client", "Produit", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="statistiques_ventes.csv"
        )
        
        if filename:
            # Ajouter une ligne de totaux
            data.append(["", "", "", "", "", "", ""])
            data.append(["TOTAL", "", 
                        self.total_cartons_var.get(), 
                        self.total_unites_var.get(),
                        "", self.total_ca_var.get(), ""])
            
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    def export_stats_html(self):
        """Exporte les statistiques en HTML"""
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        headers = ["Client", "Produit", "Qté Cartons", "Qté Unités", "Total HT", "Total TTC", "% du CA"]
        
        client_filter = self.client_var.get()
        produit_filter = self.produit_var.get()
        mode = self.affichage_var.get()
        
        title = f"STATISTIQUES DES VENTES - {mode}"
        if client_filter != "Tous":
            title += f" - Client: {client_filter}"
        if produit_filter != "Tous":
            title += f" - Produit: {produit_filter}"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="statistiques_ventes.html"
        )
        
        if filename:
            # Ajouter une ligne de totaux
            data.append(["", "", "", "", "", "", ""])
            data.append(["TOTAL", "", 
                        self.total_cartons_var.get(), 
                        self.total_unites_var.get(),
                        "", self.total_ca_var.get(), ""])
            
            if export_to_html(data, filename, title, headers):
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)


# ========== DIALOGUE DÉTAIL VENTE CLIENT ==========

class DetailVenteClientDialog(tk.Toplevel):
    """
    Fenêtre de détail des achats d'un client.
    Affiche une table avec : Produit, Quantité (cartons), Prix d'achat, Prix de vente, Total.
    Une checkbox permet de filtrer pour afficher uniquement les produits intéressants.
    """
    
    def __init__(self, parent, client_id, client_nom):
        super().__init__(parent)
        self.parent = parent
        self.client_id = client_id
        self.client_nom = client_nom
        self.data_rows = []  # Stockage des données pour le filtrage
        self.filtre_interet = tk.BooleanVar(value=False)  # Checkbox pour filtrer
        
        self.title(f"📊 Détail des Achats - {client_nom}")
        self.configure(bg=CLR_BG)
        self.geometry("1000x600")
        self.minsize(900, 500)
        
        self._build()
        self.load_data()
        center_window(self, 1000, 600)
    
    def _build(self):
        # Frame principal
        main_frame = tk.Frame(self, bg=CLR_BG, padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # En-tête avec le nom du client
        header_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        header_frame.pack(fill="x", pady=(0, 10))
        
        lbl(header_frame, f"👤 Client: {self.client_nom}", 14, True, CLR_ACCENT).pack(side="left")
        
        # Total des achats
        self.total_achats_var = tk.StringVar(value="0.00 DA")
        lbl(header_frame, "Total: ", 10, True, CLR_MUTED).pack(side="right", padx=5)
        lbl(header_frame, "0.00 DA", 12, True, CLR_GREEN, textvariable=self.total_achats_var).pack(side="right")
        
        # Frame des filtres
        filter_frame = tk.Frame(main_frame, bg=CLR_BG)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        # Checkbox pour filtrer les produits intéressants
        self.check_interet = tk.Checkbutton(
            filter_frame, 
            text="🔍 Afficher uniquement les produits intéressants",
            variable=self.filtre_interet,
            bg=CLR_BG,
            fg=CLR_TEXT,
            selectcolor=CLR_INPUT,
            activebackground=CLR_BG,
            activeforeground=CLR_TEXT,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            relief="flat"
        )
        self.check_interet.pack(side="left", padx=5)
        self.check_interet.bind("<ButtonRelease-1>", self.apply_filter)
        
        # Bouton de réinitialisation
        tk.Button(
            filter_frame, 
            text="🔄 Réinitialiser les filtres", 
            command=self.reset_filters,
            bg=CLR_ORANGE,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2"
        ).pack(side="left", padx=20)
        
        # Tableau des produits
        cols = ["Produit", "Code", "Quantité (cartons)", "Prix Achat", "Prix Vente", "Total", "Intéressant"]
        widths = [250, 100, 120, 100, 100, 120, 100]
        tf, self.tree = make_tree(main_frame, cols, widths)
        tf.pack(fill="both", expand=True, pady=10)
        
        # Cadre de la légende
        legend_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=8)
        legend_frame.pack(fill="x", pady=(0, 10))
        
        lbl(legend_frame, "🟢 Intéressant: ", 9, True, CLR_GREEN).pack(side="left", padx=5)
        lbl(legend_frame, "Marge bénéficiaire élevée (>35%)", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        lbl(legend_frame, "🔴 Non intéressant: ", 9, True, CLR_RED).pack(side="left", padx=(20, 5))
        lbl(legend_frame, "Marge bénéficiaire faible (<20%)", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        # Boutons d'action
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=5)
        
        tk.Button(
            btn_frame,
            text="📋 Exporter CSV",
            command=self.export_csv,
            bg=CLR_ACCENT,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="🖨 Imprimer",
            command=self.print_detail,
            bg=CLR_GREEN,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="❌ Fermer",
            command=self.destroy,
            bg=CLR_RED,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2"
        ).pack(side="right", padx=5)
        
        # ✅ Configuration des tags pour les couleurs
        self.tree.tag_configure("interessant", foreground=CLR_GREEN)
        self.tree.tag_configure("non_interessant", foreground=CLR_RED)
    
    def load_data(self):
        """Charge les données depuis la base de données"""
        self.tree.delete(*self.tree.get_children())
        self.data_rows = []
        
        conn = get_conn()
        
        # ✅ Récupérer les paramètres des filtres depuis la page parente
        date_debut = self.parent.date_debut_var.get()
        date_fin = self.parent.date_fin_var.get()
        
        # ✅ Requête pour obtenir les achats du client avec les prix d'achat et de vente
        query = """
            SELECT 
                p.id as produit_id,
                p.code as produit_code,
                p.designation as produit_designation,
                p.prix_achat,
                p.prix_detail,
                p.prix_vente,
                p.facteur_conversion,
                COALESCE(SUM(lv.quantite / NULLIF(p.facteur_conversion, 0)), 0) as total_cartons,
                COALESCE(AVG(lv.prix_unitaire), 0) as prix_moyen_vente,
                COALESCE(SUM(lv.total), 0) as total_ht
            FROM bons_vente bv
            JOIN lignes_vente lv ON bv.id = lv.bon_id
            JOIN produits p ON lv.produit_id = p.id
            WHERE bv.client_id = ? AND bv.statut = 'Validé'
        """
        params = [self.client_id]
        
        # ✅ Ajouter les filtres de dates si présents
        if date_debut and date_fin:
            query += " AND bv.date_bon BETWEEN ? AND ?"
            params.extend([date_debut, date_fin])
        
        query += " GROUP BY p.id, p.code, p.designation, p.prix_achat, p.prix_detail, p.prix_vente, p.facteur_conversion"
        query += " ORDER BY total_cartons DESC"
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        # ✅ Stocker les données pour le filtrage
        total_general = 0
        
        for r in rows:
            produit_id = r["produit_id"]
            code = r["produit_code"]
            designation = r["produit_designation"]
            prix_achat = r["prix_achat"] or 0
            prix_detail = r["prix_detail"] or r["prix_vente"] or 0
            prix_vente = r["prix_vente"] or prix_detail
            total_cartons = r["total_cartons"]
            total_ht = r["total_ht"]
            
            # ✅ Déterminer si le produit est intéressant (marge > 35%)
            marge = 0
            if prix_achat > 0:
                marge = ((prix_vente - prix_achat) / prix_achat) * 100
            
            interessant = marge > 35
            
            row_data = {
                "produit_id": produit_id,
                "code": code,
                "designation": designation,
                "prix_achat": prix_achat,
                "prix_detail": prix_detail,
                "prix_vente": prix_vente,
                "total_cartons": total_cartons,
                "total_ht": total_ht,
                "marge": marge,
                "interessant": interessant
            }
            self.data_rows.append(row_data)
            total_general += total_ht
            
            # ✅ Déterminer la couleur selon la marge
            if interessant:
                tag = "interessant"
            elif marge < 20:
                tag = "non_interessant"
            else:
                tag = ""
            
            # ✅ Ajouter à l'arbre avec les bons tags
            self.tree.insert("", "end", iid=str(len(self.data_rows)-1), values=(
                designation,
                code,
                f"{total_cartons:.2f}",
                f"{prix_achat:.2f} DA",
                f"{prix_vente:.2f} DA",
                f"{total_ht:.2f} DA",
                "⭐" if interessant else "⚠️" if marge < 20 else "➖"
            ), tags=(tag,) if tag else ())
        
        # Mettre à jour le total
        self.total_achats_var.set(f"{total_general:,.2f} DA")
        
        # Mettre à jour le total des lignes
        nb_lignes = len(self.data_rows)
        # (Optionnel) Ajouter un label pour le nombre de lignes
    
    def apply_filter(self, event=None):
        """Applique le filtre pour afficher uniquement les produits intéressants"""
        self.tree.delete(*self.tree.get_children())
        
        filtre_interet = self.filtre_interet.get()
        total_general = 0
        
        for i, row_data in enumerate(self.data_rows):
            # Si le filtre est activé et que le produit n'est pas intéressant, on le saute
            if filtre_interet and not row_data["interessant"]:
                continue
            
            total_general += row_data["total_ht"]
            
            # Déterminer la couleur
            if row_data["interessant"]:
                tag = "interessant"
            elif row_data["marge"] < 20:
                tag = "non_interessant"
            else:
                tag = ""
            
            # Ajouter à l'arbre
            self.tree.insert("", "end", iid=str(i), values=(
                row_data["designation"],
                row_data["code"],
                f"{row_data['total_cartons']:.2f}",
                f"{row_data['prix_achat']:.2f} DA",
                f"{row_data['prix_vente']:.2f} DA",
                f"{row_data['total_ht']:.2f} DA",
                "⭐" if row_data["interessant"] else "⚠️" if row_data["marge"] < 20 else "➖"
            ), tags=(tag,) if tag else ())
        
        # Mettre à jour le total affiché
        self.total_achats_var.set(f"{total_general:,.2f} DA")
        
        # Mettre à jour l'état de la checkbox
        if filtre_interet:
            nb_interessants = sum(1 for r in self.data_rows if r["interessant"])
            self.check_interet.config(text=f"🔍 Afficher uniquement les produits intéressants ({nb_interessants} produits)")
        else:
            self.check_interet.config(text="🔍 Afficher uniquement les produits intéressants")
    
    def reset_filters(self):
        """Réinitialise tous les filtres"""
        self.filtre_interet.set(False)
        self.apply_filter()
    
    def export_csv(self):
        """Exporte les données en CSV"""
        if not self.data_rows:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"achats_{self.client_nom}.csv"
        )
        
        if not filename:
            return
        
        # Préparer les données
        headers = ["Code", "Produit", "Quantité (cartons)", "Prix Achat", "Prix Vente", "Total", "Intéressant"]
        data = []
        
        # Utiliser les données filtrées
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        # Ajouter la ligne de total
        data.append(["", "", "", "", "", "", ""])
        data.append(["TOTAL", "", "", "", "", self.total_achats_var.get(), ""])
        
        if export_to_csv(data, filename, headers):
            messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    def print_detail(self):
        """Imprime le détail"""
        if not self.data_rows:
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        # Préparer les données
        headers = ["Code", "Produit", "Quantité (cartons)", "Prix Achat", "Prix Vente", "Total", "Intéressant"]
        data = []
        
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        # Ajouter la ligne de total
        data.append(["", "", "", "", "", "", ""])
        data.append(["TOTAL", "", "", "", "", self.total_achats_var.get(), ""])
        
        title = f"DÉTAIL DES ACHATS - {self.client_nom}"
        if self.filtre_interet.get():
            title += " (Produits intéressants uniquement)"
        
        print_preview(data, title, headers)                        
# ========== PAGE FACTURES ==========

class FacturePage(tk.Frame):
    """Page de gestion des factures"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "🧾  Gestion des Factures", 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouvelle Facture", command=self.nouvelle_facture,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        # Filtre par statut
        lbl(sf, "Statut:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.statut_var = tk.StringVar(value="Tous")
        statut_combo = combo(sf, ["Tous", "Émise", "Payée", "Annulée"], width=12, textvariable=self.statut_var)
        statut_combo.pack(side="left", padx=5)
        statut_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        cols = ["Numéro", "Date", "Client", "Bon Vente", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        widths = [120, 100, 200, 100, 100, 60, 120, 100, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_facture,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_facture,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_facture,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_factures,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="📊 Exporter", command=self.export_factures,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        # Double-clic pour modifier
        self.tree.bind("<Double-1>", lambda e: self.edit_facture())
    
    def refresh(self):
        q = self.search_var.get().lower()
        statut = self.statut_var.get()
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if statut == "Tous":
            rows = conn.execute("""
                SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
                FROM factures f
                JOIN clients c ON f.client_id = c.id
                JOIN bons_vente bv ON f.bon_vente_id = bv.id
                ORDER BY f.date_facture DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
                FROM factures f
                JOIN clients c ON f.client_id = c.id
                JOIN bons_vente bv ON f.bon_vente_id = bv.id
                WHERE f.statut = ?
                ORDER BY f.date_facture DESC
            """, (statut,)).fetchall()
        conn.close()
        
        for r in rows:
            if q in r["numero"].lower() or q in r["client_nom"].lower():
                # Couleur selon le statut
                tag = None
                if r["statut"] == "Payée":
                    tag = "payee"
                elif r["statut"] == "Annulée":
                    tag = "annulee"
                
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], r["date_facture"], r["client_nom"],
                    r["bon_numero"], f"{r['total_ht']:,.2f}", 
                    f"{r['tva']:.0f}%", f"{r['total_ttc']:,.2f}",
                    r["statut"], r["date_echeance"] or ""
                ), tags=(tag,) if tag else ())
        
        self.tree.tag_configure("payee", foreground=CLR_GREEN)
        self.tree.tag_configure("annulee", foreground=CLR_RED)
    
    def nouvelle_facture(self):
        d = FactureDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def view_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture")
            return
        d = FactureDetailDialog(self, sel[0])
        self.wait_window(d)
    
    def edit_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture à modifier")
            return
        d = FactureEditDialog(self, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture à supprimer")
            return
        
        if messagebox.askyesno("Confirmation", "⚠️ Supprimer définitivement cette facture ?\nCette action est irréversible."):
            conn = get_conn()
            try:
                facture_id = sel[0]
                conn.execute("DELETE FROM facture_tva_details WHERE facture_id=?", (facture_id,))
                conn.execute("DELETE FROM factures WHERE id=?", (facture_id,))
                conn.commit()
                messagebox.showinfo("Succès", "Facture supprimée")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()
    
    def get_factures_data(self):
        """Récupérer les données des factures pour export"""
        conn = get_conn()
        rows = conn.execute("""
            SELECT f.numero, f.date_facture, c.nom as client, 
                   f.total_ht, f.tva, f.total_ttc, f.statut, f.date_echeance
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            ORDER BY f.date_facture DESC
        """).fetchall()
        conn.close()
        
        data = []
        for r in rows:
            data.append([
                r["numero"], r["date_facture"], r["client"],
                f"{r['total_ht']:,.2f}", f"{r['tva']:.0f}%",
                f"{r['total_ttc']:,.2f}", r["statut"], r["date_echeance"] or ""
            ])
        return data
    
    def print_factures(self):
        data = self.get_factures_data()
        headers = ["Numéro", "Date", "Client", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        print_preview(data, "LISTE DES FACTURES", headers)
    
    def export_factures(self):
        data = self.get_factures_data()
        headers = ["Numéro", "Date", "Client", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="factures.csv"
        )
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "LISTE DES FACTURES", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")


class FactureDialog(tk.Toplevel):
    """Dialogue de création de facture"""
    
    def __init__(self, parent, pre_selected_bon=None):
        super().__init__(parent)
        self.pre_selected_bon = pre_selected_bon
        self.title("Nouvelle Facture")
        self.configure(bg=CLR_BG)
        self.geometry("750x600")
        self._build()
        center_window(self, 750, 600)
    
    def _build(self):
            main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            # Titre
            lbl(main_frame, "📄 CRÉATION DE FACTURE", 14, True, CLR_ACCENT).pack(pady=(0,15))
            
            # Sélection du bon de vente
            frame_bon = tk.LabelFrame(main_frame, text="1. Sélectionner le Bon de Vente", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_bon.pack(fill="x", pady=10)
            
            lbl(frame_bon, "Bon de vente:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            
            # Charger les bons de vente non facturés
            conn = get_conn()
            bons = conn.execute("""
                SELECT bv.id, bv.numero, c.nom as client_nom, bv.total, bv.date_bon
                FROM bons_vente bv
                JOIN clients c ON bv.client_id = c.id
                WHERE bv.id NOT IN (SELECT bon_vente_id FROM factures WHERE bon_vente_id IS NOT NULL)
                AND bv.statut = 'Validé'
                ORDER BY bv.date_bon DESC
            """).fetchall()
            conn.close()
            
            self.bons_map = {}
            bon_liste = []
            for b in bons:
                display = f"{b['numero']} - {b['client_nom']} - {b['total']:,.2f} DA"
                self.bons_map[display] = dict(b)
                bon_liste.append(display)
            
            self.bon_var = tk.StringVar()
            self.bon_combo = combo(frame_bon, bon_liste, width=40, textvariable=self.bon_var)
            self.bon_combo.pack(side="left", padx=10, fill="x", expand=True)
            self.bon_combo.bind("<<ComboboxSelected>>", self.on_bon_selected)
            
            if bon_liste:
                self.bon_var.set(bon_liste[0])
            
            # Informations de la facture
            frame_info = tk.LabelFrame(main_frame, text="2. Informations de la facture", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_info.pack(fill="x", pady=10)
            
            # Numéro de facture (auto)
            row1 = tk.Frame(frame_info, bg=CLR_CARD)
            row1.pack(fill="x", pady=5)
            lbl(row1, "Numéro facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.num_var = tk.StringVar(value=next_numero("FC", "factures"))
            entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
            
            # Date facture
            self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            DateEntry(row1, self.date_var, label_text="Date facture:", width=12).pack(side="left", padx=10)
            
            # Date échéance
            row2 = tk.Frame(frame_info, bg=CLR_CARD)
            row2.pack(fill="x", pady=5)
            lbl(row2, "Date échéance:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.echeance_var = tk.StringVar(value="")
            entry(row2, width=15, textvariable=self.echeance_var).pack(side="left", padx=10)
            lbl(row2, "(Optionnel - format YYYY-MM-DD)", 8, False, CLR_MUTED).pack(side="left", padx=10)
            
            # TVA - mode automatique basé sur les produits
            row3 = tk.Frame(frame_info, bg=CLR_CARD)
            row3.pack(fill="x", pady=5)
            lbl(row3, "TVA:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            lbl(row3, "Calculée automatiquement par produit", 9, False, True, CLR_GREEN).pack(side="left", padx=10)            
            # Observations
            row4 = tk.Frame(frame_info, bg=CLR_CARD)
            row4.pack(fill="x", pady=5)
            lbl(row4, "Observations:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.obs_var = tk.StringVar(value="")
            entry(row4, width=50, textvariable=self.obs_var).pack(side="left", padx=10, fill="x", expand=True)
            
            # Récapitulatif
            frame_recap = tk.LabelFrame(main_frame, text="3. Récapitulatif", 
                                        bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                        padx=15, pady=10)
            frame_recap.pack(fill="x", pady=10)
            
            recap_inner = tk.Frame(frame_recap, bg=CLR_CARD)
            recap_inner.pack(fill="x")
            
            # CORRECTION : ordre correct des arguments pour lbl()
            lbl1 = tk.Label(recap_inner, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl1.grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.total_ht_var = tk.StringVar(value="0.00 DA")
            lbl1_val = tk.Label(recap_inner, textvariable=self.total_ht_var, bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 11, "bold"))
            lbl1_val.grid(row=0, column=1, sticky="w", padx=10, pady=2)
            
            lbl2 = tk.Label(recap_inner, text="TVA:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl2.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            self.tva_montant_var = tk.StringVar(value="0.00 DA")
            lbl2_val = tk.Label(recap_inner, textvariable=self.tva_montant_var, bg=CLR_CARD, fg=CLR_ORANGE, font=("Segoe UI", 11, "bold"))
            lbl2_val.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            
            lbl3 = tk.Label(recap_inner, text="Total TTC:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl3.grid(row=2, column=0, sticky="w", padx=5, pady=2)
            self.total_ttc_var = tk.StringVar(value="0.00 DA")
            lbl3_val = tk.Label(recap_inner, textvariable=self.total_ttc_var, bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 14, "bold"))
            lbl3_val.grid(row=2, column=1, sticky="w", padx=10, pady=2)
            
            # Boutons
            btn_frame = tk.Frame(main_frame, bg=CLR_BG)
            btn_frame.pack(fill="x", pady=15)
            
            tk.Button(btn_frame, text="✅ CRÉER LA FACTURE", command=self.save,
                    bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                    padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                    bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
            
            # Initialiser l'affichage
            self.on_bon_selected()
    
    def on_bon_selected(self, event=None):
        """Mettre à jour le récapitulatif quand un bon est sélectionné"""
        key = self.bon_var.get()
        if key and key in self.bons_map:
            bon = self.bons_map[key]
            
            conn = get_conn()
            lignes = conn.execute("""
                SELECT l.total, p.tva
                FROM lignes_vente l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.bon_id = ?
            """, (bon["id"],)).fetchall()
            conn.close()
            
            # Regrouper par taux de TVA
            self.tva_details = {}  # {taux: total_ht}
            total_ht = 0
            total_tva = 0
            for l in lignes:
                taux = l["tva"] if l["tva"] is not None else 19
                ht = l["total"]
                tva_montant = ht * taux / 100
                self.tva_details[taux] = self.tva_details.get(taux, 0) + ht
                total_ht += ht
                total_tva += tva_montant
            
            total_ttc = total_ht + total_tva
            
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            self.tva_montant_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
    
    def save(self):
        key = self.bon_var.get()
        if not key or key not in self.bons_map:
            messagebox.showerror("Erreur", "Sélectionnez un bon de vente")
            return
        
        bon = self.bons_map[key]
        
        conn = get_conn()
        try:
            bon_data = conn.execute("SELECT client_id FROM bons_vente WHERE id = ?", (bon["id"],)).fetchone()
            if not bon_data:
                messagebox.showerror("Erreur", "Bon de vente non trouvé")
                return
            client_id = bon_data["client_id"]
            
            # Recalculer HT/TVA/TTC par produit
            lignes = conn.execute("""
                SELECT l.total, p.tva
                FROM lignes_vente l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.bon_id = ?
            """, (bon["id"],)).fetchall()
            
            tva_details = {}
            total_ht = 0
            total_tva = 0
            for l in lignes:
                taux = l["tva"] if l["tva"] is not None else 19
                ht = l["total"]
                tva_montant = ht * taux / 100
                if taux not in tva_details:
                    tva_details[taux] = {"ht": 0, "tva": 0}
                tva_details[taux]["ht"] += ht
                tva_details[taux]["tva"] += tva_montant
                total_ht += ht
                total_tva += tva_montant
            
            total_ttc = total_ht + total_tva
            
            # TVA "moyenne" pour compat avec l'ancien champ tva (en %)
            tva_moyenne = (total_tva / total_ht * 100) if total_ht > 0 else 0
            
            conn.execute("""
                INSERT INTO factures(numero, date_facture, bon_vente_id, client_id, 
                                    total_ht, tva, total_ttc, statut, date_echeance, observations)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.num_var.get(), self.date_var.get(), bon["id"], client_id,
                total_ht, tva_moyenne, total_ttc, "Émise", 
                self.echeance_var.get() or None, self.obs_var.get() or None
            ))
            
            facture_id = conn.execute("SELECT id FROM factures WHERE numero=?", (self.num_var.get(),)).fetchone()["id"]
            
            for taux, vals in tva_details.items():
                conn.execute("""
                    INSERT INTO facture_tva_details(facture_id, taux_tva, total_ht, total_tva)
                    VALUES(?, ?, ?, ?)
                """, (facture_id, taux, vals["ht"], vals["tva"]))
            
            conn.commit()
            messagebox.showinfo("Succès", f"Facture {self.num_var.get()} créée avec succès !")
            self.destroy()
        except sqlite3.IntegrityError:
            nouveau_num = next_numero("FC", "factures")
            self.num_var.set(nouveau_num)
            messagebox.showwarning("Numéro dupliqué", 
                                 f"Le numéro existait déjà.\nNouveau numéro: {nouveau_num}\nVeuillez réessayer.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            conn.rollback()
        finally:
            conn.close()


class FactureEditDialog(tk.Toplevel):
    """Dialogue de modification de facture"""
    
    def __init__(self, parent, facture_id):
        super().__init__(parent)
        self.facture_id = facture_id
        self.title("Modifier Facture")
        self.configure(bg=CLR_BG)
        self.geometry("750x550")
        self._load_data()
        self._build()
        center_window(self, 750, 550)
    
    def _load_data(self):
        conn = get_conn()
        self.facture = conn.execute("""
            SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            JOIN bons_vente bv ON f.bon_vente_id = bv.id
            WHERE f.id = ?
        """, (self.facture_id,)).fetchone()
        conn.close()
    
    def _build(self):
            main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            lbl(main_frame, "✏ MODIFICATION FACTURE", 14, True, CLR_ACCENT).pack(pady=(0,15))
            
            # Informations
            frame_info = tk.LabelFrame(main_frame, text="Informations", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_info.pack(fill="x", pady=10)
            
            # Numéro (non modifiable)
            row1 = tk.Frame(frame_info, bg=CLR_CARD)
            row1.pack(fill="x", pady=5)
            lbl(row1, "Numéro facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.num_var = tk.StringVar(value=self.facture["numero"])
            entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
            
            lbl(row1, "Bon de vente:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            lbl1 = tk.Label(row1, text=self.facture["bon_numero"], bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 9, "bold"))
            lbl1.pack(side="left", padx=10)
            
            # Date facture
            row2 = tk.Frame(frame_info, bg=CLR_CARD)
            row2.pack(fill="x", pady=5)
            lbl(row2, "Date facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.date_var = tk.StringVar(value=self.facture["date_facture"])
            entry(row2, width=15, textvariable=self.date_var).pack(side="left", padx=10)
            
            lbl(row2, "Client:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            lbl2 = tk.Label(row2, text=self.facture["client_nom"], bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 9, "bold"))
            lbl2.pack(side="left", padx=10)
            
            # Date échéance
            row3 = tk.Frame(frame_info, bg=CLR_CARD)
            row3.pack(fill="x", pady=5)
            lbl(row3, "Date échéance:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.echeance_var = tk.StringVar(value=self.facture["date_echeance"] or "")
            entry(row3, width=15, textvariable=self.echeance_var).pack(side="left", padx=10)
            
            # Statut
            lbl(row3, "Statut:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            self.statut_var = tk.StringVar(value=self.facture["statut"])
            statut_combo = combo(row3, ["Émise", "Payée", "Annulée"], width=12, textvariable=self.statut_var)
            statut_combo.pack(side="left", padx=10)
            
            # TVA
            row4 = tk.Frame(frame_info, bg=CLR_CARD)
            row4.pack(fill="x", pady=5)
            lbl(row4, "TVA (%):", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.tva_var = tk.StringVar(value=str(self.facture["tva"]))
            tva_spin = tk.Spinbox(row4, from_=0, to=50, increment=1, width=10,
                                textvariable=self.tva_var, bg=CLR_INPUT, fg=CLR_TEXT,
                                relief="flat", font=("Segoe UI", 10))
            tva_spin.pack(side="left", padx=10)
            
            # Observations
            row5 = tk.Frame(frame_info, bg=CLR_CARD)
            row5.pack(fill="x", pady=5)
            lbl(row5, "Observations:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.obs_var = tk.StringVar(value=self.facture["observations"] or "")
            entry(row5, width=50, textvariable=self.obs_var).pack(side="left", padx=10, fill="x", expand=True)
            
            # Récapitulatif
            frame_recap = tk.LabelFrame(main_frame, text="Récapitulatif", 
                                        bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                        padx=15, pady=10)
            frame_recap.pack(fill="x", pady=10)
            
            recap_inner = tk.Frame(frame_recap, bg=CLR_CARD)
            recap_inner.pack(fill="x")
            
            # CORRECTION : utilisation directe de tk.Label
            lbl_ht = tk.Label(recap_inner, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_ht.grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.total_ht_var = tk.StringVar(value=f"{self.facture['total_ht']:,.2f} DA")
            val_ht = tk.Label(recap_inner, textvariable=self.total_ht_var, bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 11, "bold"))
            val_ht.grid(row=0, column=1, sticky="w", padx=10, pady=2)
            
            lbl_tva = tk.Label(recap_inner, text="TVA montant:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_tva.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            tva_montant = self.facture['total_ht'] * self.facture['tva'] / 100
            self.tva_montant_var = tk.StringVar(value=f"{tva_montant:,.2f} DA")
            val_tva = tk.Label(recap_inner, textvariable=self.tva_montant_var, bg=CLR_CARD, fg=CLR_ORANGE, font=("Segoe UI", 11, "bold"))
            val_tva.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            
            lbl_ttc = tk.Label(recap_inner, text="Total TTC:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_ttc.grid(row=2, column=0, sticky="w", padx=5, pady=2)
            self.total_ttc_var = tk.StringVar(value=f"{self.facture['total_ttc']:,.2f} DA")
            val_ttc = tk.Label(recap_inner, textvariable=self.total_ttc_var, bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 14, "bold"))
            val_ttc.grid(row=2, column=1, sticky="w", padx=10, pady=2)
            
            # Mettre à jour quand TVA change
            self.tva_var.trace_add("write", self.update_totals)
            
            # Boutons
            btn_frame = tk.Frame(main_frame, bg=CLR_BG)
            btn_frame.pack(fill="x", pady=15)
            
            tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                    bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                    padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="🖨 APERÇU/IMPRESSION", command=self.print_facture,
                    bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                    bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def update_totals(self, *args):
        try:
            total_ht = self.facture["total_ht"]
            tva_pct = float(self.tva_var.get() or 0)
            tva_montant = total_ht * tva_pct / 100
            total_ttc = total_ht + tva_montant
            
            self.tva_montant_var.set(f"{tva_montant:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
        except (ValueError, TypeError):
            pass
    
    def save(self):
        conn = get_conn()
        try:
            # ✅ Recalculer le TTC depuis les détails TVA réels (pas depuis le champ tva%)
            tva_details = conn.execute(
                "SELECT * FROM facture_tva_details WHERE facture_id=?",
                (self.facture_id,)
            ).fetchall()

            if tva_details:
                total_tva = sum(d["total_tva"] for d in tva_details)
                total_ht  = sum(d["total_ht"]  for d in tva_details)
                total_ttc = total_ht + total_tva
                # tva_moyenne pour compat avec l'ancien champ
                tva_pct = (total_tva / total_ht * 100) if total_ht > 0 else 0
            else:
                # Fallback si pas de détails (ancienne facture)
                try:
                    tva_pct = float(self.tva_var.get() or 0)
                except ValueError:
                    messagebox.showerror("Erreur", "TVA invalide")
                    return
                total_ht  = self.facture["total_ht"]
                total_tva = total_ht * tva_pct / 100
                total_ttc = total_ht + total_tva

            conn.execute("""
                UPDATE factures
                SET date_facture=?, tva=?, total_ttc=?, statut=?,
                    date_echeance=?, observations=?
                WHERE id=?
            """, (
                self.date_var.get(), tva_pct, total_ttc,
                self.statut_var.get(),
                self.echeance_var.get() or None,
                self.obs_var.get() or None,
                self.facture_id
            ))
            conn.commit()
            messagebox.showinfo("Succès", "Facture modifiée avec succès")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def print_facture(self):
        """Afficher l'aperçu de la facture"""
        d = FactureDetailDialog(self, self.facture_id, parent=self)
        # Ne pas attendre la fermeture


class FactureDetailDialog(tk.Toplevel):
    """Dialogue de détail et impression de facture"""
    
    def __init__(self, parent, facture_id, parent_window=None):
        super().__init__(parent)
        self.facture_id = facture_id
        self.parent_window = parent_window or self
        self.title("Détail Facture")
        self.configure(bg=CLR_BG)
        self.geometry("1400x750")
        self.minsize(1200, 650)
        self._load_data()
        self._build()
        center_window(self, 1200, 750)
    
    def _load_data(self):
        conn = get_conn()
        self.facture = conn.execute("""
            SELECT f.*, c.nom as client_nom, c.adresse as client_adresse, 
                   c.tel as client_tel, c.email as client_email,
                   bv.numero as bon_numero, bv.date_bon
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            JOIN bons_vente bv ON f.bon_vente_id = bv.id
            WHERE f.id = ?
        """, (self.facture_id,)).fetchone()
        
        # Lignes du bon de vente
        self.lignes = conn.execute("""
            SELECT l.*, p.designation, p.unite
            FROM lignes_vente l
            JOIN produits p ON l.produit_id = p.id
            WHERE l.bon_id = ?
        """, (self.facture["bon_vente_id"],)).fetchall()
        self.tva_details = conn.execute("""
            SELECT * FROM facture_tva_details WHERE facture_id = ? """, (self.facture_id,)).fetchall()
        conn.close()
    
    def _build(self):
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ Ajouter cette ligne — indispensable pour que la colonne gauche s'étire
        main_container.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0)

        # ========== COLONNE GAUCHE ==========
        left_container = tk.Frame(main_container, bg=CLR_BG)
        left_container.grid(row=0, column=0, sticky="nsew")

        canvas = tk.Canvas(left_container, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

        # ========== COLONNE DROITE ==========
        right_container = tk.Frame(main_container, bg=CLR_SIDEBAR, width=180)
        right_container.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        right_container.grid_propagate(False)  # ✅ grid_propagate et non pack_propagate

        lbl(right_container, "ACTIONS", 10, True, color=CLR_ACCENT).pack(pady=(15, 10))

        sep = tk.Frame(right_container, bg=CLR_BORDER, height=2)
        sep.pack(fill="x", padx=10, pady=5)

        btn_print = tk.Button(right_container, text="🖨  Imprimer", command=self.print_facture,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_print.pack(pady=8, padx=10)

        btn_pdf = tk.Button(right_container, text="📄  PDF", command=self.export_pdf,
                            bg=CLR_GREEN, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_pdf.pack(pady=8, padx=10)

        sep2 = tk.Frame(right_container, bg=CLR_BORDER, height=2)
        sep2.pack(fill="x", padx=10, pady=5)

        btn_close = tk.Button(right_container, text="❌  Fermer", command=self.destroy,
                            bg=CLR_RED, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_close.pack(pady=8, padx=10)
        
        # ========== CONTENU SCROLLABLE ==========
        
        # En-tête avec profil entreprise
        profil = get_profil_by_type("facture")
        if profil:
            nom_entreprise = profil.get("nom", "") or "VOTRE SOCIÉTÉ"
            adresse_entreprise = profil.get("adresse", "") or ""
            ville_entreprise = profil.get("ville", "") or ""
            telephone_entreprise = profil.get("telephone", "") or ""
            email_entreprise = profil.get("email", "") or ""
            nif = profil.get("nif", "") or ""
            nis = profil.get("nis", "") or ""
            nrc = profil.get("nrc", "") or ""
        else:
            nom_entreprise = "VOTRE SOCIÉTÉ"
            adresse_entreprise = ville_entreprise = telephone_entreprise = ""
            email_entreprise = nif = nis = nrc = ""
        
        header_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=20, pady=15)
        header_frame.pack(fill="x", pady=(0,15))
        
        lbl(header_frame, nom_entreprise, 18, True, color=CLR_ACCENT).pack(anchor="center")
        if adresse_entreprise:
            lbl(header_frame, adresse_entreprise, 9, color=CLR_MUTED).pack(anchor="center")
        if ville_entreprise:
            lbl(header_frame, ville_entreprise, 9, color=CLR_MUTED).pack(anchor="center")
        if telephone_entreprise:
            lbl(header_frame, f"Tél: {telephone_entreprise}", 9, color=CLR_MUTED).pack(anchor="center")
        if email_entreprise:
            lbl(header_frame, f"Email: {email_entreprise}", 9, color=CLR_MUTED).pack(anchor="center")
        
        fiscal_text = ""
        if nif:
            fiscal_text += f"NIF: {nif}  "
        if nis:
            fiscal_text += f"NIS: {nis}  "
        if nrc:
            fiscal_text += f"NRC: {nrc}"
        if fiscal_text:
            lbl(header_frame, fiscal_text, 8, color=CLR_MUTED).pack(anchor="center", pady=(5,0))
        
        lbl(header_frame, "="*60, 9, color=CLR_BORDER).pack(pady=8)
        lbl(header_frame, f"FACTURE N° {self.facture['numero']}", 16, True, color=CLR_GREEN).pack(anchor="center")
        
        # Frame pour les informations client et facture (2 colonnes)
        info_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=10)
        
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)
        
        # Colonne gauche - Client
        left_info = tk.LabelFrame(info_frame, text="📌 CLIENT", bg=CLR_CARD, fg=CLR_ACCENT, 
                                  font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        left_info.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        lbl(left_info, self.facture['client_nom'], 10, True).pack(anchor="w", pady=2)
        if self.facture['client_adresse']:
            lbl(left_info, self.facture['client_adresse'], 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        if self.facture['client_tel']:
            lbl(left_info, f"Tél: {self.facture['client_tel']}", 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        if self.facture['client_email']:
            lbl(left_info, f"Email: {self.facture['client_email']}", 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        
        # Colonne droite - Facture
        right_info = tk.LabelFrame(info_frame, text="📄 FACTURE", bg=CLR_CARD, fg=CLR_ACCENT,
                                   font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        right_info.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        lbl(right_info, f"Numéro: {self.facture['numero']}", 9).pack(anchor="w", pady=2)
        lbl(right_info, f"Date: {self.facture['date_facture']}", 9).pack(anchor="w", pady=2)
        lbl(right_info, f"Bon de vente: {self.facture['bon_numero']}", 9).pack(anchor="w", pady=2)
        if self.facture['date_echeance']:
            lbl(right_info, f"Échéance: {self.facture['date_echeance']}", 9).pack(anchor="w", pady=2)
        
        statut_color = CLR_GREEN if self.facture['statut'] == 'Payée' else (CLR_RED if self.facture['statut'] == 'Annulée' else CLR_ORANGE)
        lbl(right_info, f"Statut: {self.facture['statut']}", 9, True, color=statut_color).pack(anchor="w", pady=2)
        
        # Tableau des produits
        table_frame = tk.LabelFrame(scrollable_frame, text="📦 DÉTAIL DES PRODUITS", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=10)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ["Désignation", "Quantité", "Unité", "Prix Unitaire", "Total"]
        widths = [350, 80, 60, 100, 120]
        
        tree_frame = tk.Frame(table_frame, bg=CLR_CARD)
        tree_frame.pack(fill="both", expand=True)
        
        style = ttk.Style()
        style.configure("Facture.Treeview", background=CLR_INPUT, foreground=CLR_TEXT, rowheight=28)
        style.configure("Facture.Treeview.Heading", background=CLR_ACCENT, foreground="white", font=("Segoe UI", 9, "bold"))
        
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10, style="Facture.Treeview")
        
        for i, col in enumerate(cols):
            tree.heading(col, text=col)
            if col in ["Quantité", "Unité"]:
                tree.column(col, width=widths[i], anchor="center")
            elif col in ["Prix Unitaire", "Total"]:
                tree.column(col, width=widths[i], anchor="e")
            else:
                tree.column(col, width=widths[i], anchor="w")
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        for l in self.lignes:
            tree.insert("", "end", values=(
                l["designation"],
                f"{l['quantite']:.2f}",
                l["unite"] or "Pcs",
                f"{l['prix_unitaire']:.2f}",
                f"{l['total']:.2f}"
            ))
        
        # Totaux
        total_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=15, pady=10)
        total_frame.pack(fill="x", pady=10)
        
        tva_montant = self.facture['total_ht'] * self.facture['tva'] / 100
        
        total_inner = tk.Frame(total_frame, bg=CLR_CARD)
        total_inner.pack(side="right")
        
        row1 = tk.Frame(total_inner, bg=CLR_CARD)
        row1.pack(fill="x", pady=3)
        lbl(row1, "Total HT:", 11, True, color=CLR_MUTED).pack(side="left", padx=10)
        lbl(row1, f"{self.facture['total_ht']:,.2f} DA", 11, True, color=CLR_TEXT).pack(side="left", padx=10)
        
        # Détail TVA par taux
        for tva_d in self.tva_details:
            row_tva = tk.Frame(total_inner, bg=CLR_CARD)
            row_tva.pack(fill="x", pady=2)
            lbl(row_tva, f"TVA ({tva_d['taux_tva']:.0f}%) sur {tva_d['total_ht']:,.2f} DA:", 10, False, color=CLR_MUTED).pack(side="left", padx=10)
            lbl(row_tva, f"{tva_d['total_tva']:,.2f} DA", 10, True, color=CLR_ORANGE).pack(side="left", padx=10)
        row3 = tk.Frame(total_inner, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        lbl(row3, "TOTAL TTC:", 13, True, color=CLR_MUTED).pack(side="left", padx=10)
        lbl(row3, f"{self.facture['total_ttc']:,.2f} DA", 15, True, color=CLR_GREEN).pack(side="left", padx=10)
        
        # Observations
        if self.facture['observations']:
            obs_frame = tk.LabelFrame(scrollable_frame, text="📝 OBSERVATIONS", 
                                      bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 9, "bold"),
                                      padx=15, pady=10)
            obs_frame.pack(fill="x", pady=10)
            lbl(obs_frame, self.facture['observations'], 9, color=CLR_TEXT, wraplength=800).pack(anchor="w")
        
        # Footer
        footer_frame = tk.Frame(scrollable_frame, bg=CLR_BG, padx=15, pady=15)
        footer_frame.pack(fill="x")
        
        lbl(footer_frame, "Merci pour votre confiance !", 9, color=CLR_MUTED).pack()
        lbl(footer_frame, f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}", 8, color=CLR_MUTED).pack()
    
    def _get_html(self) -> str:
        from gestion_stock import get_profil_by_type
        profil = get_profil_by_type("facture")
        fac = dict(self.facture)
        fac["bon_numero"] = self.facture.get("bon_numero", "")
        
        html = hr.build_facture_html(
            profil      = profil,
            facture     = fac,
            lignes      = [dict(l) for l in self.lignes],
            tva_details = [dict(t) for t in self.tva_details],
        )
        
        # ✅ AJOUT DES STYLES D'IMPRESSION
        print_styles = """
        <style>
            @media print {
                * {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    box-shadow: none !important;
                    text-shadow: none !important;
                    background-image: none !important;
                    filter: none !important;
                    -webkit-filter: none !important;
                    opacity: 1 !important;
                }
                
                body {
                    background-color: #ffffff !important;
                    margin: 15px !important;
                    font-size: 11pt !important;
                    color: #000000 !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                }
                
                th {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    font-weight: 700 !important;
                    font-size: 11pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    border: 2px solid #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                    text-align: center !important;
                    padding: 8px 12px !important;
                    vertical-align: middle !important;
                    page-break-inside: avoid !important;
                }
                
                td {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border: 1px solid #888888 !important;
                    padding: 6px 10px !important;
                    font-size: 10pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    text-align: center !important;
                }
                
                tr:nth-child(even) td {
                    background-color: #f5f5f5 !important;
                }
                
                .header-section, .header, .bg-primary, .bg-dark {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                }
                
                .header-section h1, .header-section h2, .header-section h3 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                h1, h2, h3, h4, h5 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                table {
                    border-collapse: collapse !important;
                    width: 100% !important;
                    page-break-inside: auto !important;
                }
                
                thead {
                    display: table-header-group !important;
                }
                
                tr {
                    page-break-inside: avoid !important;
                    page-break-after: auto !important;
                }
                
                .total-row td, .grand-total td {
                    font-weight: 700 !important;
                    border-top: 3px solid #000000 !important;
                }
                
                .footer, .footer p, .footer div {
                    color: #000000 !important;
                    border-top: 2px solid #000000 !important;
                    padding-top: 10px !important;
                    margin-top: 15px !important;
                }
            }
        </style>
        """
        
        if '</head>' in html:
            html = html.replace('</head>', print_styles + '</head>')
        else:
            html = html.replace('<body>', print_styles + '<body>')
        
        return html
 
    def print_facture(self):
        viewer = hr.DocumentViewer(self)
        viewer.show(self._get_html(), f"Facture {self.facture['numero']}")
 
    def export_pdf(self):
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(
            self._get_html(),
            default_name=f"Facture_{self.facture['numero']}.pdf",
        )

# ========== PAGE PRODUITS ==========

class ProduitPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "📦  Gestion des Produits", 16, True).pack(side="left")
        
        tk.Button(hdr, text="+ Nouveau Produit", command=self.new_item,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI",9,"bold"),
                padx=14, pady=7, cursor="hand2").pack(side="right")

        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        e = entry(sf, width=30, textvariable=self.search_var)
        e.pack(side="left", padx=8)

        cols = ["Code","Code Barre","Désignation","Marque","Unité","Facteur","Prix Achat","Prix Moyen","Variation","Prix Vente","TVA","Stock","Stock Min (cartons)"]
        widths = [80,140,180,100,60,60,90,90,80,90,60,80,120]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree.tag_configure("stock_ok", foreground=CLR_GREEN)
        self.tree.tag_configure("stock_low", foreground=CLR_RED)
        self.tree.tag_configure("var_pos", foreground=CLR_GREEN)
        self.tree.tag_configure("var_neg", foreground=CLR_RED)
        self.tree.tag_configure("var_zero", foreground=CLR_MUTED)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0,15))
        tk.Button(bf, text="✏ Modifier", command=self.edit_item,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🗑 Supprimer", command=self.del_item,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🔄 Rafraîchir", command=self.refresh,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)

        self.invent_filter_var = tk.StringVar(value="Tous")
        self.invent_sort_var = tk.StringVar(value="Désignation")

        tk.Label(bf, text="Filtrer unité:", bg=CLR_BG, fg=CLR_MUTED).pack(side="right", padx=(8,2))
        self.invent_filter_cb = combo(bf, ["Tous", "kg", "carton", "Pcs"], width=8, textvariable=self.invent_filter_var)
        self.invent_filter_cb.pack(side="right", padx=4)

        tk.Label(bf, text="Trier par:", bg=CLR_BG, fg=CLR_MUTED).pack(side="right", padx=(8,2))
        self.invent_sort_cb = combo(bf, ["Désignation", "Stock", "Prix Achat"], width=12, textvariable=self.invent_sort_var)
        self.invent_sort_cb.pack(side="right", padx=4)

        tk.Button(bf, text="📄 Export CSV", command=self.export_inventaire_csv,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bf, text="📄 Export PDF", command=self.export_inventaire_pdf,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bf, text="🖨 Imprimer Inventaire", command=self.print_inventaire,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="right", padx=8)
        tk.Button(bf, text="📁 Voir archivés", command=self.show_archived,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=4)

    def show_archived(self):
        archive_win = tk.Toplevel(self)
        archive_win.title("Produits Archivés")
        archive_win.configure(bg=CLR_BG)
        archive_win.geometry("900x500")
        archive_win.transient(self)
        archive_win.grab_set()
        center_window(archive_win, 900, 500)
        
        main_frame = tk.Frame(archive_win, bg=CLR_BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        lbl(main_frame, "📁 Produits Archivés", 14, True).pack(anchor="w", pady=(0, 10))
        
        cols = ["Code", "Désignation", "Stock", "Prix Vente"]
        widths = [100, 300, 100, 100]
        tf, tree = make_tree(main_frame, cols, widths)
        tf.pack(fill="both", expand=True, pady=10)
        
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, code, designation, stock_actuel, prix_vente FROM produits WHERE actif = 0 ORDER BY designation"
        ).fetchall()
        conn.close()
        
        for r in rows:
            tree.insert("", "end", iid=r["id"], values=(
                r["code"], r["designation"], f"{r['stock_actuel']:.2f}", f"{r['prix_vente']:.2f}"
            ))
        
        boutons_frame = tk.Frame(main_frame, bg=CLR_BG)
        boutons_frame.pack(fill="x", pady=10)
        
        def restaurer_produit():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Avertissement", "Sélectionnez un produit à restaurer")
                return
            produit_id = sel[0]
            
            if messagebox.askyesno("Confirmation", "Restaurer ce produit ?\nIl réapparaîtra dans la liste principale."):
                conn = get_conn()
                conn.execute("UPDATE produits SET actif = 1 WHERE id = ?", (produit_id,))
                conn.commit()
                conn.close()
                archive_win.destroy()
                self.refresh()
                messagebox.showinfo("Succès", "✅ Produit restauré avec succès")
        
        def supprimer_definitivement():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Avertissement", "Sélectionnez un produit à supprimer")
                return
            produit_id = sel[0]
            
            conn = get_conn()
            produit = conn.execute("SELECT designation FROM produits WHERE id=?", (produit_id,)).fetchone()
            conn.close()
            
            if messagebox.askyesno("Confirmation définitive", 
                                f"⚠️⚠️⚠️ ATTENTION ⚠️⚠️⚠️\n\n"
                                f"Supprimer définitivement '{produit['designation']}' ?\n\n"
                                "Cette action est IRRÉVERSIBLE et ne peut pas être annulée."):
                conn = get_conn()
                conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
                conn.commit()
                conn.close()
                for item in tree.get_children():
                    tree.delete(item)
                conn = get_conn()
                rows = conn.execute(
                    "SELECT id, code, designation, stock_actuel, prix_vente FROM produits WHERE actif = 0 ORDER BY designation"
                ).fetchall()
                conn.close()
                for r in rows:
                    tree.insert("", "end", iid=r["id"], values=(
                        r["code"], r["designation"], f"{r['stock_actuel']:.2f}", f"{r['prix_vente']:.2f}"
                    ))
                messagebox.showinfo("Succès", "Produit supprimé définitivement")
        
        tk.Button(boutons_frame, text="↩️ Restaurer", command=restaurer_produit,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(boutons_frame, text="⚠️ Supprimer définitivement", command=supprimer_definitivement,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(boutons_frame, text="❌ Fermer", command=archive_win.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=12, pady=6, cursor="hand2").pack(side="right")

    def refresh(self):
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif = 1 ORDER BY designation"
        ).fetchall()
        conn.close()

        for r in rows:
            barcode_val = r["barcode"] if r["barcode"] else ""
            if q in r["code"].lower() or q in r["designation"].lower() or q in barcode_val.lower():
                facteur = r["facteur_conversion"] or 1
                prix_achat = r["prix_achat"] or 0
                stock_min_cartons = (r["stock_min"] / facteur) if facteur else r["stock_min"]
                tag = "stock_ok" if r["stock_actuel"] > r["stock_min"] else "stock_low"
                prix_moyen = r["prix_moyen_pondere"] if r["prix_moyen_pondere"] else prix_achat
                if prix_achat > 0:
                    variation = ((prix_moyen - prix_achat) / prix_achat) * 100
                    variation_text = f"{variation:+.1f}%" if abs(variation) > 0.01 else "0%"
                else:
                    variation_text = "0%"
                
                # ✅ AJOUTER LA MARQUE
                fournisseur = r["fournisseur"] or ""
                
                self.tree.insert("", "end", iid=r["id"],
                    values=(
                        r["code"], barcode_val, r["designation"],
                        fournisseur,  # ✅ NOUVEAU
                        r["unite"], f"{facteur:.0f}", f"{prix_achat:.2f}",
                        f"{prix_moyen:.2f}", variation_text,
                        f"{r['prix_vente']:.2f}", f"{(r['tva'] or 0):.0f}%",
                        f"{r['stock_actuel']:.2f}",
                        f"{stock_min_cartons:.2f}",
                    ),
                    tags=(tag,)
                )

    def _form(self, data=None):
        d = ProduitDialog(self, data)
        self.wait_window(d)
        self.refresh()

    def print_inventaire(self):
        headers, data = self.build_inventaire_data()
        print_preview(data, "Inventaire - Désignation / Qté / Qté cartons/kg / Prix Achat", headers)

    def build_inventaire_data(self):
        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT code, barcode, designation, unite, facteur_conversion, prix_achat, prix_vente, stock_actuel, stock_min FROM produits"
            ).fetchall()
        finally:
            conn.close()
        filter_val = (self.invent_filter_var.get() or "Tous").strip().lower()
        sort_val = (self.invent_sort_var.get() or "Désignation").strip()
        headers = ["Désignation", "Quantité en stock", "Qté (cartons/kg)", "Prix Achat"]
        data = []
        for r in rows:
            designation = r["designation"]
            stock = float(r["stock_actuel"] or 0)
            prix_achat = float(r["prix_achat"] or 0)
            facteur = float(r["facteur_conversion"] or 1)
            unite = (r["unite"] or "").strip().lower()
            if filter_val != "tous":
                if filter_val == "kg":
                    if "kg" not in unite:
                        continue
                elif filter_val == "carton":
                    if "cart" not in unite and unite != "carton":
                        continue
                else:
                    if filter_val != unite:
                        continue
            if "kg" in unite:
                secondaire = f"{stock:.2f}"
            else:
                secondaire_qty = stock / facteur if facteur and facteur > 0 else stock
                secondaire = f"{secondaire_qty:.2f}"
            data.append([designation, f"{stock:.2f}", secondaire, f"{prix_achat:.2f}"])
        try:
            if sort_val == "Désignation":
                data.sort(key=lambda x: x[0].lower())
            elif sort_val == "Stock":
                data.sort(key=lambda x: float(x[1]) if x[1] else 0, reverse=True)
            elif sort_val == "Prix Achat":
                data.sort(key=lambda x: float(x[3]) if x[3] else 0, reverse=True)
        except Exception:
            pass
        return headers, data

    def export_inventaire_csv(self):
        headers, data = self.build_inventaire_data()
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="inventaire.csv"
        )
        if filename:
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Fichier CSV créé: {filename}")

    def export_inventaire_pdf(self):
        from gestion_stock import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif=1 ORDER BY designation"
        ).fetchall()
        conn.close()
        html = hr.build_inventaire_html(
            [dict(r) for r in rows], titre="Inventaire des produits"
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(html, "inventaire.pdf")
 
    def export_inventaire_html(self):
        from gestion_stock import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif=1 ORDER BY designation"
        ).fetchall()
        conn.close()
        html = hr.build_inventaire_html(
            [dict(r) for r in rows], titre="Inventaire des produits"
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_html(html, "inventaire.html")

    def new_item(self): 
        self._form()

    def edit_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        conn = get_conn()
        r = conn.execute("SELECT * FROM produits WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        self._form(dict(r))

    def del_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        conn = get_conn()
        produit_id = sel[0]
        produit = conn.execute("SELECT designation, stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not produit:
            conn.close()
            return
        nb_utilisations = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM lignes_achat WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_vente WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_retour_vente WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_retour_achat WHERE produit_id=?) as total
        """, (produit_id, produit_id, produit_id, produit_id)).fetchone()[0]
        if nb_utilisations > 0 or produit['stock_actuel'] > 0:
            msg = f"⚠️ Ce produit est utilisé dans {nb_utilisations} transaction(s)\n"
            if produit['stock_actuel'] > 0:
                msg += f"   Stock restant: {produit['stock_actuel']}\n"
            msg += f"\n📦 Produit: {produit['designation']}\n\n"
            msg += "Il sera ARCHIVÉ (plus visible dans la liste)\n"
            msg += "mais restera dans l'historique.\n\n"
            msg += "Confirmer l'archivage ?"
            if messagebox.askyesno("Archiver le produit", msg):
                conn.execute("UPDATE produits SET actif = 0 WHERE id=?", (produit_id,))
                conn.commit()
                messagebox.showinfo("Succès", f"✅ Produit archivé avec succès")
        else:
            if messagebox.askyesno("Confirmation", 
                                f"⚠️ Supprimer définitivement '{produit['designation']}' ?\n"
                                "Cette action est irréversible."):
                conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
                conn.commit()
                messagebox.showinfo("Succès", "✅ Produit supprimé définitivement")
        conn.close()
        self.refresh()


class ProduitDialog(tk.Toplevel):
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Produit")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.data = data
        self._build()
        self.update_idletasks()
        center_window(self, self.winfo_width(), self.winfo_height())

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=30, pady=20)
        f.pack()
        
        if not self.data:
            code_auto = generer_code_unique("PROD", "produits", mode="sequentiel")
        else:
            code_auto = self.data["code"]
        
        fields = [
            ("Code *", "code", True),
            ("Code Barre", "barcode", False),
            ("Désignation *", "designation", False),
            ("Unité", "unite", False),
            ("Facteur Conversion (ex: 24 carton)", "facteur_conversion", False),
            ("🏷️ Marque/Fournisseur *", "fournisseur", False),  # ✅ AJOUTÉ
            ("Prix Achat", "prix_achat", False),
            ("TVA (%)", "tva", False),
            ("Stock actuel", "stock_actuel", False),
            ("Stock minimum (cartons)", "stock_min", False),
        ]
        
        self.vars = {}
        for i, (lbl_text, key, readonly) in enumerate(fields):
            lbl(f, lbl_text, color=CLR_MUTED).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            
            if key == "code" and not self.data:
                v.set(code_auto)
            elif self.data and key in self.data:
                if key == "stock_min":
                    try:
                        facteur = float(self.data["facteur_conversion"] or 1) if self.data["facteur_conversion"] else 1.0
                        v.set(f"{float(self.data[key]) / facteur:.2f}")
                    except Exception:
                        v.set(str(self.data[key]))
                elif self.data[key] is not None:
                    v.set(str(self.data[key]))
            elif key == "facteur_conversion":
                v.set("1")
            elif key == "tva" and not self.data:
                v.set("19")
            elif key == "fournisseur" and not self.data:  # ✅ AJOUTÉ
                v.set("")  # Vide par défaut
            
            # ✅ Pour le champ unité, ajouter une combobox avec les unités courantes (g, kg, L, mL, Pièce, Carton, Paquet, etc.)
            if key == "unite":
                # Récupérer les unités existantes de la base de données
                conn = get_conn()
                unites_db = conn.execute(
                    "SELECT DISTINCT unite FROM produits WHERE unite != '' ORDER BY unite"
                ).fetchall()
                conn.close()
                
                unites_defaut = ["Pièce", "g", "kg", "L", "mL", "Pcs", "Carton", "Paquet", "Bouteille", "Sachet", "Boîte", "Mètre", "Cm"]
                unites_existantes = [u["unite"] for u in unites_db if u["unite"]]
                
                # Combiner sans doublons
                unites_liste = list(dict.fromkeys(unites_defaut + unites_existantes))
                
                cb_unite = combo(f, unites_liste, width=28, textvariable=v)
                cb_unite.grid(row=i, column=1, padx=(10, 0), pady=4)
                
                # Bouton pour ajouter une nouvelle unité personnalisée
                btn_new_unite = tk.Button(
                    f, text="➕", 
                    command=self.ajouter_nouvelle_unite,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                    cursor="hand2"
                )
                btn_new_unite.grid(row=i, column=2, padx=5, pady=4)

            elif key == "fournisseur":
                # Récupérer les marques existantes
                conn = get_conn()
                marques = conn.execute(
                    "SELECT DISTINCT fournisseur FROM produits WHERE fournisseur != '' ORDER BY fournisseur"
                ).fetchall()
                conn.close()
                
                marques_liste = [""] + [m["fournisseur"] for m in marques]
                
                # Utiliser une Combobox au lieu d'un Entry
                cb = combo(f, marques_liste, width=28, textvariable=v)
                cb.grid(row=i, column=1, padx=(10, 0), pady=4)
                
                # Ajouter un bouton pour créer une nouvelle marque
                btn_new_marque = tk.Button(
                    f, text="➕", 
                    command=self.ajouter_nouvelle_marque,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                    cursor="hand2"
                )
                btn_new_marque.grid(row=i, column=2, padx=5, pady=4)
                
            else:
                e = entry(f, width=28, textvariable=v)
                e.grid(row=i, column=1, padx=(10, 0), pady=4)
            
            if key == "code" and not self.data:
                e.config(state="readonly", readonlybackground=CLR_INPUT)
            
            if key == "barcode":
                def on_barcode_change(*args, var=v):
                    raw = var.get()
                    if not raw:
                        return
                    cleaned = re.sub(r"[^A-Za-z0-9\-_\.]", "", raw)
                    cleaned = cleaned.upper()
                    if cleaned != raw:
                        var.trace_remove("write", var.trace_info()[0][1])
                        var.set(cleaned)
                        var.trace_add("write", on_barcode_change)
                v.trace_add("write", on_barcode_change)
            
            self.vars[key] = v
        
        # Prix niveaux (comme avant)
        pnf = prix_niveaux.PrixNiveauxFrame(f, self.vars, self.data)
        pnf.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=8)

        if not self.data:
            tk.Button(f, text="🔄 Régénérer", command=self.regenerate_code,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=10, pady=2,
                    cursor="hand2").grid(row=0, column=2, padx=5, pady=4)
        
        bf = tk.Frame(f, bg=CLR_BG)
        bf.grid(row=len(fields)+1, column=0, columnspan=3, pady=15)
        tk.Button(bf, text="💾 Enregistrer", command=self.save,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                cursor="hand2").pack(side="left", padx=6)
        tk.Button(bf, text="Annuler", command=self.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=14, pady=7,
                cursor="hand2").pack(side="left", padx=6)

    def ajouter_nouvelle_unite(self):
        """Ajouter une nouvelle unité personnalisée"""
        nouvelle_unite = simpledialog.askstring(
            "Nouvelle Unité",
            "Entrez la nouvelle unité (ex: g, kg, L, mL, Pièce, etc.) :",
            parent=self
        )
        if nouvelle_unite and nouvelle_unite.strip():
            unite = nouvelle_unite.strip()
            self.vars["unite"].set(unite)
            messagebox.showinfo("Succès", f"✅ Unité '{unite}' ajoutée avec succès !")

    def ajouter_nouvelle_marque(self):
        """Ajouter une nouvelle marque/fournisseur"""
        nouvelle_marque = simpledialog.askstring(
            "Nouvelle Marque",
            "Entrez le nom de la nouvelle marque/fournisseur :",
            parent=self
        )
        if nouvelle_marque and nouvelle_marque.strip():
            marque = nouvelle_marque.strip().upper()
            # Mettre à jour la combobox
            self.vars["fournisseur"].set(marque)
            messagebox.showinfo("Succès", f"✅ Marque '{marque}' ajoutée avec succès !")
    
    def regenerate_code(self):
        nouveau_code = generer_code_unique("PROD", "produits", mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")

    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        
        # ✅ Validation : Le fournisseur est facultatif, mais vous pouvez le rendre obligatoire
        # if not v.get("fournisseur", ""):
        #     messagebox.showerror("Erreur", "La marque/fournisseur est obligatoire")
        #     return
        
        if not v["code"] or not v["designation"]:
            messagebox.showerror("Erreur", "Code et désignation obligatoires")
            return
        try:
            fc = parse_decimal(v["facteur_conversion"] or 1)
            pa = parse_decimal(v["prix_achat"] or 0)
            tva = parse_decimal(v.get("tva", "19") or "19")
            # Récupérer les 4 niveaux de prix
            prix_sg = parse_decimal(v.get("prix_super_gros", "0") or "0")
            prix_g = parse_decimal(v.get("prix_gros", "0") or "0")
            prix_d = parse_decimal(v.get("prix_detail", "0") or "0")
            prix_sp = parse_decimal(v.get("prix_special", "0") or "0")
            # prix_vente = prix détail par défaut
            pv = prix_d if prix_d > 0 else pa * 1.35
            sa = parse_decimal(v["stock_actuel"] or 0)
            sm_cartons = parse_decimal(v["stock_min"] or 0)
            sm = sm_cartons * fc
            
            # ✅ Récupérer le fournisseur
            fournisseur = v.get("fournisseur", "")
            
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides")
            return

        conn = get_conn()
        try:
            if self.data:
                barcode_val = v["barcode"] if v["barcode"] else None
                # ✅ UPDATE avec fournisseur
                conn.execute("""UPDATE produits SET 
                    code=?, barcode=?, designation=?, unite=?,
                    facteur_conversion=?, prix_achat=?, prix_vente=?, tva=?,
                    prix_super_gros=?, prix_gros=?, prix_detail=?, prix_special=?,
                    stock_actuel=?, stock_min=?, fournisseur=? 
                    WHERE id=?""",
                    (v["code"], barcode_val, v["designation"], v["unite"], 
                    fc, pa, pv, tva,
                    prix_sg, prix_g, prix_d, prix_sp, 
                    sa, sm, fournisseur, self.data["id"]))
            else:
                existing = conn.execute("SELECT id FROM produits WHERE code = ?", (v["code"],)).fetchone()
                if existing:
                    messagebox.showerror("Erreur", 
                        f"Le code '{v['code']}' existe déjà.\n"
                        "Cliquez sur 'Régénérer' pour obtenir un nouveau code.")
                    conn.close()
                    return
                barcode_val = v["barcode"] if v["barcode"] else None
                # ✅ INSERT avec fournisseur
                conn.execute("""INSERT INTO produits(
                    code, barcode, designation, unite,
                    facteur_conversion, prix_achat, prix_vente, tva,
                    prix_super_gros, prix_gros, prix_detail, prix_special,
                    stock_actuel, stock_min, fournisseur)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (v["code"], barcode_val, v["designation"], v["unite"], 
                    fc, pa, pv, tva,
                    prix_sg, prix_g, prix_d, prix_sp, 
                    sa, sm, fournisseur))
            conn.commit()
            messagebox.showinfo("Succès", "Produit enregistré avec succès !")
            self.notifier_toutes_les_fenetres()
            self.destroy()
        except sqlite3.IntegrityError as e:
            if "code" in str(e):
                messagebox.showerror("Erreur", f"Le code '{v['code']}' existe déjà.")
            elif "barcode" in str(e):
                messagebox.showerror("Erreur", f"Le code barre '{v['barcode']}' est déjà utilisé.")
            else:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
        except Exception as ex:
            messagebox.showerror("Erreur", f"Erreur: {str(ex)}")
        finally:
            conn.close()
    def notifier_toutes_les_fenetres(self):
        """Notifie toutes les fenêtres Toplevel ouvertes qu'un produit a changé"""
        # Méthode 1 : Utiliser un événement virtuel global
        # Envoyer un événement à la fenêtre principale
        root = self.winfo_toplevel()
        root.event_generate("<<ProduitsModifies>>", when="tail")
        
        # Méthode 2 : Parcourir toutes les fenêtres Toplevel
        for fenetre in root.winfo_children():
            if isinstance(fenetre, tk.Toplevel):
                # Essayer de trouver une méthode refresh_produits dans la fenêtre
                if hasattr(fenetre, 'refresh_produits'):
                    fenetre.refresh_produits()
                # Ou chercher dans les enfants de la fenêtre
                else:
                    self._chercher_refresh_dans_enfants(fenetre)
    
    def _chercher_refresh_dans_enfants(self, widget):
        """Recherche récursivement un widget avec refresh_produits"""
        if hasattr(widget, 'refresh_produits'):
            widget.refresh_produits()
            return True
        
        if hasattr(widget, 'winfo_children'):
            for enfant in widget.winfo_children():
                if self._chercher_refresh_dans_enfants(enfant):
                    return True
        return False        

# ========== PAGE TABLEAU DE BORD ==========

class DashboardPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()

    def _build(self):
        lbl(self,"🏠  Tableau de Bord",18,True).pack(padx=25,pady=(25,5),anchor="w")
        lbl(self,"Vue d'ensemble de votre activité",10,color=CLR_MUTED).pack(padx=25,anchor="w")
        self.cards_frame = tk.Frame(self,bg=CLR_BG)
        self.cards_frame.pack(fill="x",padx=20,pady=20)
        self.alert_frame = tk.Frame(self,bg=CLR_BG)
        self.alert_frame.pack(fill="both",expand=True,padx=20)
        self.refresh()

    def refresh(self):
        for w in self.cards_frame.winfo_children(): w.destroy()
        for w in self.alert_frame.winfo_children(): w.destroy()

        conn = get_conn()
        nb_prod = conn.execute("SELECT COUNT(*) FROM produits").fetchone()[0]
        nb_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        nb_fourn = conn.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0]
        nb_bv = conn.execute("SELECT COUNT(*) FROM bons_vente WHERE statut='Validé'").fetchone()[0]
        nb_ba = conn.execute("SELECT COUNT(*) FROM bons_achat WHERE statut='Validé'").fetchone()[0]
        nb_factures = conn.execute("SELECT COUNT(*) FROM factures").fetchone()[0]
        ca_vente = conn.execute("SELECT COALESCE(SUM(total),0) FROM bons_vente WHERE statut='Validé'").fetchone()[0]
        ca_achat = conn.execute("SELECT COALESCE(SUM(total),0) FROM bons_achat WHERE statut='Validé'").fetchone()[0]
        stock_alerte = conn.execute("SELECT COUNT(*) FROM produits WHERE stock_actuel<=stock_min").fetchone()[0]
        clients_solde = conn.execute("SELECT COUNT(*) FROM clients WHERE solde>0").fetchone()[0]
        conn.close()

        kpis = [
            ("📦 Produits",str(nb_prod),CLR_ACCENT),
            ("👥 Clients",str(nb_clients),CLR_GREEN),
            ("🏭 Fournisseurs",str(nb_fourn),CLR_ORANGE),
            ("🛒 Bons Achat",str(nb_ba),CLR_ACCENT),
            ("🏷️ Bons Vente",str(nb_bv),CLR_GREEN),
            ("🧾 Factures",str(nb_factures),CLR_ACCENT),
            ("💰 CA Ventes",f"{ca_vente:,.0f} DA",CLR_GREEN),
            ("📥 Total Achats",f"{ca_achat:,.0f} DA",CLR_ORANGE),
            ("⚠️ Alertes Stock",str(stock_alerte),CLR_RED),
        ]
        for i,(title,val,clr) in enumerate(kpis):
            card = tk.Frame(self.cards_frame,bg=CLR_CARD,padx=22,pady=16,relief="flat")
            card.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="ew")
            self.cards_frame.grid_columnconfigure(i%3, weight=1)
            lbl(card,title,9,color=CLR_MUTED).pack(anchor="w")
            lbl(card,val,18,True,color=clr).pack(anchor="w",pady=(4,0))

        lbl(self.alert_frame,"⚠️  Alertes & Notifications",12,True,CLR_ORANGE).pack(anchor="w",pady=(10,8))
        conn = get_conn()
        alerts = conn.execute("SELECT code,designation,unite,facteur_conversion,stock_actuel,stock_min FROM produits WHERE stock_actuel<=stock_min ORDER BY stock_actuel").fetchall()
        conn.close()
        if alerts:
            for a in alerts[:8]:
                af = tk.Frame(self.alert_frame,bg=CLR_CARD,padx=15,pady=8)
                af.pack(fill="x",pady=2)
                facteur = a['facteur_conversion'] or 1
                stock_cartons = a['stock_actuel'] / facteur if facteur else a['stock_actuel']
                min_cartons = a['stock_min'] / facteur if facteur else a['stock_min']
                unit_label = "cartons" if facteur != 1 else a['unite'] or "unités"
                lbl(af,f"📦 {a['designation']} ({a['code']})  —  Stock: {stock_cartons:.1f} {unit_label}  /  Min: {min_cartons:.1f} {unit_label}",
                    9,color=CLR_RED).pack(side="left")
        else:
            lbl(self.alert_frame,"✅  Aucune alerte — Tous les stocks sont suffisants",
                10,color=CLR_GREEN).pack(anchor="w")


# ========== PAGE CLIENTS / FOURNISSEURS ==========

class TiersPage(tk.Frame):
    def __init__(self, parent, tiers_type="client"):
        self.tiers_type = tiers_type
        self.table = "clients" if tiers_type == "client" else "fournisseurs"
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
        self.tiers_list = []


    def _build(self):
        title = "👥  Clients" if self.tiers_type == "client" else "🏭  Fournisseurs"
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, title, 16, True).pack(side="left")
        nom = "Client" if self.tiers_type == "client" else "Fournisseur"
        tk.Button(hdr, text=f"+ Nouveau {nom}", command=self.new_item,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="right")
        # Dans TiersPage._build(), après les autres boutons
        
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)

        # ✅ AJOUTER PLUS DE COLONNES
        cols = ["Code", "Nom", "Adresse", "Ville", "Téléphone", "Email", "NIF", "Solde"]
        widths = [80, 150, 150, 80, 100, 130, 100, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0,15))
        
        for txt, cmd, clr in [
            ("✏ Modifier", self.edit_item, CLR_ACCENT),
            ("💰 Prix spéciaux", self.gestion_prix_speciaux, CLR_ORANGE),
            ("🗑 Supprimer", self.del_item, CLR_RED),
            ("💸 Dette", self.gestion_dette, CLR_ORANGE),  
            ("🗑 Supprimer Solde Initial", self.supprimer_solde_initial, CLR_RED),  # ✅ NOUVEAU


        ]:
            tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)  
    def gestion_dette(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return

        conn = get_conn()
        tiers = conn.execute(
            f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)
        ).fetchone()
        conn.close()

        if not tiers:
            return

        if self.tiers_type == "client" and tiers["nom"].upper() == "COMPTOIR":
            messagebox.showwarning("Action impossible",
                "Le client 'COMPTOIR' est un compte technique.")
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Gestion des dettes — {tiers['nom']}")
        dlg.configure(bg=CLR_BG)
        dlg.geometry("600x750")  # PLUS GRAND
        dlg.minsize(550, 650)    # TAILLE MINIMUM
        dlg.resizable(True, True)
        dlg.grab_set()
        center_window(dlg, 600, 750)

        main = tk.Frame(dlg, bg=CLR_BG, padx=25, pady=20)
        main.pack(fill="both", expand=True)

        # En-tête
        lbl(main, "💸 GESTION DES DETTES", 14, True, CLR_ACCENT).pack(anchor="w")
        lbl(main, tiers["nom"], 11, True, CLR_TEXT).pack(anchor="w", pady=(2, 0))
        solde_color = CLR_RED if tiers["solde"] < 0 else CLR_ORANGE
        lbl(main, f"Solde actuel : {tiers['solde']:,.2f} DA",
            10, False, solde_color).pack(anchor="w", pady=(0, 15))

        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=(0, 15))

        # Choix du type
        lbl(main, "Type d'opération :", 9, True, CLR_MUTED).pack(anchor="w", pady=(0, 8))

        type_var = tk.StringVar(value="solde_initial")

        choix_frame = tk.Frame(main, bg=CLR_BG)
        choix_frame.pack(fill="x", pady=(0, 15))
        choix_frame.grid_columnconfigure(0, weight=1)
        choix_frame.grid_columnconfigure(1, weight=1)

        card_si = tk.Frame(choix_frame, bg=CLR_CARD, relief="flat",
                        padx=15, pady=12,
                        highlightthickness=2,
                        highlightbackground=CLR_ACCENT)
        card_si.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        card_remb = tk.Frame(choix_frame, bg=CLR_CARD, relief="flat",
                            padx=15, pady=12,
                            highlightthickness=1,
                            highlightbackground=CLR_BORDER)
        card_remb.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        if self.tiers_type == "fournisseur":
            remb_titre  = "🛒 Achat en nature / avoir"
            remb_desc   = "Marchandise ou service reçu\n(ex: frigos, équipements…)\n→ Augmente le solde fournisseur"
            remb_couleur = CLR_ORANGE
            # solde_initial : dette de départ → augmente aussi le solde
            si_desc = "Dette antérieure au démarrage\n→ Augmente le solde fournisseur"
        else:
            remb_titre  = "↩️ Remboursement client"
            remb_desc   = "Somme à rembourser au client\n→ Diminue son solde"
            remb_couleur = CLR_GREEN
            si_desc = "Dette antérieure au démarrage\n→ Augmente le solde client"

        lbl(card_si, "📋 Solde initial", 10, True, CLR_ACCENT).pack(anchor="w")
        lbl(card_si, si_desc, 8, False, CLR_MUTED).pack(anchor="w", pady=(3, 0))

        lbl(card_remb, remb_titre, 10, True, CLR_TEXT).pack(anchor="w")
        lbl(card_remb, remb_desc, 8, False, CLR_MUTED).pack(anchor="w", pady=(3, 0))

        def select_si(e=None):
            type_var.set("solde_initial")
            card_si.config(highlightthickness=2, highlightbackground=CLR_ACCENT)
            card_remb.config(highlightthickness=1, highlightbackground=CLR_BORDER)
            update_preview()

        def select_remb(e=None):
            type_var.set("remboursement")
            card_remb.config(highlightthickness=2, highlightbackground=remb_couleur)
            card_si.config(highlightthickness=1, highlightbackground=CLR_BORDER)
            update_preview()

        for w in [card_si] + list(card_si.winfo_children()):
            w.bind("<Button-1>", select_si)
        for w in [card_remb] + list(card_remb.winfo_children()):
            w.bind("<Button-1>", select_remb)

        # Montant
        lbl(main, "Montant (DA) :", 9, False, CLR_MUTED).pack(anchor="w", pady=(5, 3))
        montant_var = tk.StringVar()
        entry(main, width=30, textvariable=montant_var,
            font=("Segoe UI", 12, "bold")).pack(anchor="w")

        # Motif
        lbl(main, "Motif :", 9, False, CLR_MUTED).pack(anchor="w", pady=(10, 3))
        motif_var = tk.StringVar()
        entry(main, width=50, textvariable=motif_var).pack(anchor="w", fill="x")

        # Date
        lbl(main, "Date :", 9, False, CLR_MUTED).pack(anchor="w", pady=(10, 3))
        date_var = tk.StringVar(value="2025-12-31")
        entry(main, width=18, textvariable=date_var).pack(anchor="w")

        # Aperçu solde
        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=15)

        preview = tk.Frame(main, bg=CLR_CARD, padx=15, pady=12)
        preview.pack(fill="x")

        r1 = tk.Frame(preview, bg=CLR_CARD)
        r1.pack(fill="x", pady=2)
        lbl(r1, "Solde avant :", 9, False, CLR_MUTED).pack(side="left")
        lbl(r1, f"{tiers['solde']:,.2f} DA", 9, False, CLR_TEXT).pack(side="right")

        r2 = tk.Frame(preview, bg=CLR_CARD)
        r2.pack(fill="x", pady=2)
        lbl(r2, "Opération :", 9, False, CLR_MUTED).pack(side="left")
        op_var = tk.StringVar(value="+ 0,00 DA")
        tk.Label(r2, textvariable=op_var, bg=CLR_CARD,
                fg=CLR_ACCENT, font=("Segoe UI", 9, "bold")).pack(side="right")

        tk.Frame(preview, bg=CLR_BORDER, height=1).pack(fill="x", pady=6)

        r3 = tk.Frame(preview, bg=CLR_CARD)
        r3.pack(fill="x", pady=2)
        lbl(r3, "Nouveau solde :", 10, True, CLR_MUTED).pack(side="left")
        nv_var = tk.StringVar(value=f"{tiers['solde']:,.2f} DA")
        tk.Label(r3, textvariable=nv_var, bg=CLR_CARD,
                fg=CLR_GREEN, font=("Segoe UI", 11, "bold")).pack(side="right")

        def update_preview(*args):
            try:
                montant = parse_decimal(montant_var.get() or "0")
            except ValueError:
                montant = 0
            solde = tiers["solde"]
            type_op = type_var.get()

            if type_op == "solde_initial":
                # Solde initial → toujours augmente (client ou fournisseur)
                nouveau = solde + montant
                op_var.set(f"+ {montant:,.2f} DA")
            else:
                if self.tiers_type == "fournisseur":
                    # Achat en nature → augmente le solde fournisseur
                    nouveau = solde + montant
                    op_var.set(f"+ {montant:,.2f} DA")
                else:
                    # Remboursement client → diminue son solde
                    nouveau = solde - montant
                    op_var.set(f"- {montant:,.2f} DA")

            nv_var.set(f"{nouveau:,.2f} DA")

        montant_var.trace_add("write", update_preview)

        # Boutons
        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=15)
        btn_frame = tk.Frame(main, bg=CLR_BG)
        btn_frame.pack(fill="x")

        def enregistrer():
            try:
                montant = parse_decimal(montant_var.get() or "0")
                if montant <= 0:
                    messagebox.showerror("Erreur", "Montant invalide", parent=dlg)
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Montant invalide", parent=dlg)
                return

            motif = motif_var.get().strip()
            if not motif:
                messagebox.showerror("Erreur", "Le motif est obligatoire", parent=dlg)
                return

            date_val = date_var.get().strip()
            if not valider_date(date_val):
                messagebox.showerror("Erreur",
                    "Date invalide (format YYYY-MM-DD)", parent=dlg)
                return

            type_op = type_var.get()

            if type_op == "solde_initial":
                # ── Vérifier doublon solde initial ──────────────────────────
                conn2 = get_conn()
                if self.tiers_type == "client":
                    existing = conn2.execute(
                        "SELECT id, numero, total FROM bons_vente "
                        "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                        (tiers["id"],)
                    ).fetchone()
                else:
                    existing = conn2.execute(
                        "SELECT id, numero, total FROM bons_achat "
                        "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                        (tiers["id"],)
                    ).fetchone()
                conn2.close()

                if existing:
                    messagebox.showwarning(
                        "Solde initial déjà existant",
                        f"Un solde initial existe déjà :\n"
                        f"📄 {existing['numero']} : {existing['total']:,.2f} DA\n\n"
                        "Supprimez-le d'abord via 'Supprimer Solde Initial'.",
                        parent=dlg
                    )
                    return

                ok = self.ajouter_solde_initial(
                    tiers["id"], montant, motif, date_val
                )
                if ok:
                    messagebox.showinfo("Succès",
                        f"✅ Solde initial enregistré !\n\n"
                        f"Montant : {montant:,.2f} DA\n"
                        f"Motif   : {motif}\n"
                        f"Date    : {date_val}", parent=dlg)
                    dlg.destroy()
                    self.refresh()

            else:
                # ── Achat en nature (fournisseur) ou remboursement (client) ─
                if self.tiers_type == "fournisseur":
                    # Enregistrer comme bon d'achat spécial
                    ok = self._enregistrer_achat_nature(
                        tiers["id"], montant, motif, date_val
                    )
                else:
                    # Remboursement client → diminue le solde
                    ok = self._enregistrer_remboursement_client(
                        tiers["id"], montant, motif, date_val
                    )
                if ok:
                    type_label = ("Achat en nature" if self.tiers_type == "fournisseur"
                                else "Remboursement client")
                    messagebox.showinfo("Succès",
                        f"✅ {type_label} enregistré !\n\n"
                        f"Montant : {montant:,.2f} DA\n"
                        f"Motif   : {motif}\n"
                        f"Date    : {date_val}", parent=dlg)
                    dlg.destroy()
                    self.refresh()

        tk.Button(btn_frame, text="✅ Enregistrer", command=enregistrer,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=(0, 10), expand=True, fill="x")

        tk.Button(btn_frame, text="❌ Annuler", command=dlg.destroy,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", expand=True, fill="x")

    def _generer_numero_avoir(self, conn, type_avoir):
        """
        Génère un numéro séquentiel pour les AVOIR par type
        type_avoir: "client" ou "fournisseur"
        Retourne: "AVOIR-C-001" ou "AVOIR-F-001"
        """
        if type_avoir == "client":
            table = "bons_vente"
            prefix = "AVOIR-C"
        else:
            table = "bons_achat"
            prefix = "AVOIR-F"
        
        # Compter le nombre d'AVOIR existants pour ce type
        count = conn.execute(f"""
            SELECT COUNT(*) FROM {table} 
            WHERE numero LIKE '{prefix}-%'
        """).fetchone()[0]
        
        # Générer le prochain numéro
        next_num = count + 1
        return f"{prefix}-{next_num:03d}"  # Format AVOIR-C-001 ou AVOIR-F-001
    def _enregistrer_achat_nature(self, fournisseur_id, montant, motif, date_bon):
        """
        Enregistre un achat en nature (ex: frigos fournis par le fournisseur).
        Augmente le solde fournisseur.
        Préfixe : AVOIR-YYYY-TIMESTAMP
        """
        conn = get_conn()
        try:
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            if not produit:
                conn.execute("""
                    INSERT INTO produits(code, designation, unite,
                        prix_achat, prix_vente, stock_actuel, stock_min, actif, tva)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, ("SOLDE_INITIAL", "Opération comptable", "Pcs",
                    0, 0, 0, 0, 0, 0))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code='SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]

            today = datetime.now()
            current_year = today.strftime("%Y")
            timestamp = today.strftime("%Y%m%d%H%M%S%f")
            num = self._generer_numero_avoir(conn, "fournisseur")

            fournisseur = conn.execute(
                "SELECT solde FROM fournisseurs WHERE id=?", (fournisseur_id,)
            ).fetchone()
            ancien_solde = fournisseur["solde"] if fournisseur else 0
            nouveau_solde = ancien_solde + montant

            conn.execute("""
                INSERT INTO bons_achat(
                    numero, date_bon, fournisseur_id, total, statut,
                    date_creation, observations, ancien_solde, nouveau_solde)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (num, date_bon, fournisseur_id, montant, "Validé",
                today.strftime("%Y-%m-%d %H:%M:%S"),
                motif, ancien_solde, nouveau_solde))

            bon_id = conn.execute(
                "SELECT id FROM bons_achat WHERE numero=?", (num,)
            ).fetchone()["id"]

            conn.execute("""
                INSERT INTO lignes_achat(
                    bon_id, produit_id, quantite, prix_unitaire,
                    total, total_ht, tva_taux, total_ttc)
                VALUES(?,?,?,?,?,?,?,?)
            """, (bon_id, produit_id, 1, montant, montant,
                montant, 0, montant))

            conn.execute(
                "UPDATE fournisseurs SET solde = solde + ? WHERE id=?",
                (montant, fournisseur_id)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()


    def _enregistrer_remboursement_client(self, client_id, montant, motif, date_bon):
        """
        Enregistre un remboursement au client.
        Diminue le solde client.
        Préfixe : REMB-C-YYYY-TIMESTAMP
        """
        conn = get_conn()
        try:
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            if not produit:
                conn.execute("""
                    INSERT INTO produits(code, designation, unite,
                        prix_achat, prix_vente, stock_actuel, stock_min, actif, tva)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, ("SOLDE_INITIAL", "Opération comptable", "Pcs",
                    0, 0, 0, 0, 0, 0))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code='SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]

            today = datetime.now()
            current_year = today.strftime("%Y")
            timestamp = today.strftime("%Y%m%d%H%M%S%f")
            num = self._generer_numero_avoir(conn, "client")

            conn.execute("""
                INSERT INTO bons_vente(
                    numero, date_bon, client_id, total, statut, observations)
                VALUES(?,?,?,?,?,?)
            """, (num, date_bon, client_id, montant, "Validé", motif))

            bon_id = conn.execute(
                "SELECT id FROM bons_vente WHERE numero=?", (num,)
            ).fetchone()["id"]

            conn.execute("""
                INSERT INTO lignes_vente(
                    bon_id, produit_id, quantite, prix_unitaire, total)
                VALUES(?,?,?,?,?)
            """, (bon_id, produit_id, 1, montant, montant))

            conn.execute(
                "UPDATE clients SET solde = solde - ? WHERE id=?",
                (montant, client_id)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()          
    def supprimer_solde_initial(self):
        """Supprimer le solde initial d'un client/fournisseur"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return
        
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        if not tiers:
            return
        
        # Chercher le(s) solde(s) initial(aux)
        conn = get_conn()
        if self.tiers_type == "client":
            soldes = conn.execute(
                "SELECT id, numero, total FROM bons_vente "
                "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchall()
        else:
            soldes = conn.execute(
                "SELECT id, numero, total FROM bons_achat "
                "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchall()
        conn.close()
        
        if not soldes:
            messagebox.showinfo("Information", f"Aucun solde initial trouvé pour {tiers['nom']}")
            return
        
        # Afficher les soldes existants
        msg = f"🗑 Supprimer le(s) solde(s) initial(aux) de {tiers['nom']} ?\n\n"
        total_si = 0
        for si in soldes:
            msg += f"   📄 {si['numero']} : {si['total']:,.2f} DA\n"
            total_si += si['total']
        msg += f"\n💰 Total à supprimer : {total_si:,.2f} DA"
        msg += f"\n📊 Solde actuel : {tiers['solde']:,.2f} DA"
        msg += f"\n📊 Nouveau solde : {tiers['solde'] - total_si:,.2f} DA\n\n"
        msg += "⚠️ Cette action est irréversible !"
        
        if not messagebox.askyesno("⚠️ Confirmation", msg):
            return
        
        # Supprimer les soldes initiaux
        conn = get_conn()
        try:
            for si in soldes:
                if self.tiers_type == "client":
                    # Supprimer le bon de vente
                    conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (si["id"],))
                    conn.execute("DELETE FROM bons_vente WHERE id=?", (si["id"],))
                else:
                    # Supprimer le bon d'achat
                    conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (si["id"],))
                    conn.execute("DELETE FROM bons_achat WHERE id=?", (si["id"],))
            
            # Mettre à jour le solde
            conn.execute(
                f"UPDATE {self.table} SET solde = solde - ? WHERE id=?",
                (total_si, tiers["id"])
            )
            conn.commit()
            messagebox.showinfo("Succès", f"✅ Solde initial supprimé avec succès !")
            self.refresh()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
        finally:
            conn.close()        
    def gestion_solde_initial(self):
        """Dialogue pour ajouter un solde initial (dette antérieure)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return
        
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        if not tiers:
            return
        
        # ❌ EXCLURE LE CLIENT COMPTOIR
        if self.tiers_type == "client" and tiers["nom"].upper() == "COMPTOIR":
            messagebox.showwarning(
                "⚠️ Action impossible",
                "Le client 'COMPTOIR' est un compte technique.\n"
                "Les soldes initiaux ne peuvent pas être ajoutés pour ce client."
            )
            return
        
        # ✅ VÉRIFIER SI UN SOLDE INITIAL EXISTE DÉJÀ
        conn = get_conn()
        if self.tiers_type == "client":
            existing = conn.execute(
                "SELECT id, numero, total, date_bon FROM bons_vente "
                "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id, numero, total, date_bon FROM bons_achat "
                "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchone()
        conn.close()
        
        # ❌ BLOQUER SI UN SOLDE INITIAL EXISTE DÉJÀ
        if existing:
            messagebox.showwarning(
                "⚠️ Solde initial déjà existant",
                f"Un solde initial existe déjà pour {tiers['nom']} :\n\n"
                f"📄 {existing['numero']} : {existing['total']:,.2f} DA\n"
                f"📅 Date : {existing['date_bon']}\n\n"
                f"Solde actuel : {tiers['solde']:,.2f} DA\n\n"
                f"❌ Impossible d'ajouter un deuxième solde initial.\n"
                f"💡 Si vous devez corriger le montant, supprimez d'abord le solde initial existant."
            )
            return  # ✅ Le return est ici, après tout est bon
        
        # ✅ DEMANDER LE MONTANT (après le return)
        montant = simpledialog.askfloat(
            "💰 Solde Initial",
            f"Entrez le montant du solde initial pour {tiers['nom']} :\n\n"
            f"Solde actuel : {tiers['solde']:,.2f} DA\n\n"
            f"💡 Montant du solde initial :",
            parent=self,
            minvalue=0,
            initialvalue=0
        )
        
        if montant is None or montant <= 0:
            return
        
        # ✅ DEMANDER LE MOTIF
        motif = simpledialog.askstring(
            "Motif",
            "Motif du solde initial :",
            initialvalue="Solde initial",
            parent=self
        )
        
        if motif is None:
            return
        
        # ✅ DEMANDER LA DATE
        date_si = simpledialog.askstring(
            "Date du solde initial",
            "Date du solde initial (YYYY-MM-DD) :\n"
            "💡 Laisser vide pour utiliser 2025-12-31",
            initialvalue="2025-12-31",
            parent=self
        )
        
        # ✅ VALIDER LA DATE
        if date_si and valider_date(date_si):
            date_bon = date_si
        else:
            date_bon = "2025-12-31"
            if date_si:  # Si une date a été saisie mais invalide
                messagebox.showwarning(
                    "Date invalide",
                    f"La date '{date_si}' n'est pas valide.\n"
                    "Utilisation de la date par défaut : 2025-12-31"
                )
        
        # ✅ CRÉER LE BON SPÉCIAL AVEC LA DATE
        if self.ajouter_solde_initial(tiers["id"], montant, motif, date_bon):
            messagebox.showinfo("Succès", 
                f"✅ Solde initial ajouté avec succès !\n\n"
                f"{'Client' if self.tiers_type == 'client' else 'Fournisseur'} : {tiers['nom']}\n"
                f"Montant : {montant:,.2f} DA\n"
                f"Date : {date_bon}\n"
                f"Motif : {motif}"
            )
            self.refresh()
    def ajouter_solde_initial(self, tiers_id, montant, motif="Solde initial", date_bon=None):
        """
        Ajoute un solde initial pour un client OU un fournisseur.
        Retourne True si succès, False sinon.
        """
        conn = get_conn()
        try:
            # 1. Créer le produit "SOLDE_INITIAL" s'il n'existe pas
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            
            if not produit:
                conn.execute("""
                    INSERT INTO produits(
                        code, designation, unite, prix_achat, prix_vente, 
                        stock_actuel, stock_min, actif, tva
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "SOLDE_INITIAL",
                    f"Solde initial {self.tiers_type}",
                    "Pcs", 0, 0, 0, 0, 0, 0
                ))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]
            
            # 2. Générer un numéro unique avec l'année en cours
            today = datetime.now()
            current_year = today.strftime("%Y")
            prefix = "SI-C" if self.tiers_type == "client" else "SI-F"
            
            # ✅ CORRECTION : Table correcte
            table_bons = "bons_vente" if self.tiers_type == "client" else "bons_achat"
            
            # ✅ CORRECTION : Compter les soldes initiaux existants
            # Construire le pattern complet
            pattern = f"{prefix}-{current_year}-%"
            
            # ✅ CORRECTION : Utiliser une requête simple SANS f-string pour le LIKE
            query = f"SELECT COUNT(*) FROM {table_bons} WHERE numero LIKE ? AND statut='Validé'"
            count = conn.execute(query, (pattern,)).fetchone()[0]
            
            num = f"{prefix}-{current_year}-{count + 1:03d}"
            
            # ✅ Utiliser la date passée ou la date par défaut
            if date_bon is None:
                date_bon = "2025-12-31"
            
            # 3. Récupérer le solde actuel
            tiers = conn.execute(
                f"SELECT solde FROM {self.table} WHERE id=?", (tiers_id,)
            ).fetchone()
            ancien_solde = tiers["solde"] if tiers else 0
            nouveau_solde = ancien_solde + montant
            
            # 4. Créer le bon selon le type
            if self.tiers_type == "client":
                # ✅ CLIENTS → bon de vente
                conn.execute("""
                    INSERT INTO bons_vente(
                        numero, date_bon, client_id, total, statut, observations
                    ) VALUES(?, ?, ?, ?, ?, ?)
                """, (num, date_bon, tiers_id, montant, "Validé", motif))
                
                bon_id = conn.execute(
                    "SELECT id FROM bons_vente WHERE numero=?", (num,)
                ).fetchone()["id"]
                
                conn.execute("""
                    INSERT INTO lignes_vente(
                        bon_id, produit_id, quantite, prix_unitaire, total
                    ) VALUES(?, ?, ?, ?, ?)
                """, (bon_id, produit_id, 1, montant, montant))
                
            else:
                # ✅ FOURNISSEURS → bon d'achat
                conn.execute("""
                    INSERT INTO bons_achat(
                        numero, date_bon, fournisseur_id, total, statut,
                        date_creation, observations,
                        ancien_solde, nouveau_solde
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    num, date_bon, tiers_id, montant, "Validé",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    motif, ancien_solde, nouveau_solde
                ))
                
                bon_id = conn.execute(
                    "SELECT id FROM bons_achat WHERE numero=?", (num,)
                ).fetchone()["id"]
                
                conn.execute("""
                    INSERT INTO lignes_achat(
                        bon_id, produit_id, quantite, prix_unitaire, total,
                        total_ht, tva_taux, total_ttc
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bon_id, produit_id, 1, montant, montant,
                    montant, 0, montant
                ))
            
            # 5. Mettre à jour le solde
            conn.execute(
                f"UPDATE {self.table} SET solde = ? WHERE id=?",
                (nouveau_solde, tiers_id)
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()
            
    def gestion_prix_speciaux(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un client")
            return
        
        conn = get_conn()
        client = conn.execute(f"SELECT id, nom FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        d = PrixSpeciauxClientDialog(self, client["id"], client["nom"])
        self.wait_window(d)
    def refresh(self):
        """Rafraîchit la liste et met à jour la liste des noms"""
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        rows = conn.execute(f"SELECT * FROM {self.table} ORDER BY nom").fetchall()
        
        # ✅ METTRE À JOUR LA LISTE DES TIERS
        self.tiers_list = []
        
        for r in rows:
            if q in r["code"].lower() or q in r["nom"].lower():
                tiers_id = r["id"]
                
                # ✅ Calculer le solde réel
                if self.tiers_type == "client":
                    # Récupérer les soldes initiaux
                    si = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_vente 
                        WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les ventes
                    ventes = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_vente 
                        WHERE client_id=? AND statut='Validé' AND numero NOT LIKE 'SI-C-%'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les retours
                    retours = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM retours_vente 
                        WHERE client_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les versements
                    versements = conn.execute("""
                        SELECT COALESCE(SUM(montant),0) FROM versements_clients 
                        WHERE client_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Calculer le solde réel
                    solde_reel = si + ventes - retours - versements
                    
                else:  # fournisseur
                    # Récupérer les soldes initiaux
                    si = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_achat 
                        WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les achats
                    achats = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_achat 
                        WHERE fournisseur_id=? AND statut='Validé' AND numero NOT LIKE 'SI-F-%'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les retours
                    retours = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM retours_achat 
                        WHERE fournisseur_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les versements
                    versements = conn.execute("""
                        SELECT COALESCE(SUM(montant),0) FROM versements_fournisseurs 
                        WHERE fournisseur_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Calculer le solde réel
                    solde_reel = si + achats - retours - versements
                
                # ✅ Afficher le solde réel
                clr = CLR_RED if solde_reel < 0 else CLR_TEXT
                
                # ✅ Ajouter une indication si le solde enregistré est différent
                solde_enregistre = r["solde"]
               
                solde_affichage = f"{solde_reel:.2f}"
                
                self.tree.insert("", "end", iid=r["id"],
                    values=(
                        r["code"], 
                        r["nom"], 
                        r["adresse"] or "",
                        r["ville"] or "",
                        r["tel"] or "",
                        r["email"] or "",
                        r["nif"] or "",
                        solde_affichage  # ✅ Solde réel calculé
                    ),
                    tags=("neg",) if solde_reel < 0 else ())
                
                self.tiers_list.append(r["nom"])  # ✅ AJOUTER À LA LISTE
        
        self.tree.tag_configure("neg", foreground=CLR_RED)
        conn.close()
        
        # ✅ METTRE À JOUR LES COMBOBOX DANS LES AUTRES PAGES
        self.update_comboboxes()
    def update_comboboxes(self):
        """Met à jour les combobox des autres pages"""
        # Si nous sommes dans la page des clients, mettre à jour les combos de ventes
        if self.tiers_type == "client":
            if hasattr(self.master, '_pages') and 'bons_vente' in self.master._pages:
                bon_vente_page = self.master._pages['bons_vente']
                if hasattr(bon_vente_page, 'load_clients_list'):
                    bon_vente_page.load_clients_list()
        # Si nous sommes dans la page des fournisseurs, mettre à jour les combos d'achats
        elif self.tiers_type == "fournisseur":
            if hasattr(self.master, '_pages') and 'bons_achat' in self.master._pages:
                bon_achat_page = self.master._pages['bons_achat']
                if hasattr(bon_achat_page, 'load_fournisseurs_list'):
                    bon_achat_page.load_fournisseurs_list()
    def _form(self, data=None):
        d = TiersDialog(self, self.tiers_type, data)
        self.wait_window(d)
        self.refresh()

    def new_item(self): 
        self._form()
        
    def edit_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un élément")
            return
        conn = get_conn()
        r = conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        self._form(dict(r))

    def del_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un élément")
            return
        if messagebox.askyesno("Confirmation","Supprimer ?"):
            try:
                conn = get_conn()
                conn.execute(f"DELETE FROM {self.table} WHERE id=?", (sel[0],))
                conn.commit()
                conn.close()
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

class TiersDialog(tk.Toplevel):
    def __init__(self, parent, tiers_type, data=None):
        super().__init__(parent)
        self.tiers_type = tiers_type
        self.parent = parent
        self.title("Client" if tiers_type == "client" else "Fournisseur")
        self.configure(bg=CLR_BG)
        self.resizable(True, True)  # ✅ Permettre le redimensionnement
        self.table = "clients" if tiers_type == "client" else "fournisseurs"
        self.data = data
        self._build()
        self.update_idletasks()
        # ✅ Agrandir la fenêtre
        self.geometry("700x650")
        center_window(self, 700, 650)

    def _build(self):
        # ✅ Frame principal avec padding
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # ✅ Titre
        titre = "CLIENT" if self.tiers_type == "client" else "FOURNISSEUR"
        lbl(main_frame, f"📋 INFORMATIONS {titre}", 14, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # ✅ Canvas + Scrollbar pour le formulaire
        canvas_frame = tk.Frame(main_frame, bg=CLR_BG)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=650)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ✅ Formulaire dans le frame scrollable
        f = tk.Frame(scrollable_frame, bg=CLR_BG, padx=10, pady=10)
        f.pack(fill="both", expand=True)
        
        # Génération du code
        if not self.data:
            prefix = "CLT" if self.tiers_type == "client" else "FRN"
            code_auto = generer_code_unique(prefix, self.table, mode="sequentiel")
        else:
            code_auto = self.data["code"]
        
        # ✅ Dictionnaire pour stocker les variables
        self.vars = {}
        row_idx = 0
        
        # ✅ SECTION 1: INFORMATIONS DE BASE
        lbl(f, "🏷️ INFORMATIONS DE BASE", 11, True, CLR_ACCENT).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(10, 5)
        )
        row_idx += 1
        
        # Séparateur
        sep = tk.Frame(f, bg=CLR_BORDER, height=2)
        sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=5)
        row_idx += 1
        
        fields_base = [
            ("Code *", "code", True),
            ("Nom *", "nom", False),
            ("Adresse", "adresse", False),
            ("Ville", "ville", False),
            ("Téléphone", "tel", False),
            ("Email", "email", False),
        ]
        
        for lbl_text, key, readonly in fields_base:
            lbl(f, lbl_text, color=CLR_MUTED, size=9).grid(
                row=row_idx, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            v = tk.StringVar()
            if key == "code" and not self.data:
                v.set(code_auto)
            elif self.data and self.data.get(key):
                v.set(str(self.data[key]))
            
            # ✅ Plus large pour les champs de base
            e = entry(f, width=40, textvariable=v)
            e.grid(row=row_idx, column=1, padx=(0, 10), pady=5, sticky="w")
            
            if key == "code" and not self.data:
                e.config(state="readonly", readonlybackground=CLR_INPUT)
                # Bouton régénérer
                btn_regenerate = tk.Button(
                    f, text="🔄", command=self.regenerate_code,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=8, pady=2, cursor="hand2"
                )
                btn_regenerate.grid(row=row_idx, column=2, padx=5, pady=5)
            
            self.vars[key] = v
            row_idx += 1
        
        # ✅ SECTION 2: INFORMATIONS COMMERCIALES
        lbl(f, "🏢 INFORMATIONS COMMERCIALES", 11, True, CLR_ACCENT).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(15, 5)
        )
        row_idx += 1
        
        # Séparateur
        sep = tk.Frame(f, bg=CLR_BORDER, height=2)
        sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=5)
        row_idx += 1
        
        fields_commercial = [
            ("NIF (N° Identification Fiscale)", "nif", False),
            ("NIS (N° Identification Statistique)", "nis", False),
            ("NRC (N° Registre de Commerce)", "nrc", False),
            ("Article d'imposition", "art_imp", False),
            ("Registre de commerce", "registre_commerce", False),
            ("Capital social", "capitale_social", False),
        ]
        
        for lbl_text, key, readonly in fields_commercial:
            lbl(f, lbl_text, color=CLR_MUTED, size=9).grid(
                row=row_idx, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            v = tk.StringVar()
            if self.data and self.data.get(key):
                v.set(str(self.data[key]))
            e = entry(f, width=40, textvariable=v)
            e.grid(row=row_idx, column=1, padx=(0, 10), pady=5, sticky="w")
            self.vars[key] = v
            row_idx += 1
        
        # ✅ BOUTONS EN BAS
        btn_frame = tk.Frame(f, bg=CLR_BG)
        btn_frame.grid(row=row_idx, column=0, columnspan=3, pady=25)
        
        tk.Button(
            btn_frame, text="💾 Enregistrer", command=self.save,
            bg=CLR_GREEN, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=25, pady=8, cursor="hand2"
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame, text="❌ Annuler", command=self.destroy,
            bg=CLR_RED, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=25, pady=8, cursor="hand2"
        ).pack(side="left", padx=10)
    
    def regenerate_code(self):
        prefix = "CLT" if self.tiers_type == "client" else "FRN"
        nouveau_code = generer_code_unique(prefix, self.table, mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")

    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        if not v["code"] or not v["nom"]:
            messagebox.showerror("Erreur", "Code et nom obligatoires")
            return
        
        conn = get_conn()
        try:
            if self.data:
                conn.execute(f"""
                    UPDATE {self.table} 
                    SET code=?, nom=?, adresse=?, ville=?, tel=?, email=?,
                        nif=?, nis=?, nrc=?, art_imp=?, registre_commerce=?, capitale_social=?
                    WHERE id=?
                """, (
                    v["code"], v["nom"], v["adresse"], v["ville"], v["tel"], v["email"],
                    v["nif"], v["nis"], v["nrc"], v["art_imp"], v["registre_commerce"], v["capitale_social"],
                    self.data["id"]
                ))
            else:
                conn.execute(f"""
                    INSERT INTO {self.table}(code, nom, adresse, ville, tel, email,
                        nif, nis, nrc, art_imp, registre_commerce, capitale_social)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    v["code"], v["nom"], v["adresse"], v["ville"], v["tel"], v["email"],
                    v["nif"], v["nis"], v["nrc"], v["art_imp"], v["registre_commerce"], v["capitale_social"]
                ))
            
            conn.commit()
            conn.close()
            if hasattr(self.parent, 'refresh'):
                self.parent.refresh()
            messagebox.showinfo("Succès", f"{'Client' if self.tiers_type == 'client' else 'Fournisseur'} enregistré avec succès !")
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Code déjà existant")
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))


# ========== PAGE BONS D'ACHAT ==========

class BonAchatPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        logging.info("🚀 BonAchatPage.__init__() appelé")
        
        # ✅ Initialiser TOUTES les variables AVANT _build()
        self.fournisseur_filter_var = tk.StringVar(value="Tous")
        self.fournisseur_filter_combo = None
        self.sv = tk.StringVar()
        self.tree = None
        self.total_ht_global = tk.StringVar(value="0.00 DA")
        self.total_ttc_global = tk.StringVar(value="0.00 DA")
        self.situation_ttc_global = tk.StringVar(value="0.00 DA")
        
        try:
            self._build()
            logging.info("✅ _build() terminé")
            self.refresh()
            logging.info("✅ refresh() terminé")
        except Exception as e:
            logging.error(f"❌ ERREUR INIT: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self._afficher_erreur(e)

    def _build(self):
        logging.info("🏗️ _build() - Construction de la page...")
        
        try:
            hdr = tk.Frame(self, bg=CLR_BG)
            hdr.pack(fill="x", padx=20, pady=(20,10))
            lbl(hdr, "🛒  Bons d'Achat", 16, True).pack(side="left")
            logging.info("✅ En-tête créé")
            
            btn_frame = tk.Frame(hdr, bg=CLR_BG)
            btn_frame.pack(side="right")
            
            tk.Button(btn_frame, text="+ Nouveau Bon", command=self.new_bon,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
            
            tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bons,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
            
            tk.Button(btn_frame, text="📊 Exporter", command=self.export_bons,
                    bg=CLR_ORANGE, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
            logging.info("✅ Boutons créés")

            # 🔹 BARRE DE RECHERCHE ET FILTRES
            sf = tk.Frame(self, bg=CLR_BG)
            sf.pack(fill="x", padx=20, pady=5)
            logging.info("✅ Frame de recherche créé")
            
            # Recherche textuelle
            lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
            self.sv.trace_add("write", lambda *a: self.refresh())
            entry(sf, width=20, textvariable=self.sv).pack(side="left", padx=8)
            logging.info("✅ Champ recherche créé")

            # ✅ COMBOBOX FILTRE PAR FOURNISSEUR
            try:
                logging.info("🔧 Création de la combobox fournisseur...")
                lbl(sf, "Fournisseur:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
                
                if not hasattr(self, 'fournisseur_filter_var'):
                    self.fournisseur_filter_var = tk.StringVar(value="Tous")
                    
                self.fournisseur_filter_combo = combo(sf, ["Tous"], width=25, textvariable=self.fournisseur_filter_var)
                self.fournisseur_filter_combo.pack(side="left", padx=5)
                self.fournisseur_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
                logging.info("✅ Combobox fournisseur créée")
            except Exception as e:
                logging.error(f"❌ Erreur création combobox: {e}")
                self.fournisseur_filter_combo = None
                self.fournisseur_filter_var = tk.StringVar(value="Tous")
                logging.warning("⚠️ Combobox de secours créée")

            # ✅ CHARGER LES FOURNISSEURS
            try:
                logging.info("🔄 Chargement des fournisseurs...")
                self.load_fournisseurs_list()
                logging.info("✅ Fournisseurs chargés")
            except Exception as e:
                logging.error(f"❌ Erreur chargement fournisseurs: {e}")
                if self.fournisseur_filter_combo:
                    self.fournisseur_filter_combo['values'] = ["Tous"]
                    self.fournisseur_filter_var.set("Tous")

            # ✅ TABLEAU
            try:
                logging.info("🔧 Création du tableau...")
                cols = ["Numéro", "Date création", "Date livraison", "Fournisseur", "Total HT", "Total TTC", "Statut", "Situation TTC", "Cartons"]
                widths = [120, 100, 100, 200, 100, 100, 80, 120, 100]
                tf, self.tree = make_tree(self, cols, widths)
                tf.pack(fill="both", expand=True, padx=20, pady=10)
                logging.info("✅ Tableau créé")
            except Exception as e:
                logging.error(f"❌ Erreur création tableau: {e}")
                raise

            # ✅ CADRE DE SYNTHÈSE
            try:
                logging.info("🔧 Création de la synthèse...")
                synthese_frame = tk.Frame(self, bg=CLR_CARD, padx=15, pady=10)
                synthese_frame.pack(fill="x", padx=20, pady=(0, 10))
                
                lbl(synthese_frame, "📊 SYNTHÈSE DES ACHATS", 11, True, CLR_ACCENT).pack(anchor="w", pady=(0, 5))
                tk.Frame(synthese_frame, bg=CLR_BORDER, height=1).pack(fill="x", pady=5)
                
                totals_frame = tk.Frame(synthese_frame, bg=CLR_CARD)
                totals_frame.pack(fill="x", pady=5)
                
                lbl(totals_frame, "Total HT:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.total_ht_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.total_ht_global, bg=CLR_CARD, 
                        fg=CLR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 20))

                lbl(totals_frame, "Total TTC:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.total_ttc_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.total_ttc_global, bg=CLR_CARD, 
                        fg=CLR_ORANGE, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 20))

                lbl(totals_frame, "Situation TTC:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.situation_ttc_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.situation_ttc_global, bg=CLR_CARD, 
                        fg=CLR_GREEN, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 20))
                logging.info("✅ Synthèse créée")
            except Exception as e:
                logging.error(f"❌ Erreur création synthèse: {e}")
                self.total_ht_global = tk.StringVar(value="0.00 DA")
                self.total_ttc_global = tk.StringVar(value="0.00 DA")
                self.situation_ttc_global = tk.StringVar(value="0.00 DA")

            # ✅ BOUTONS D'ACTION
            try:
                logging.info("🔧 Création des boutons d'action...")
                bf = tk.Frame(self, bg=CLR_BG)
                bf.pack(fill="x", padx=20, pady=(0,15))
                
                for txt, cmd, clr in [
                    ("👁 Détail", self.view_bon, CLR_ACCENT),
                    ("✏ Modifier", self.edit_bon, CLR_ORANGE),
                    ("🗑 Supprimer", self.delete_bon, CLR_RED),
                    ("🗑 Annuler", self.cancel_bon, CLR_RED)
                ]:
                    tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                            font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
                logging.info("✅ Boutons d'action créés")
            except Exception as e:
                logging.error(f"❌ Erreur création boutons: {e}")

        except Exception as e:
            logging.error(f"❌ ERREUR DANS _build(): {e}")
            logging.error(traceback.format_exc())
            raise

    def load_fournisseurs_list(self):
        """Charge la liste des fournisseurs dans le combobox - AVEC LOGS"""
        try:
            logging.info("🔍 load_fournisseurs_list() - Début")
            
            # ✅ VÉRIFIER QUE LA COMBOBOX EXISTE
            if not hasattr(self, 'fournisseur_filter_combo') or self.fournisseur_filter_combo is None:
                logging.warning("❌ fournisseur_filter_combo n'existe pas ou est None !")
                # Créer une combobox de secours
                sf = tk.Frame(self, bg=CLR_BG)
                sf.pack(fill="x", padx=20, pady=5)
                lbl(sf, "Fournisseur:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
                self.fournisseur_filter_var = tk.StringVar(value="Tous")
                self.fournisseur_filter_combo = combo(sf, ["Tous"], width=25, textvariable=self.fournisseur_filter_var)
                self.fournisseur_filter_combo.pack(side="left", padx=5)
                self.fournisseur_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
                logging.info("✅ Combobox de secours créée")
            
            # ✅ CONNEXION À LA BASE
            logging.info(f"🔍 Connexion à la base: {DB_PATH}")
            conn = get_conn()
            logging.info("✅ Connexion OK")
            
            # ✅ VÉRIFIER LA TABLE fournisseurs
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fournisseurs'").fetchall()
            if not tables:
                logging.warning("⚠️ Table fournisseurs manquante !")
                conn.close()
                if self.fournisseur_filter_combo:
                    self.fournisseur_filter_combo['values'] = ["Tous"]
                    self.fournisseur_filter_var.set("Tous")
                return
            
            # ✅ COMPTER LES FOURNISSEURS
            count = conn.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0]
            logging.info(f"📊 {count} fournisseurs dans la base")
            
            # ✅ RÉCUPÉRER LES FOURNISSEURS
            fournisseurs = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            conn.close()
            
            # ✅ CONSTRUIRE LA LISTE
            fournisseur_liste = ["Tous"]
            for f in fournisseurs:
                fournisseur_liste.append(f["nom"])
            
            logging.info(f"📋 Liste des fournisseurs: {fournisseur_liste}")
            
            # ✅ METTRE À JOUR LA COMBOBOX
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = fournisseur_liste
                self.fournisseur_filter_var.set("Tous")
                logging.info("✅ Combobox mise à jour avec succès")
            else:
                logging.error("❌ fournisseur_filter_combo est None après création !")
                
        except sqlite3.OperationalError as e:
            logging.error(f"❌ Erreur SQLite: {e}")
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = ["Tous"]
                self.fournisseur_filter_var.set("Tous")
        except Exception as e:
            logging.error(f"❌ Erreur load_fournisseurs_list: {e}")
            
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = ["Tous"]
                self.fournisseur_filter_var.set("Tous")


    def refresh(self):
        q = self.sv.get().lower()
        fournisseur_filter = self.fournisseur_filter_var.get()
        
        if self.tree:
            self.tree.delete(*self.tree.get_children())
        else:
            logging.warning("⚠️ self.tree est None dans refresh()")
            return
        
        conn = get_conn()
        
        try:
            # ✅ REQUÊTE PRINCIPALE : Récupérer TOUS les bons (y compris SI-F-)
            if fournisseur_filter != "Tous":
                rows = conn.execute("""
                    SELECT 
                        b.id,
                        b.numero,
                        b.date_bon,
                        b.date_livraison,
                        f.nom as fnom,
                        b.total as total_ttc,
                        b.statut,
                        b.ancien_solde,
                        b.nouveau_solde,
                        (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                        FROM lignes_achat la 
                        JOIN produits p ON la.produit_id = p.id 
                        WHERE la.bon_id = b.id) as total_cartons
                    FROM bons_achat b
                    JOIN fournisseurs f ON b.fournisseur_id = f.id
                    WHERE f.nom = ?
                    ORDER BY b.date_bon DESC, b.numero DESC
                """, (fournisseur_filter,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT 
                        b.id,
                        b.numero,
                        b.date_bon,
                        b.date_livraison,
                        f.nom as fnom,
                        b.total as total_ttc,
                        b.statut,
                        b.ancien_solde,
                        b.nouveau_solde,
                        (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                        FROM lignes_achat la 
                        JOIN produits p ON la.produit_id = p.id 
                        WHERE la.bon_id = b.id) as total_cartons
                    FROM bons_achat b
                    JOIN fournisseurs f ON b.fournisseur_id = f.id
                    ORDER BY b.date_bon DESC, b.numero DESC
                """).fetchall()
        except Exception as e:
            logging.error(f"❌ Erreur requête: {e}")
            conn.close()
            return
        
        conn.close()
        
        total_ht_global = 0
        total_ttc_global = 0

        for r in rows:
            # ✅ RECHERCHE TEXTUELLE (numéro + fournisseur)
            if q and q not in r["numero"].lower() and q not in r["fnom"].lower():
                continue
            
            # ✅ RÉCUPÉRER LES LIGNES DU BON AVEC UNE NOUVELLE CONNEXION
            conn2 = get_conn()
            try:
                lignes_bon = conn2.execute("""
                    SELECT 
                        COALESCE(total_ht, 0) as ht,
                        COALESCE(total_ttc, 0) as ttc,
                        COALESCE(tva_taux, 19) as tva,
                        COALESCE(total, 0) as total
                    FROM lignes_achat 
                    WHERE bon_id = ?
                """, (r["id"],)).fetchall()
            except Exception as e:
                logging.error(f"❌ Erreur récupération lignes bon {r['id']}: {e}")
                conn2.close()
                continue
            
            conn2.close()
            
            ht_bon = 0
            ttc_bon = 0
            
            # ✅ SI LE BON N'A PAS DE LIGNES (ex: solde initial), on utilise total_ttc
            if not lignes_bon:
                # Utiliser le total du bon (souvent dans b.total)
                try:
                    ttc_bon = float(r["total_ttc"] or 0)
                    ht_bon = ttc_bon  # Pour les soldes initiaux, on considère HT = TTC
                except Exception as e:
                    logging.warning(f"⚠️ Erreur conversion total bon: {e}")
                    ttc_bon = 0
                    ht_bon = 0
            else:
                # ✅ CALCUL À PARTIR DES LIGNES
                for lg in lignes_bon:
                    try:
                        # Conversion sécurisée
                        ht_val = float(str(lg["ht"]).replace(',', '.')) if lg["ht"] not in (None, '') else 0
                        ttc_val = float(str(lg["ttc"]).replace(',', '.')) if lg["ttc"] not in (None, '') else 0
                        tva_val = float(str(lg["tva"]).replace(',', '.')) if lg["tva"] not in (None, '') else 19
                        total_val = float(str(lg["total"]).replace(',', '.')) if lg["total"] not in (None, '') else 0
                        
                        # Si TTC manquant, le recalculer
                        if ttc_val == 0 and ht_val > 0:
                            ttc_val = ht_val * (1 + tva_val / 100)
                        
                        ht_bon += ht_val
                        ttc_bon += ttc_val
                        
                    except Exception as e:
                        logging.warning(f"⚠️ Erreur traitement ligne: {e}")
                        continue
            
            # ✅ SI APRÈS TOUT, LE TTC EST ENCORE À 0, UTILISER LA VALEUR GLOBALE DU BON
            if ttc_bon == 0 and ht_bon == 0:
                try:
                    ttc_bon = float(r["total_ttc"] or 0)
                    ht_bon = ttc_bon
                except Exception as e:
                    logging.warning(f"⚠️ Erreur conversion total bon (fallback): {e}")
                    ttc_bon = 0
                    ht_bon = 0

            total_ht_global += ht_bon
            total_ttc_global += ttc_bon
            
            cartons = r['total_cartons'] or 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            # ✅ DÉTERMINER SI C'EST UN SOLDE INITIAL POUR L'AFFICHAGE
            if r["numero"].startswith("SI-F-"):
                statut_affichage = "SOLDE INITIAL"
                tag = ("solde_initial",)
            else:
                statut_affichage = r["statut"]
                tag = None
            
            try:
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], 
                    r["date_bon"],
                    r["date_livraison"] or "-", 
                    r["fnom"],
                    f"{ht_bon:,.2f}", 
                    f"{ttc_bon:,.2f}",
                    statut_affichage, 
                    f"{ttc_bon:,.2f}",
                    cartons_text
                ), tags=tag if tag else ())
            except Exception as e:
                logging.error(f"❌ Erreur insertion dans treeview: {e}")

        # ✅ METTRE À JOUR LES TOTAUX GLOBAUX
        self.total_ht_global.set(f"{total_ht_global:,.2f} DA")
        self.total_ttc_global.set(f"{total_ttc_global:,.2f} DA")
        self.situation_ttc_global.set(f"{total_ttc_global:,.2f} DA")

        # ✅ CONFIGURER LE TAG "solde_initial"
        self.tree.tag_configure("solde_initial", foreground=CLR_PURPLE, font=("Segoe UI", 9, "bold"))

        logging.info("✅ refresh() terminé")
    def _afficher_erreur(self, error):
        """Affiche une erreur dans la page"""
        for w in self.winfo_children():
            w.destroy()
        
        error_frame = tk.Frame(self, bg=CLR_BG)
        error_frame.pack(fill="both", expand=True, padx=50, pady=50)
        
        tk.Label(error_frame, text="❌ Erreur de chargement", 
                bg=CLR_BG, fg=CLR_RED, font=("Segoe UI", 18, "bold")).pack(pady=20)
        
        tk.Label(error_frame, text=f"Erreur: {str(error)}", 
                bg=CLR_BG, fg=CLR_TEXT, font=("Segoe UI", 12)).pack(pady=10)
        
        tk.Label(error_frame, text=f"Base de données: {DB_PATH}", 
                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 9)).pack(pady=5)
        
        if os.path.exists(DB_PATH):
            tk.Label(error_frame, text="✅ Fichier base trouvé", 
                    bg=CLR_BG, fg=CLR_GREEN, font=("Segoe UI", 9)).pack(pady=5)
        else:
            tk.Label(error_frame, text=f"❌ Fichier base NON trouvé: {DB_PATH}", 
                    bg=CLR_BG, fg=CLR_RED, font=("Segoe UI", 9)).pack(pady=5)
        
        tk.Button(error_frame, text="🔄 Réessayer", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(pady=20)

    def new_bon(self):
        d = BonDialog(self, "achat")
        self.wait_window(d)
        self.refresh()

    def view_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon")
            return
        d = BonDetailDialog(self, "achat", sel[0])
        self.wait_window(d)

    def edit_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à modifier")
            return
        bon_id = sel[0]
        conn = get_conn()
        bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (bon_id,)).fetchone()
        if bon["statut"] == "Annulé":
            messagebox.showwarning("", "Impossible de modifier un bon annulé")
            conn.close()
            return
        lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.prix_achat 
                                FROM lignes_achat l
                                JOIN produits p ON l.produit_id = p.id
                                WHERE l.bon_id=?""", (bon_id,)).fetchall()
        conn.close()
        d = BonEditDialog(self, "achat", bon_id, dict(bon), lignes)
        self.wait_window(d)
        self.refresh()

    def delete_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à supprimer")
            return
        if not messagebox.askyesno("Confirmation", 
                                "⚠️ Supprimer définitivement ce bon ?\n"
                                "Cette action est irréversible et ajustera le stock et les soldes."):
            return
        conn = get_conn()
        try:
            bon_id = sel[0]
            bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (bon_id,)).fetchone()
            lignes = conn.execute("SELECT * FROM lignes_achat WHERE bon_id=?", (bon_id,)).fetchall()
            if bon["statut"] != "Annulé":
                inverser_stock_achat(conn, lignes)
                conn.execute("UPDATE fournisseurs SET solde = solde - ? WHERE id=?", 
                        (bon["total"], bon["fournisseur_id"]))
            conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (bon_id,))
            conn.execute("DELETE FROM bons_achat WHERE id=?", (bon_id,))
            conn.commit()
            messagebox.showinfo("Succès", "Bon supprimé avec succès")
            self.refresh()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(ex)}")
        finally:
            conn.close()

    def cancel_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon")
            return
        if messagebox.askyesno("Annulation", "Annuler ce bon ? Le stock sera recalculé."):
            conn = get_conn()
            bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (sel[0],)).fetchone()
            if bon["statut"] == "Annulé":
                messagebox.showinfo("", "Déjà annulé")
                conn.close()
                return
            lignes = conn.execute("SELECT * FROM lignes_achat WHERE bon_id=?", (sel[0],)).fetchall()
            inverser_stock_achat(conn, lignes)
            fid = bon["fournisseur_id"]
            conn.execute("UPDATE fournisseurs SET solde = solde - ? WHERE id=?", (bon["total"], fid))
            conn.execute("UPDATE bons_achat SET statut='Annulé' WHERE id=?", (sel[0],))
            conn.commit()
            conn.close()
            self.refresh()

    def get_bons_data(self, fournisseur_filter=None):
        """Récupérer les données des bons avec filtre fournisseur"""
        conn = get_conn()
        
        if fournisseur_filter and fournisseur_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    f.nom as fournisseur, 
                    b.total as total_ttc,
                    b.statut,
                    (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                    FROM lignes_achat la 
                    JOIN produits p ON la.produit_id = p.id 
                    WHERE la.bon_id = b.id) as total_cartons
                FROM bons_achat b
                JOIN fournisseurs f ON b.fournisseur_id = f.id
                WHERE f.nom = ?
                ORDER BY b.date_bon DESC
            """, (fournisseur_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    f.nom as fournisseur, 
                    b.total as total_ttc,
                    b.statut,
                    (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                    FROM lignes_achat la 
                    JOIN produits p ON la.produit_id = p.id 
                    WHERE la.bon_id = b.id) as total_cartons
                FROM bons_achat b
                JOIN fournisseurs f ON b.fournisseur_id = f.id
                ORDER BY b.date_bon DESC
            """).fetchall()
        
        conn.close()
        
        data = []
        total_general = 0
        for r in rows:
            total_ttc = r["total_ttc"]
            total_general += total_ttc
            cartons = r["total_cartons"] if r["total_cartons"] is not None else 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            data.append([
                r["numero"], 
                r["date_bon"], 
                r["fournisseur"], 
                f"{total_ttc:,.2f}", 
                r["statut"],
                cartons_text
            ])
        
        if data:
            data.append(["", "", "", "", "", ""])
            data.append(["", "", "TOTAL TTC", f"{total_general:,.2f} DA", "", ""])
        
        return data, total_general

    def print_bons(self):
        fournisseur_filter = self.fournisseur_filter_var.get()
        data, total_general = self.get_bons_data(fournisseur_filter)
        
        if not data or len(data) <= 1:
            messagebox.showinfo("Information", "Aucun bon d'achat trouvé pour ce fournisseur")
            return
        
        if fournisseur_filter and fournisseur_filter != "Tous":
            title = f"LISTE DES BONS D'ACHAT - {fournisseur_filter.upper()}"
        else:
            title = "LISTE DES BONS D'ACHAT - TOUS LES FOURNISSEURS"
        
        headers = ["Numéro", "Date", "Fournisseur", "Total TTC", "Statut", "Cartons"]
        
        footer_text = f"\n{'='*60}\nTOTAL GENERAL TTC: {total_general:,.2f} DA\n{'='*60}\n"
        footer_text += f"Nombre de bons: {len(data)-2}\n"
        footer_text += f"Date d'impression: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        print_preview(data, title, headers, footer_text=footer_text)

    def export_bons(self):
        data, _ = self.get_bons_data(self.fournisseur_filter_var.get())
        headers = ["Numéro", "Date", "Fournisseur", "Total", "Statut", "Cartons"]
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="bons_achat.csv"
        )
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "BONS D'ACHAT", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")

# ========== PAGE BONS DE VENTE ==========

class BonVentePage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self,bg=CLR_BG)
        hdr.pack(fill="x",padx=20,pady=(20,10))
        lbl(hdr,"🏷️  Bons de Vente",16,True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Bon", command=self.new_bon,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # ✅ AJOUT DU BOUTON IMPRIMER
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bons,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="📊 Exporter", command=self.export_bons,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🛒 Vente Comptoir", command=self.vente_comptoir,
            bg=CLR_ORANGE, fg="white", relief="flat",
            font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🧾 Créer Facture", command=self.creer_facture,
            bg=CLR_GREEN, fg="white", relief="flat",
            font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)

        # 🔹 BARRE DE RECHERCHE ET FILTRES
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        
        # Recherche textuelle
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.sv = tk.StringVar()
        self.sv.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=20, textvariable=self.sv).pack(side="left", padx=8)

        # COMBOBOX FILTRE PAR CLIENT
        lbl(sf, "Client:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
        self.client_filter_var = tk.StringVar(value="Tous")
        self.client_filter_combo = combo(sf, [], width=25, textvariable=self.client_filter_var)
        self.client_filter_combo.pack(side="left", padx=5)
        self.client_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Charger la liste des clients
        self.load_clients_list()

        cols = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        widths = [120, 100, 200, 100, 80, 80, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        bf = tk.Frame(self,bg=CLR_BG)
        bf.pack(fill="x",padx=20,pady=(0,15))
        
        for txt, cmd, clr in [
            ("👁 Détail", self.view_bon, CLR_ACCENT),
            ("✏ Modifier", self.edit_bon, CLR_ORANGE),
            ("🗑 Supprimer", self.delete_bon, CLR_RED),
            ("🗑 Annuler", self.cancel_bon, CLR_RED)
        ]:
            tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    def get_bons_data(self, client_filter=None):
        """Récupérer les données des bons avec filtre client"""
        conn = get_conn()
        
        if client_filter and client_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    c.nom as client, 
                    b.total, 
                    b.statut,
                    CASE WHEN f.id IS NOT NULL THEN '✅ Oui' ELSE '❌ Non' END as facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id
                LEFT JOIN factures f ON b.id = f.bon_vente_id
                WHERE c.nom = ?
                ORDER BY b.date_bon DESC
            """, (client_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    c.nom as client, 
                    b.total, 
                    b.statut,
                    CASE WHEN f.id IS NOT NULL THEN '✅ Oui' ELSE '❌ Non' END as facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id
                LEFT JOIN factures f ON b.id = f.bon_vente_id
                ORDER BY b.date_bon DESC
            """).fetchall()
        
        conn.close()
        
        data = []
        total_general = 0
        for r in rows:
            # ✅ ACCÈS CORRECT avec le nom de la colonne
            total = r["total"]  # ✅ r["total"] est disponible
            total_general += total
            cartons = r["total_cartons"] if r["total_cartons"] is not None else 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            data.append([
                r["numero"], 
                r["date_bon"], 
                r["client"], 
                f"{total:,.2f}", 
                r["statut"], 
                r["facture"],
                cartons_text
            ])
        
        # Ajouter la ligne de total en bas
        if data:
            data.append(["", "", "", "", "", "", ""])
            data.append(["", "", "TOTAL GENERAL", f"{total_general:,.2f} DA", "", "", ""])
        
        return data, total_general                
    def print_bons(self):
        """Imprimer les bons du client sélectionné avec total"""
        client_filter = self.client_filter_var.get()
        
        # ✅ Récupérer les données via get_bons_data()
        data, total_general = self.get_bons_data(client_filter)
        
        if not data or len(data) <= 1:
            messagebox.showinfo("Information", "Aucun bon de vente trouvé pour ce client")
            return
        
        if client_filter and client_filter != "Tous":
            title = f"LISTE DES BONS DE VENTE - {client_filter.upper()}"
        else:
            title = "LISTE DES BONS DE VENTE - TOUS LES CLIENTS"
        
        # ✅ En-têtes avec la colonne Cartons
        headers = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        
        footer_text = f"\n{'='*60}\nTOTAL GENERAL: {total_general:,.2f} DA\n{'='*60}\n"
        footer_text += f"Nombre de bons: {len(data)-2}\n"
        footer_text += f"Date d'impression: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        print_preview(data, title, headers, footer_text=footer_text)
    def export_bons(self):
        """Exporter les bons de vente en CSV ou HTML"""
        client_filter = self.client_filter_var.get()
        
        # ✅ Récupérer les données via get_bons_data()
        data, total_general = self.get_bons_data(client_filter)
        
        if not data or len(data) <= 1:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        # ✅ En-têtes avec la colonne Cartons
        headers = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="bons_vente.csv"
        )
        
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "BONS DE VENTE", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    def vente_comptoir(self):
        d = VenteComptoirDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def creer_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon de vente")
            return
        
        conn = get_conn()
        # Vérifier si une facture existe déjà
        existing = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if existing:
            messagebox.showwarning("", "Ce bon a déjà une facture associée")
            conn.close()
            return
        
        bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        # Ouvrir le dialogue de création de facture avec le bon pré-sélectionné
        d = FactureDialog(self, pre_selected_bon=dict(bon))
        self.wait_window(d)
        self.refresh()
    def load_clients_list(self):
        """Charge la liste des clients dans le combobox"""
        conn = get_conn()
        clients = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
        conn.close()
        
        client_liste = ["Tous"] + [f"{c['nom']}" for c in clients]
        self.client_filter_combo['values'] = client_liste
        if client_liste:
            self.client_filter_var.set("Tous")

    def refresh(self):
        q = self.sv.get().lower()
        client_filter = self.client_filter_var.get()
        
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        
        # 🔹 REQUÊTE AVEC FILTRE CLIENT ET CALCUL DES CARTONS
        if client_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.*, 
                    c.nom as cnom,
                    (SELECT COUNT(*) FROM factures WHERE bon_vente_id = b.id) as a_facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id 
                WHERE c.nom = ?
                ORDER BY b.date_bon DESC, b.numero DESC
            """, (client_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.*, 
                    c.nom as cnom,
                    (SELECT COUNT(*) FROM factures WHERE bon_vente_id = b.id) as a_facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id 
                ORDER BY b.date_bon DESC, b.numero DESC
            """).fetchall()
        conn.close()
        
        for r in rows:
            if q in r["numero"].lower() or q in r["cnom"].lower():
                facture_info = "✅ Oui" if r["a_facture"] > 0 else "❌ Non"
                cartons = r['total_cartons'] or 0
                cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
                
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], 
                    r["date_bon"], 
                    r["cnom"],
                    f"{r['total']:.2f}", 
                    r["statut"], 
                    facture_info,
                    cartons_text  # ✅ Nouvelle colonne
                ))

    def new_bon(self):
        d = BonDialog(self,"vente")
        self.wait_window(d)
        self.refresh()

    def view_bon(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un bon")
            return
        d = BonDetailDialog(self,"vente",sel[0])
        self.wait_window(d)

    def edit_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à modifier")
            return
        bon_id = sel[0]
        conn = get_conn()
        bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (bon_id,)).fetchone()
        if bon["statut"] == "Annulé":
            messagebox.showwarning("", "Impossible de modifier un bon annulé")
            conn.close()
            return
        # Vérifier si une facture existe
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (bon_id,)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible de modifier un bon qui a déjà une facture")
            conn.close()
            return
        lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.prix_vente 
                                FROM lignes_vente l
                                JOIN produits p ON l.produit_id = p.id
                                WHERE l.bon_id=?""", (bon_id,)).fetchall()
        conn.close()
        d = BonEditDialog(self, "vente", bon_id, dict(bon), lignes)
        self.wait_window(d)
        self.refresh()

    def delete_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à supprimer")
            return
        conn = get_conn()
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible de supprimer un bon qui a une facture associée")
            conn.close()
            return
        conn.close()
        
        if not messagebox.askyesno("Confirmation", 
                                "⚠️ Supprimer définitivement ce bon ?\n"
                                "Cette action est irréversible et ajustera le stock et les soldes."):
            return
        conn = get_conn()
        try:
            bon_id = sel[0]
            bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (bon_id,)).fetchone()
            lignes = conn.execute("SELECT * FROM lignes_vente WHERE bon_id=?", (bon_id,)).fetchall()
            if bon["statut"] != "Annulé":
                for l in lignes:
                    # ✅ CORRECTION : recalculer le coût du stock en même temps que la quantité
                    entree_stock_annulation_vente(conn, l["produit_id"], l["quantite"])
                # ✅ CORRECTION — ne pas toucher au solde COMPTOIR
                client = conn.execute("SELECT nom FROM clients WHERE id=?",
                                    (bon["client_id"],)).fetchone()
                if client and client["nom"] != "COMPTOIR":
                    conn.execute("UPDATE clients SET solde = solde - ? WHERE id=?", 
                            (bon["total"], bon["client_id"]))
            conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (bon_id,))
            conn.execute("DELETE FROM bons_vente WHERE id=?", (bon_id,))
            conn.commit()
            messagebox.showinfo("Succès", "Bon supprimé avec succès")
            self.refresh()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(ex)}")
        finally:
            conn.close()

    def cancel_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon")
            return
    
        conn = get_conn()
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible d'annuler un bon qui a une facture associée")
            conn.close()
            return
    
        if messagebox.askyesno("Annulation", "Annuler ce bon de vente ?"):
            bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (sel[0],)).fetchone()
            if bon["statut"] == "Annulé":
                messagebox.showinfo("", "Déjà annulé")
                conn.close()
                return
    
            lignes = conn.execute("SELECT * FROM lignes_vente WHERE bon_id=?", (sel[0],)).fetchall()
            for l in lignes:
                # ✅ CORRECTION
                entree_stock_annulation_vente(conn, l["produit_id"], l["quantite"])
    
            # ✅ CORRECTION : ne pas toucher au solde du client COMPTOIR
            client = conn.execute(
                "SELECT nom FROM clients WHERE id=?", (bon["client_id"],)
            ).fetchone()
            if client and client["nom"] != "COMPTOIR":
                conn.execute(
                    "UPDATE clients SET solde=solde-? WHERE id=?",
                    (bon["total"], bon["client_id"])
                )
    
            conn.execute("UPDATE bons_vente SET statut='Annulé' WHERE id=?", (sel[0],))
            conn.commit()
            conn.close()
            self.refresh()
 


# ========== DIALOGUE VENTE COMPTOIR ==========

class VenteComptoirDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🛒 CAISSE ENREGISTREUSE - Vente Comptoir")
        self.configure(bg=CLR_BG)
        self.geometry("1400x700")
        self.minsize(1200, 700)
        center_window(self, 1400, 700)
        
        # ✅ Initialiser toutes les variables AVANT _build()
        self.lignes = []
        self.montant_recu = 0
        self.monnaie = 0
        self.total_avant_remise = 0
        
        # ✅ Variables tkinter
        self.prix_var = tk.StringVar()
        self.prod_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        self.client_nom = tk.StringVar(value="COMPTOIR")
        self.code_barre = tk.StringVar()
        self.total_var = tk.StringVar(value="0.00 DA")
        self.montant_recu_var = tk.StringVar(value="0")
        self.monnaie_var = tk.StringVar(value="0.00 DA")
        
        # ✅ Maps et listes
        self.prod_map = {}
        self.prod_list = []
        self.clients_map = {}
        
        self._build()
        self.after(100, lambda: self.code_barre_entry.focus())
    
    def _build(self):
        # ============================================================
        # 1. HEADER
        # ============================================================
        header = tk.Frame(self, bg=CLR_CARD, height=80)
        header.pack(fill="x", padx=10, pady=(10,5))
        header.pack_propagate(False)
        
        # Titre à gauche
        title_frame = tk.Frame(header, bg=CLR_CARD)
        title_frame.pack(side="left", fill="y", padx=15)
        lbl(title_frame, "🏪 CAISSE ENREGISTREUSE", 18, True, color=CLR_GREEN).pack(anchor="w")
        lbl(title_frame, "Mode Vente Comptoir", 9, color=CLR_MUTED).pack(anchor="w")
        
        # Date/Heure à droite
        datetime_frame = tk.Frame(header, bg=CLR_CARD)
        datetime_frame.pack(side="right", padx=15)
        self.date_label = tk.Label(datetime_frame, font=("Segoe UI", 10), bg=CLR_CARD, fg=CLR_TEXT)
        self.date_label.pack()
        self.time_label = tk.Label(datetime_frame, font=("Segoe UI", 16, "bold"), bg=CLR_CARD, fg=CLR_ACCENT)
        self.time_label.pack()
        self.update_datetime()
        
        # Client (à droite avant la date)
        client_frame = tk.Frame(header, bg=CLR_CARD)
        client_frame.pack(side="right", padx=15)
        lbl(client_frame, "Client:", color=CLR_MUTED, size=10).pack(side="left")
        
        self.client_combo = combo(client_frame, ["COMPTOIR"], width=18, textvariable=self.client_nom)
        self.client_combo.pack(side="left", padx=5)
        
        tk.Button(client_frame, text="+ Client", command=self.creer_client_rapide,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=8, pady=2, cursor="hand2").pack(side="left", padx=5)
        
        self.charger_clients()
        
        # ============================================================
        # 2. CONTENEUR PRINCIPAL (3 colonnes)
        # ============================================================
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configuration des colonnes avec des poids corrects
        main_container.grid_columnconfigure(0, weight=1)   # Panneau gauche
        main_container.grid_columnconfigure(1, weight=2)   # Panneau central
        main_container.grid_columnconfigure(2, weight=1)   # Panneau droit
        main_container.grid_rowconfigure(0, weight=1)
        
        # ============================================================
        # 3. PANEL GAUCHE - Recherche et saisie
        # ============================================================
        left_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        
        # --- Titre ---
        lbl(left_panel, "🔍 RECHERCHE", 12, True, color=CLR_ACCENT).pack(anchor="w", pady=(0,10))
        
        # --- Code barre ---
        scan_frame = tk.Frame(left_panel, bg=CLR_CARD)
        scan_frame.pack(fill="x", pady=5)
        lbl(scan_frame, "Code barre:", color=CLR_MUTED, size=9).pack(side="left")
        
        self.code_barre_entry = tk.Entry(scan_frame, width=20, textvariable=self.code_barre,
                                         bg=CLR_INPUT, fg=CLR_TEXT, font=("Segoe UI", 11),
                                         relief="flat", highlightthickness=1)
        self.code_barre_entry.pack(side="left", padx=8)
        self.code_barre_entry.bind("<Return>", lambda e: self.recherche_par_code())
        
        tk.Button(scan_frame, text="Chercher", command=self.recherche_par_code,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=10).pack(side="left")
        
        # --- Sélection produit ---
        lbl(left_panel, "Sélection produit:", color=CLR_MUTED, size=9).pack(anchor="w", pady=(15,5))
        
        self.charger_produits()
        
        self.prod_combo = combo(left_panel, self.prod_list, width=30, textvariable=self.prod_var)
        self.prod_combo.pack(fill="x", pady=5)
        self.prod_combo.bind("<<ComboboxSelected>>", self.on_produit_selectionne)
        
        # --- Quantité et Prix sur une ligne ---
        qty_frame = tk.Frame(left_panel, bg=CLR_CARD)
        qty_frame.pack(fill="x", pady=8)
        
        lbl(qty_frame, "Qté:", color=CLR_MUTED, size=9).pack(side="left", padx=2)
        entry(qty_frame, width=8, textvariable=self.qty_var, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        lbl(qty_frame, "Prix:", color=CLR_MUTED, size=9).pack(side="left", padx=(15,2))
        entry(qty_frame, width=10, textvariable=self.prix_var, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # --- Boutons ---
        btn_frame = tk.Frame(left_panel, bg=CLR_CARD)
        btn_frame.pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="➕ AJOUTER", command=self.ajouter_ligne,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)
        
        tk.Button(btn_frame, text="🔄 Rafraîchir", command=self.charger_produits,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)
        
        # ============================================================
        # 4. PANEL CENTRAL - Panier
        # ============================================================
        center_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=5)
                
        # Tableau du panier
        cols = ["Code", "Produit", "Qté", "Prix", "Total"]
        widths = [80, 280, 60, 80, 100]
        tf, self.tree = make_tree(center_panel, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)
        
        # Boutons du panier
        panier_btn_frame = tk.Frame(center_panel, bg=CLR_CARD)
        panier_btn_frame.pack(fill="x", pady=8)
        
        tk.Button(panier_btn_frame, text="🗑 Supprimer", command=self.supprimer_ligne,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        tk.Button(panier_btn_frame, text="🔄 Modifier Qté", command=self.modifier_quantite,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        tk.Button(panier_btn_frame, text="🗑 Vider", command=self.vider_panier,
                  bg=CLR_BORDER, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        # ============================================================
        # 5. PANEL DROIT - Encaissement
        # ============================================================
        right_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5,0))
        
        # Total
        total_frame = tk.Frame(right_panel, bg=CLR_CARD)
        total_frame.pack(fill="x", pady=5)
        lbl(total_frame, "TOTAL À PAYER", 10, True, color=CLR_TEXT).pack(side="left")
        tk.Label(total_frame, textvariable=self.total_var, bg=CLR_CARD, 
                 fg=CLR_GREEN, font=("Segoe UI", 20, "bold")).pack(side="right")
        
        # Montant reçu
        recu_frame = tk.Frame(right_panel, bg=CLR_CARD)
        recu_frame.pack(fill="x", pady=8)
        lbl(recu_frame, "Montant reçu:", 9, True).pack(side="left")
        
        self.montant_recu_entry = entry(recu_frame, width=12, textvariable=self.montant_recu_var, 
                                        font=("Segoe UI", 12), justify="right")
        self.montant_recu_entry.pack(side="right", padx=5)
        self.montant_recu_entry.bind("<KeyRelease>", self.calculer_monnaie)
        
        # Monnaie à rendre
        monnaie_frame = tk.Frame(right_panel, bg=CLR_CARD)
        monnaie_frame.pack(fill="x", pady=8)
        lbl(monnaie_frame, "Monnaie à rendre:", 9, True).pack(side="left")
        tk.Label(monnaie_frame, textvariable=self.monnaie_var, bg=CLR_CARD, 
                 fg=CLR_ORANGE, font=("Segoe UI", 14, "bold")).pack(side="right")
        
        # Séparateur
        tk.Frame(right_panel, bg=CLR_BORDER, height=2).pack(fill="x", pady=8)
        
        # Boutons d'action
        tk.Button(right_panel, text="✅ VALIDER", command=self.valider_vente,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=15, pady=10, cursor="hand2").pack(fill="x", pady=5)
        
        tk.Button(right_panel, text="🖨 TICKET", command=self.imprimer_ticket_rapide,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(fill="x", pady=5)
        
        tk.Button(right_panel, text="❌ ANNULER", command=self.destroy,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(fill="x", pady=5)
    
    def charger_produits(self):
        """Charge/recharge la liste des produits"""
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                                   prix_achat, prix_vente, barcode, stock_actuel,
                                   prix_detail, prix_gros, prix_super_gros, prix_special
                            FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        self.prod_map = {}
        self.prod_list = []
        for r in prods:
            display = f"{r['code']} - {r['designation']} ({r['prix_vente']:.2f} DA)"
            self.prod_map[display] = dict(r)
            self.prod_list.append(display)
        
        if hasattr(self, 'prod_combo'):
            self.prod_combo['values'] = self.prod_list
        
        # Garder la sélection actuelle si possible
        current = self.prod_var.get()
        if current not in self.prod_map and self.prod_list:
            self.prod_var.set(self.prod_list[0])
    
    def update_datetime(self):
        now = datetime.now()
        self.date_label.config(text=now.strftime("%A %d %B %Y").upper())
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.after(1000, self.update_datetime)
    
    def charger_clients(self):
        conn = get_conn()
        try:
            clients = conn.execute(
                "SELECT id, nom FROM clients ORDER BY nom"
            ).fetchall()
        finally:
            conn.close()
        
        self.clients_map = {}
        client_liste = []
        for c in clients:
            self.clients_map[c["nom"]] = c["id"]
            client_liste.append(c["nom"])
        if "COMPTOIR" in self.clients_map:
            client_liste.remove("COMPTOIR")
            client_liste.insert(0, "COMPTOIR")
        self.client_combo['values'] = client_liste
        if client_liste:
            self.client_nom.set(client_liste[0])
    
    def creer_client_rapide(self):
        nom = simpledialog.askstring("Nouveau Client", "Nom du client:", parent=self)
        if nom and nom.strip():
            code_auto = generer_code_unique("CLT", "clients", mode="sequentiel")
            conn = get_conn()
            try:
                conn.execute("""INSERT INTO clients(code, nom, adresse, tel, email, solde) 
                            VALUES(?, ?, ?, ?, ?, ?)""", 
                        (code_auto, nom.strip(), "", "", "", 0))
                conn.commit()
                messagebox.showinfo("Succès", f"Client '{nom}' créé avec le code {code_auto}")
                self.charger_clients()
                self.client_nom.set(nom.strip())
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))
            finally:
                conn.close()
    
    def recherche_par_code(self):
        code = self.code_barre.get().strip()
        if not code:
            return
        normalized = normalize_barcode_input(code)
        conn = get_conn()
        produit = conn.execute(
            "SELECT * FROM produits WHERE (barcode = ? OR code = ?) AND actif = 1",
            (normalized, normalized)
        ).fetchone()
        conn.close()
        if produit:
            for display, p in self.prod_map.items():
                if p["id"] == produit["id"]:
                    self.prod_var.set(display)
                    # ✅ Utiliser le prix de détail
                    prix_detail = produit.get("prix_detail", 0) or produit.get("prix_vente", 0)
                    self.prix_var.set(str(prix_detail))
                    self.qty_var.set("1")
                    self.code_barre.set("")
                    self.ajouter_ligne()
                    break
        else:
            messagebox.showwarning("Non trouvé", f"Produit non trouvé: {code}")
    
    def on_produit_selectionne(self, event):
        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            # ✅ Utiliser le prix de détail
            prix = p.get("prix_detail", 0) or p.get("prix_vente", 0)
            self.prix_var.set(str(prix))
    
    def ajouter_ligne(self):
        key = self.prod_var.get()
        if not key or key not in self.prod_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit", parent=self)
            return
        try:
            qty = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide", parent=self)
            return
        if qty <= 0:
            messagebox.showerror("Erreur", "Quantité > 0", parent=self)
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix > 0", parent=self)
            return
        
        prod = self.prod_map[key]
        
        # Convertir la saisie en unités de stock pour comparaison
        facteur = float(prod.get("facteur_conversion") or 1)
        qty_en_unites = qty * facteur
        stock_en_cartons = prod["stock_actuel"] / facteur if facteur else prod["stock_actuel"]
        
        if qty_en_unites > prod["stock_actuel"]:
            messagebox.showerror(
                "Stock insuffisant",
                f"Stock disponible : {stock_en_cartons:.2f} cartons "
                f"({prod['stock_actuel']:.2f} unités)\n"
                f"Quantité demandée : {qty:.2f} cartons ({qty_en_unites:.2f} unités)",
                parent=self
            )
            return
        
        # Vérifier si le produit est déjà dans le panier
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                ligne["quantite"] += qty
                ligne["qty_base"] = ligne.get("qty_base", ligne["quantite"]) + qty_en_unites
                ligne["total"] = ligne["qty_base"] * ligne["prix"]
                self._refresh_panier()
                self.qty_var.set("1")
                return
        
        total = qty_en_unites * prix
        self.lignes.append({
            "produit_id": prod["id"],
            "code": prod["code"],
            "designation": prod["designation"],
            "quantite": qty,          # quantité affichée (cartons)
            "qty_base": qty_en_unites,  # quantité réelle pour le stock
            "facteur": facteur,
            "prix": prix,
            "total": total
        })
        self._refresh_panier()
        self.qty_var.set("1")
    
    def supprimer_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne", parent=self)
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_panier()
    
    def modifier_quantite(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne", parent=self)
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]
        nouvelle_qty = simpledialog.askfloat("Modifier quantité",
                                            f"Quantité: {ligne['quantite']}\nNouvelle valeur:",
                                            initialvalue=ligne['quantite'], parent=self)
        if nouvelle_qty and nouvelle_qty > 0:
            # ✅ Mettre à jour la quantité en unité d'affichage
            facteur = ligne.get("facteur", 1)
            ligne["quantite"] = nouvelle_qty
            ligne["qty_base"] = nouvelle_qty * facteur
            ligne["total"] = ligne["qty_base"] * ligne["prix"]
            self._refresh_panier()
    
    def vider_panier(self):
        if self.lignes and messagebox.askyesno("Confirmation", "Vider le panier ?", parent=self):
            self.lignes = []
            self._refresh_panier()
    
    def _refresh_panier(self):
        self.tree.delete(*self.tree.get_children())
        total_brut = 0
        for i, l in enumerate(self.lignes):
            self.tree.insert("", "end", iid=str(i),
                values=(l["code"], l["designation"], f"{l['quantite']:.1f}", 
                    f"{l['prix']:.2f}", f"{l['total']:.2f}"))
            total_brut += l["total"]
        self.total_avant_remise = total_brut
        self.total_var.set(f"{total_brut:,.2f} DA")
        self.calculer_monnaie()
    
    def calculer_monnaie(self, event=None):
        try:
            total_str = self.total_var.get().replace(" DA", "").replace(",", "")
            total = float(total_str)
            recu = parse_decimal(self.montant_recu_var.get() or "0")
            if recu >= total:
                monnaie = recu - total
                self.monnaie_var.set(f"{monnaie:,.2f} DA")
            else:
                self.monnaie_var.set(f"Manque: {total - recu:,.2f} DA")
        except (ValueError, TypeError):
            self.monnaie_var.set("0.00 DA")
    
    def valider_vente(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez des produits", parent=self)
            return
        
        total = self.total_avant_remise
        client_nom = self.client_nom.get()
        
        client_id = self.clients_map.get(client_nom)
        if not client_id:
            messagebox.showerror("Erreur", f"Client '{client_nom}' introuvable", parent=self)
            return
        
        try:
            recu = parse_decimal(self.montant_recu_var.get() or "0")
        except ValueError:
            recu = 0
        
        if recu < total:
            messagebox.showerror(
                "Erreur",
                f"Montant insuffisant!\nTotal: {total:,.2f} DA\nManque: {total-recu:,.2f} DA",
                parent=self
            )
            return
        
        monnaie = recu - total
        if not messagebox.askyesno(
            "Confirmation",
            f"✅ VALIDER ?\n\nClient: {client_nom}\nTotal: {total:,.2f} DA\n"
            f"Reçu: {recu:,.2f} DA\nMonnaie: {monnaie:,.2f} DA",
            parent=self
        ):
            return
        
        num = next_numero_tiers("BV", client_id)
        dt = date.today().strftime("%Y-%m-%d")
        
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO bons_vente(numero, date_bon, client_id, total, statut) VALUES(?,?,?,?,?)",
                (num, dt, client_id, total, "Validé")
            )
            bon_id = conn.execute(
                "SELECT id FROM bons_vente WHERE numero=?", (num,)
            ).fetchone()["id"]
            
            for l in self.lignes:
                facteur_l = float(l.get("facteur", 1) or 1)
                qty_base = l["quantite"] * facteur_l
                
                conn.execute(
                    "INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total) "
                    "VALUES(?,?,?,?,?)",
                    (bon_id, l["produit_id"], qty_base, l["prix"], l["total"])
                )
                # ✅ CORRECTION : réduire le coût du stock (PMP conservé, cout_total_stock ajusté)
                recalculer_cout_stock_apres_sortie(conn, l["produit_id"], qty_base)
               
            if client_nom != "COMPTOIR":
                conn.execute(
                    "UPDATE clients SET solde = solde + ? WHERE id=?", (total, client_id)
                )
            
            conn.commit()
            self.imprimer_ticket(num, client_nom, total, recu, monnaie)
            messagebox.showinfo(
                "Succès",
                f"✅ Vente enregistrée!\nBon: {num}\nMonnaie: {monnaie:,.2f} DA",
                parent=self
            )
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex), parent=self)
        finally:
            conn.close()
    
    def imprimer_ticket(self, num, client_nom, total, recu, monnaie):
        """Affiche le ticket avec bouton d'impression"""
        
        # ✅ Créer la fenêtre du ticket
        preview = tk.Toplevel(self)
        preview.title(f"TICKET N°{num}")
        preview.configure(bg="white")
        preview.geometry("400x600")
        preview.resizable(False, False)
        
        # ✅ Garder la fenêtre au premier plan
        preview.transient(self)
        preview.grab_set()
        preview.focus_force()
        preview.lift()
        
        # ✅ Centrer
        center_window(preview, 400, 600)
        
        # ✅ Conteneur principal
        main_frame = tk.Frame(preview, bg="white")
        main_frame.pack(fill="both", expand=True)
        
        # ✅ Zone de texte pour le ticket
        text_frame = tk.Frame(main_frame, bg="white")
        text_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        text_widget = tk.Text(text_frame, bg="white", fg="black", 
                            font=("Courier", 10), wrap="none",
                            relief="flat", highlightthickness=0)
        text_widget.pack(side="left", fill="both", expand=True)
        
        # ✅ Scrollbar
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # ✅ Construire le contenu du ticket
        content = []
        content.append("=" * 32)
        content.append("       VOTRE MAGASIN")
        content.append("=" * 32)
        content.append("")
        content.append(f"Ticket: {num}")
        content.append(f"Date  : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        content.append(f"Client: {client_nom}")
        content.append("")
        content.append("-" * 32)
        content.append("")
        
        # ✅ Lignes de produits
        for i, l in enumerate(self.lignes, 1):
            designation = l['designation'][:25]
            qty = l['quantite']
            total_ligne = l['total']
            content.append(f"{i:2d}. {designation}")
            content.append(f"    {qty:6.0f} x {l['prix']:8.2f} = {total_ligne:10.2f} DA")
            content.append("")
        
        content.append("-" * 32)
        content.append("")
        content.append(f"TOTAL À PAYER : {total:>12,.2f} DA")
        content.append(f"Montant reçu   : {recu:>12,.2f} DA")
        content.append(f"Monnaie        : {monnaie:>12,.2f} DA")
        content.append("")
        content.append("-" * 32)
        content.append("")
        content.append("         MERCI DE VOTRE VISITE !")
        content.append("")
        content.append("=" * 32)
        
        # ✅ Insérer le contenu
        text_widget.insert("1.0", "\n".join(content))
        text_widget.config(state="disabled")
        
        # ✅ Boutons en bas
        btn_frame = tk.Frame(main_frame, bg="white", pady=10)
        btn_frame.pack(fill="x", padx=15)
        
        # ✅ Bouton Imprimer
        btn_imprimer = tk.Button(
            btn_frame,
            text="🖨  IMPRIMER",
            command=lambda: self._imprimer_ticket_html(content, num),
            bg=CLR_ACCENT,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief="flat"
        )
        btn_imprimer.pack(side="left", expand=True, fill="x", padx=5)
        
        # ✅ Bouton Fermer
        btn_fermer = tk.Button(
            btn_frame,
            text="✕  FERMER",
            command=lambda: self._fermer_ticket(preview),
            bg=CLR_RED,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief="flat"
        )
        btn_fermer.pack(side="left", expand=True, fill="x", padx=5)
        
        # ✅ Focus sur le bouton Imprimer
        btn_imprimer.focus_set()
        
        # ✅ Raccourcis clavier
        preview.bind("<Escape>", lambda e: self._fermer_ticket(preview))
        preview.bind("<Return>", lambda e: self._imprimer_ticket_html(content, num))

    def _imprimer_ticket_html(self, content, num):
        """Imprime le ticket via HTML (ouvre dans le navigateur pour impression)"""
        try:
            # ✅ Construire le contenu HTML
            content_text = "\n".join(content)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Ticket N°{num}</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        font-size: 11pt;
                        padding: 20px;
                        margin: 0;
                        background: white;
                        color: black;
                        max-width: 380px;
                        margin: 0 auto;
                    }}
                    pre {{
                        font-family: 'Courier New', monospace;
                        font-size: 11pt;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        padding: 0;
                    }}
                    @media print {{
                        body {{
                            padding: 10px;
                            margin: 0;
                        }}
                        .no-print {{
                            display: none !important;
                        }}
                    }}
                </style>
            </head>
            <body>
                <pre>{content_text}</pre>
                <div class="no-print" style="text-align:center; margin-top:20px; padding:10px; border-top:1px solid #ccc;">
                    <p style="font-family:Arial; font-size:10px; color:#666;">
                        Utilisez <strong>Ctrl+P</strong> ou <strong>Fichier > Imprimer</strong>
                    </p>
                </div>
                <script>
                    // ✅ Impression automatique après 1 seconde
                    setTimeout(function() {{
                        window.print();
                    }}, 500);
                    
                    // ✅ Fermer la fenêtre après impression ou annulation
                    window.onafterprint = function() {{
                        setTimeout(function() {{
                            window.close();
                        }}, 500);
                    }};
                </script>
            </body>
            </html>
            """
            
            # ✅ Créer un fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.html', 
                delete=False, 
                encoding='utf-8'
            )
            temp_file.write(html_content)
            temp_file.close()
            
            # ✅ Ouvrir dans le navigateur
            webbrowser.open(temp_file.name)
            
            # ✅ Supprimer le fichier après 30 secondes
            self.after(30000, lambda: self._supprimer_fichier_temp(temp_file.name))
            
            # ✅ Message d'information
            messagebox.showinfo(
                "Impression", 
                "🖨️ Le ticket s'ouvre dans votre navigateur.\n\n"
                "➡️ L'impression se lance automatiquement.\n"
                "➡️ Si ce n'est pas le cas, utilisez Ctrl+P.",
                parent=self
            )
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'impression: {str(e)}")

    def _supprimer_fichier_temp(self, filepath):
        """Supprime le fichier temporaire"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except:
            pass

    def _fermer_ticket(self, preview_window):
        """Ferme la fenêtre du ticket et rend le focus à la caisse"""
        preview_window.destroy()
        # ✅ Redonner le focus à la fenêtre principale de la caisse
        self.focus_force()
        self.lift()
        self.code_barre_entry.focus_set()
    
    def imprimer_ticket_rapide(self):
        if not self.lignes:
            messagebox.showwarning("", "Panier vide", parent=self)
            return
        total = sum(l["total"] for l in self.lignes)
        recu = parse_decimal(self.montant_recu_var.get() or "0")
        monnaie = max(0, recu - total)
        self.imprimer_ticket("PREVIEW", self.client_nom.get(), total, recu, monnaie)


# ========== DIALOGUE BON (Achat/Vente) ==========

class BonDialog(tk.Toplevel):
    def __init__(self, parent, bon_type):
        super().__init__(parent)
        self.bon_type = bon_type
        self.title("Bon d'Achat" if bon_type=="achat" else "Bon de Vente")
        self.configure(bg=CLR_BG)
        
        # Maximiser la fenêtre (prend tout l'écran sauf barre des tâches)
        self.state('zoomed')  # Pour Windows
        
        self.geometry("1000x750")
        self.lignes = []
        # ✅ VARIABLES POUR LA REMISE
        self.total_avant_remise = 0
        self.total_apres_remise = 0
        self.remise_appliquee = False
        self.remise_type = "aucune"
        self.remise_valeur = 0
        self.remise_motif = ""
        self.bind("<<ProduitsModifies>>", lambda e: self.refresh_produits())
        self._build()
        center_window(self, 1000, 750)

    def _build(self):
        # Frame principal avec padding
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # ========== SECTION EN-TÊTE ==========
        header_frame = tk.Frame(main_container, bg=CLR_CARD, padx=15, pady=12, relief="groove", bd=1)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Ligne 1: Numéro et Date
        line1 = tk.Frame(header_frame, bg=CLR_CARD)
        line1.pack(fill="x", pady=5)
        
        lbl(line1, "Numéro:", color=CLR_MUTED).pack(side="left", padx=4)
        prefix = "BA" if self.bon_type=="achat" else "BV"
        self.load_tiers_list()

        # Générer le numéro dès le premier tiers disponible
        if self.tiers_map:
            premier_tiers_id = list(self.tiers_map.values())[0]
            num_initial = next_numero_tiers(prefix, premier_tiers_id)
        else:
            num_initial = f"{prefix}-00000-0001"
        self.num_var = tk.StringVar(value=num_initial)  # sera généré à la validation
        entry(line1, width=18, textvariable=self.num_var).pack(side="left", padx=4)
        
        # Date avec calendrier
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        DateEntry(line1, self.date_var, label_text="Date:", width=12).pack(side="left", padx=4)
        
        # Ligne 2: Fournisseur/Client
        line2 = tk.Frame(header_frame, bg=CLR_CARD)
        line2.pack(fill="x", pady=5)
        
        tiers_label = "Fournisseur:" if self.bon_type=="achat" else "Client:"
        lbl(line2, tiers_label, color=CLR_MUTED).pack(side="left", padx=4)
        
        tiers_frame = tk.Frame(line2, bg=CLR_CARD)
        tiers_frame.pack(side="left", padx=4)
        
        self.load_tiers_list()
        self.tiers_var = tk.StringVar()
        self.tiers_combo = combo(tiers_frame, list(self.tiers_map.keys()), width=35, 
                                  textvariable=self.tiers_var)
        self.tiers_combo.pack(side="left")
        self.tiers_combo.bind("<<ComboboxSelected>>", self.on_tiers_change)
        btn_add_tiers = tk.Button(tiers_frame, text="➕", command=self.ajouter_tiers,
                                  bg=CLR_GREEN, fg="white", relief="flat",
                                  font=("Segoe UI", 10, "bold"), width=3,
                                  padx=5, pady=2, cursor="hand2")
        btn_add_tiers.pack(side="left", padx=5)
        
        if self.tiers_map:
            self.tiers_var.set(list(self.tiers_map.keys())[0])
        
        # Lignes spécifiques aux achats
        if self.bon_type == "achat":
            line3 = tk.Frame(header_frame, bg=CLR_CARD)
            line3.pack(fill="x", pady=5)
            lbl(line3, "📅 Date livraison:", color=CLR_MUTED).pack(side="left", padx=4)
            self.date_livraison_var = tk.StringVar(value="")
            entry(line3, width=14, textvariable=self.date_livraison_var).pack(side="left", padx=4)
            
            line4 = tk.Frame(header_frame, bg=CLR_CARD)
            line4.pack(fill="x", pady=5)
            lbl(line4, "📄 N° Facture Fournisseur:", color=CLR_MUTED).pack(side="left", padx=4)
            self.num_facture_fournisseur_var = tk.StringVar(value="")
            entry(line4, width=20, textvariable=self.num_facture_fournisseur_var).pack(side="left", padx=4)
            
            lbl(line4, "🚚 N° BL Fournisseur:", color=CLR_MUTED).pack(side="left", padx=20)
            self.num_bl_fournisseur_var = tk.StringVar(value="")
            entry(line4, width=20, textvariable=self.num_bl_fournisseur_var).pack(side="left", padx=4)
        
        # ========== SECTION SAISIE PRODUITS (COMPRESSÉE) ==========
        saisie_frame = tk.Frame(main_container, bg=CLR_CARD, padx=10, pady=5, relief="groove", bd=1)
        saisie_frame.pack(fill="x", pady=(0, 10))
        
        prod_frame = tk.Frame(saisie_frame, bg=CLR_CARD)
        prod_frame.pack(fill="x")
        
        # Ligne 1: Produit
        lbl(prod_frame, "🛍️ Produit:", color=CLR_MUTED, size=9, bold=True).grid(row=0, column=0, sticky="w", padx=3, pady=2)
        conn = get_conn()
        prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion, 
                            prix_achat, prix_vente, barcode,
                            prix_detail, prix_gros, prix_super_gros, prix_special,
                            tva  -- ✅ AJOUTER LA TVA ICI
                        FROM produits ORDER BY designation""").fetchall()        
        conn.close()
        self.prod_map = {}
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
        
        self.prod_var = tk.StringVar()
        pcb = combo(prod_frame, list(self.prod_map.keys()), width=35, textvariable=self.prod_var)
        pcb.grid(row=0, column=1, padx=3, columnspan=2)
        btn_refresh = tk.Button(prod_frame, text="🔄", command=self.refresh_produits,
                        bg=CLR_ACCENT, fg="white", relief="flat",
                        font=("Segoe UI", 10, "bold"), padx=6, pady=2,
                        cursor="hand2", width=3)
        btn_refresh.grid(row=0, column=3, padx=2, pady=2)

        self.prod_var.trace_add("write", self._on_prod_change)
        
        # Infos produit sur la même ligne
        lbl(prod_frame, "📦", color=CLR_MUTED).grid(row=0, column=3, padx=(10,2))
        self.unite_label = tk.Label(prod_frame, text="", bg=CLR_CARD, fg=CLR_GREEN, 
                                    font=("Segoe UI", 8, "bold"), width=6)
        self.unite_label.grid(row=0, column=4, padx=2)
        
        lbl(prod_frame, "🔄", color=CLR_MUTED).grid(row=0, column=5, padx=2)
        self.facteur_label = tk.Label(prod_frame, text="1", bg=CLR_CARD, fg=CLR_ORANGE,
                                    font=("Segoe UI", 8, "bold"), width=4)
        self.facteur_label.grid(row=0, column=6, padx=2)
        
        # Ligne 2: Code barre et recherche
        lbl(prod_frame, "🔍 Code:", color=CLR_MUTED, size=8).grid(row=1, column=0, sticky="w", padx=3, pady=2)
        self.barcode_var = tk.StringVar()
        self.barcode_entry = entry(prod_frame, width=18, textvariable=self.barcode_var)
        self.barcode_entry.grid(row=1, column=1, padx=3, pady=2)
        self.barcode_entry.bind("<Return>", lambda e: self._search_prod_by_barcode())
        tk.Button(prod_frame, text="Chercher", width=8, command=self._search_prod_by_barcode,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8)).grid(row=1, column=2, padx=3, pady=2)
        
        # Ligne 3: Quantité et Prix
        lbl(prod_frame, "🔢 Qté:", color=CLR_MUTED, size=8).grid(row=2, column=0, sticky="w", padx=3, pady=2)
        self.qty_var = tk.StringVar(value="1")
        entry(prod_frame, width=8, textvariable=self.qty_var, font=("Segoe UI", 9)).grid(row=2, column=1, padx=3, pady=2)

        lbl(prod_frame, "💰 Prix:", color=CLR_MUTED, size=8).grid(row=2, column=2, sticky="w", padx=10, pady=2)
        self.prix_var = tk.StringVar()
        entry(prod_frame, width=12, textvariable=self.prix_var, font=("Segoe UI", 9)).grid(row=2, column=3, padx=3, pady=2)
        # ✅ NOUVEAU : Champ Remise
        lbl(prod_frame, "🏷️ Remise:", color=CLR_MUTED, size=8).grid(row=2, column=4, sticky="w", padx=10, pady=2)
        self.remise_produit_var = tk.StringVar(value="0")
        entry(prod_frame, width=8, textvariable=self.remise_produit_var, font=("Segoe UI", 9)).grid(row=2, column=5, padx=3, pady=2)
        lbl(prod_frame, "%", color=CLR_MUTED, size=8).grid(row=2, column=6, sticky="w", padx=2, pady=2)
        # ✅ Bouton AJOUTER (sans remise) - prend la remise du champ
        btn_ajouter = tk.Button(prod_frame, text="➕ AJOUTER", command=lambda: self.add_ligne(False),
                                bg=CLR_GREEN, fg="white", relief="raised",
                                font=("Segoe UI", 9, "bold"), padx=12, pady=3, cursor="hand2")
        btn_ajouter.grid(row=2, column=7, padx=5, pady=2)

        # ✅ Bouton AJOUTER AVEC REMISE (demande la remise)
        btn_ajouter_remise = tk.Button(prod_frame, text="➕ Remise", command=lambda: self.add_ligne(True),
                                        bg=CLR_ORANGE, fg="white", relief="raised",
                                        font=("Segoe UI", 9, "bold"), padx=12, pady=3, cursor="hand2")
        btn_ajouter_remise.grid(row=2, column=8, padx=5, pady=2)
        # Sélecteur de prix uniquement pour les VENTES - CORRECTION ICI
        if self.bon_type == "vente":
            selector_frame = tk.Frame(prod_frame, bg=CLR_CARD)
            selector_frame.grid(row=3, column=0, columnspan=7, sticky="ew", pady=5)

            # Référence à l'instance pour la méthode on_tiers_change
            self.prix_selector = prix_niveaux.PrixSelectorWidget(
                selector_frame,
                prix_var=self.prix_var,
                client_id_fn=self._get_client_id
            )
            self.prix_selector.pack(fill="x")
        
        # ========== SECTION TABLEAU + BOUTONS ==========
        content_frame = tk.Frame(main_container, bg=CLR_BG)
        content_frame.pack(fill="both", expand=True)
        
        # Tableau à gauche
        tableau_frame = tk.LabelFrame(content_frame, text="📋 Lignes du Bon", bg=CLR_CARD, 
                                      fg=CLR_GREEN, font=("Segoe UI", 10, "bold"),
                                      padx=10, pady=10)
        tableau_frame.pack(side="left", fill="both", expand=True)
        
        cols = ["Produit", "Quantité", "Unité", "Prix Unit.", "Remise %", "Total HT", "TVA", "Total TTC"]
        widths = [250, 70, 50, 80, 70, 90, 70, 110]
        tf, self.tree = make_tree(tableau_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # ========== PANEL DES BOUTONS À DROITE ==========
        panel_droite = tk.Frame(content_frame, bg=CLR_BG, width=320)  # 🟢 LÉGÈREMENT PLUS LARGE
        panel_droite.pack(side="right", fill="y", padx=(5, 0))
        panel_droite.pack_propagate(False)

        # ============================================================
        # 1. SECTION ACTIONS
        # ============================================================
        actions_frame = tk.LabelFrame(panel_droite, text="⚡ ACTIONS", 
                                    bg=CLR_CARD, fg=CLR_ACCENT,
                                    font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=8)
        actions_frame.pack(fill="x", padx=5, pady=5)

        # Boutons actions sur une ligne
        btn_line1 = tk.Frame(actions_frame, bg=CLR_CARD)
        btn_line1.pack(fill="x", pady=2)

        tk.Button(btn_line1, text="🗑 Retirer", command=self.remove_ligne,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        tk.Button(btn_line1, text="💵 Modifier Prix", command=self.modifier_prix_produit,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        tk.Button(btn_line1, text="✏ Modifier Qté", command=self.modifier_quantite,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)

        tk.Button(btn_line1, text="🗑 Vider", command=self.vider_panier,
                bg=CLR_BORDER, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        # Dans la section ACTIONS, après les autres boutons
        tk.Button(btn_line1, text="💰 Remise", command=self.modifier_remise_produit,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        # ============================================================
        # 2. SECTION REMISE (seulement pour les ventes)
        # ============================================================
        if self.bon_type == "vente":
            remise_frame = tk.LabelFrame(panel_droite, text="🏷️ REMISE", 
                                        bg=CLR_CARD, fg=CLR_ORANGE,
                                        font=("Segoe UI", 10, "bold"),
                                        padx=10, pady=8)
            remise_frame.pack(fill="x", padx=5, pady=5)
            
            # Type de remise
            type_frame = tk.Frame(remise_frame, bg=CLR_CARD)
            type_frame.pack(fill="x", pady=2)
            
            tk.Label(type_frame, text="Type:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=2)
            
            self.remise_type_var = tk.StringVar(value="aucune")
            
            rb_aucune = tk.Radiobutton(type_frame, text="Aucune", 
                                    variable=self.remise_type_var,
                                    value="aucune", bg=CLR_CARD, fg=CLR_TEXT,
                                    selectcolor=CLR_INPUT, relief="flat",
                                    activebackground=CLR_CARD,
                                    font=("Segoe UI", 8), cursor="hand2")
            rb_aucune.pack(side="left", padx=5)
            rb_aucune.configure(command=self.appliquer_remise)
            
            rb_pourcent = tk.Radiobutton(type_frame, text="%", 
                                        variable=self.remise_type_var,
                                        value="pourcentage", bg=CLR_CARD, fg=CLR_TEXT,
                                        selectcolor=CLR_INPUT, relief="flat",
                                        activebackground=CLR_CARD,
                                        font=("Segoe UI", 8), cursor="hand2")
            rb_pourcent.pack(side="left", padx=5)
            rb_pourcent.configure(command=self.appliquer_remise)
            
            rb_montant = tk.Radiobutton(type_frame, text="Montant", 
                                        variable=self.remise_type_var,
                                        value="montant", bg=CLR_CARD, fg=CLR_TEXT,
                                        selectcolor=CLR_INPUT, relief="flat",
                                        activebackground=CLR_CARD,
                                        font=("Segoe UI", 8), cursor="hand2")
            rb_montant.pack(side="left", padx=5)
            rb_montant.configure(command=self.appliquer_remise)
            
            # Valeur et motif sur la même ligne
            value_frame = tk.Frame(remise_frame, bg=CLR_CARD)
            value_frame.pack(fill="x", pady=2)
            
            tk.Label(value_frame, text="Valeur:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=2)
            
            self.remise_valeur_var = tk.StringVar(value="0")
            entry_remise = entry(value_frame, width=8, textvariable=self.remise_valeur_var,
                                font=("Segoe UI", 9))
            entry_remise.pack(side="left", padx=3)
            entry_remise.bind("<KeyRelease>", lambda e: self.appliquer_remise())
            
            tk.Label(value_frame, text="Motif:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=(10, 2))
            
            self.remise_motif_var = tk.StringVar(value="")
            entry_motif = entry(value_frame, width=12, textvariable=self.remise_motif_var,
                                font=("Segoe UI", 8))
            entry_motif.pack(side="left", padx=3, fill="x", expand=True)
            entry_motif.bind("<KeyRelease>", lambda e: self.appliquer_remise())
            
            # Bouton appliquer
            btn_remise = tk.Button(remise_frame, text="✅ Appliquer Remise",
                                command=self.appliquer_remise,
                                bg=CLR_ORANGE, fg="white", relief="flat",
                                font=("Segoe UI", 8, "bold"), padx=10, pady=3,
                                cursor="hand2")
            btn_remise.pack(pady=3)

        # ============================================================
        # 3. SECTION RÉCAPITULATIF
        # ============================================================
        recap_frame = tk.LabelFrame(panel_droite, text="📊 RÉCAPITULATIF", 
                                    bg=CLR_CARD, fg=CLR_GREEN,
                                    font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=8)
        recap_frame.pack(fill="x", padx=5, pady=5)

        # Total HT
        row_ht = tk.Frame(recap_frame, bg=CLR_CARD)
        row_ht.pack(fill="x", pady=2)
        tk.Label(row_ht, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        self.total_ht_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_ht, textvariable=self.total_ht_var, bg=CLR_CARD, 
                fg=CLR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right")

        # TVA
        row_tva = tk.Frame(recap_frame, bg=CLR_CARD)
        row_tva.pack(fill="x", pady=2)
        tk.Label(row_tva, text="TVA:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        self.tva_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_tva, textvariable=self.tva_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 9, "bold")).pack(side="right")

        # Remise (seulement si appliquée)
        self.remise_affichage_var = tk.StringVar(value="")
        row_remise = tk.Frame(recap_frame, bg=CLR_CARD)
        row_remise.pack(fill="x", pady=2)
        tk.Label(row_remise, text="Remise:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row_remise, textvariable=self.remise_affichage_var, bg=CLR_CARD, 
                fg=CLR_RED, font=("Segoe UI", 9, "bold")).pack(side="right")

        # Séparateur
        sep_recap = tk.Frame(recap_frame, bg=CLR_BORDER, height=1)
        sep_recap.pack(fill="x", pady=4)

        # Total TTC (en gras)
        row_ttc = tk.Frame(recap_frame, bg=CLR_CARD)
        row_ttc.pack(fill="x", pady=2)
        tk.Label(row_ttc, text="⭐ TOTAL TTC:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 10, "bold")).pack(side="left")
        self.total_ttc_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_ttc, textvariable=self.total_ttc_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 13, "bold")).pack(side="right")

        # ============================================================
        # 4. SECTION BOUTONS FINAUX
        # ============================================================
        btn_final_frame = tk.Frame(panel_droite, bg=CLR_BG)
        btn_final_frame.pack(fill="x", padx=5, pady=5)

        # Ligne 1: Valider et Annuler
        btn_line2 = tk.Frame(btn_final_frame, bg=CLR_BG)
        btn_line2.pack(fill="x", pady=2)

        tk.Button(btn_line2, text="✅ Valider", command=self.save,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"), padx=15, pady=8,
                cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        tk.Button(btn_line2, text="❌ Annuler", command=self.destroy,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"), padx=15, pady=8,
                cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        # Ligne 2: Ticket (seulement pour les ventes)
        if self.bon_type == "vente":
            btn_line3 = tk.Frame(btn_final_frame, bg=CLR_BG)
            btn_line3.pack(fill="x", pady=2)
            
            tk.Button(btn_line3, text="🖨 Ticket", command=self.imprimer_ticket_rapide,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                    cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")
            
            tk.Button(btn_line3, text="📄 Facture", command=self.creer_facture_rapide,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                    cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        # Raccourcis clavier
        shortcuts_frame = tk.Frame(panel_droite, bg=CLR_BG)
        shortcuts_frame.pack(fill="x", pady=5)
        shortcuts_label = tk.Label(shortcuts_frame, 
                                text="Entrée (Ajouter) | Suppr (Retirer) | F11 (Plein écran)", 
                                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 7))
        shortcuts_label.pack()

        # Bindings des raccourcis clavier
        self.bind('<Return>', lambda e: self.add_ligne())
        self.bind('<Delete>', lambda e: self.remove_ligne())
        if self.prod_map:
            self.prod_var.set(list(self.prod_map.keys())[0])
    def refresh_produits(self):
        """✅ Rafraîchit la liste des produits dans le combobox"""
        print(f"🔄 BonDialog.refresh_produits() appelé !")  # DEBUG
        
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion, 
                                prix_achat, prix_vente, barcode,
                                prix_detail, prix_gros, prix_super_gros, prix_special,
                                tva
                            FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        # Sauvegarder l'ancienne sélection
        old_selection = self.prod_var.get() if hasattr(self, 'prod_var') else ""
        
        # Mettre à jour le dictionnaire des produits
        self.prod_map = {}
        new_prod_list = []
        
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
            new_prod_list.append(key)
        
        print(f"📦 Nouveaux produits: {len(new_prod_list)}")  # DEBUG
        
        # ✅ MÉTHODE SIMPLIFIÉE : Mettre à jour directement la combobox
        self._update_combobox_produits(new_prod_list, old_selection)
        
        # Mettre à jour les informations du produit sélectionné
        if old_selection in self.prod_map:
            p = self.prod_map[old_selection]
            unite = p["unite"] if p["unite"] else "Pcs"
            if hasattr(self, 'unite_label'):
                self.unite_label.config(text=unite)
            facteur = p["facteur_conversion"] if p["facteur_conversion"] else 1
            if hasattr(self, 'facteur_label'):
                self.facteur_label.config(text=f"{facteur:.0f}")
            
            if hasattr(self, 'prix_selector'):
                self.prix_selector.set_produit(p)
            else:
                if self.bon_type == "achat":
                    px = p.get("prix_achat", 0)
                else:
                    px = p.get("prix_detail") or p.get("prix_vente", 0)
                self.prix_var.set(str(px))
        elif new_prod_list:
            self.prod_var.set(new_prod_list[0])
        
        # ✅ Si un nouveau produit a été ajouté, afficher un message discret
        if old_selection != self.prod_var.get() and new_prod_list:
            self._afficher_notification("✅ Nouveau produit disponible !")
    
    def _update_combobox_produits(self, new_prod_list, old_selection):
        """✅ Met à jour la combobox des produits - VERSION SIMPLIFIÉE"""
        # Méthode 1: Chercher dans la structure de la fenêtre
        # On parcourt tous les widgets pour trouver le combobox
        def find_and_update(widget):
            if isinstance(widget, ttk.Combobox):
                # Vérifier si c'est la combobox des produits
                # On vérifie si les valeurs ressemblent à des produits
                if widget['values'] and len(widget['values']) > 0:
                    # Vérifier si le premier élément contient " - " (format produit)
                    if " - " in str(widget['values'][0]):
                        widget['values'] = new_prod_list
                        if old_selection in new_prod_list:
                            self.prod_var.set(old_selection)
                        elif new_prod_list:
                            self.prod_var.set(new_prod_list[0])
                        return True
            return False
        
        # Parcourir récursivement tous les widgets
        def traverse(widget):
            if find_and_update(widget):
                return True
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if traverse(child):
                        return True
            return False
        
        traverse(self)
        
        # ✅ MÉTHODE 2: Si la première méthode échoue, forcer la mise à jour
        # Chercher le combobox dans le frame 'prod_frame'
        for child in self.winfo_children():
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_children'):
                        for grandchild in subchild.winfo_children():
                            if isinstance(grandchild, ttk.Combobox):
                                if grandchild['values'] and len(grandchild['values']) > 0:
                                    # Si les valeurs contiennent " - ", c'est probablement la bonne
                                    if " - " in str(grandchild['values'][0]):
                                        grandchild['values'] = new_prod_list
                                        if old_selection in new_prod_list:
                                            self.prod_var.set(old_selection)
                                        elif new_prod_list:
                                            self.prod_var.set(new_prod_list[0])
                                        return
    
    def _afficher_notification(self, message):
        """Affiche une notification temporaire dans la fenêtre"""
        # Créer un label de notification qui disparaît après 3 secondes
        notification = tk.Label(self, text=message, bg=CLR_GREEN, fg="white",
                               font=("Segoe UI", 10, "bold"), padx=20, pady=10)
        notification.place(relx=0.5, rely=0.02, anchor="n")
        self.after(3000, notification.destroy)  
    def _get_client_id(self):
        """Retourne l'ID du client sélectionné pour les prix spéciaux"""
        if not hasattr(self, 'tiers_var') or not self.tiers_var.get():
            return None
        if self.bon_type != "vente":
            return None
        tiers_nom = self.tiers_var.get()
        if hasattr(self, 'tiers_map') and tiers_nom in self.tiers_map:
            return self.tiers_map[tiers_nom]
        return None
    def modifier_quantite(self):
        """Modifier la quantité d'une ligne sélectionnée"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne à modifier")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]
        
        # ✅ Fenêtre de dialogue dédiée
        dlg = tk.Toplevel(self)
        dlg.title("Modifier la quantité")
        dlg.configure(bg=CLR_BG)
        dlg.geometry("400x300")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        center_window(dlg, 400, 300)
        
        main_frame = tk.Frame(dlg, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏️ Modifier la quantité", 12, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # Informations du produit
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=5)
        
        facteur = ligne.get("facteur", 1)
        qte_affichee = ligne["quantite"] 
        # facteur if facteur else ligne["quantite"]
        
        lbl(info_frame, f"Produit: {ligne['designation']}", 10, True, CLR_TEXT).pack(anchor="w")
        lbl(info_frame, f"Quantité actuelle: {qte_affichee:.2f} {ligne.get('unite', 'Pcs')}", 9, False, CLR_MUTED).pack(anchor="w")
        lbl(info_frame, f"Prix unitaire: {ligne['prix']:.2f} DA", 9, False, CLR_MUTED).pack(anchor="w")
        
        # Champ de saisie
        input_frame = tk.Frame(main_frame, bg=CLR_BG)
        input_frame.pack(fill="x", pady=10)
        
        lbl(input_frame, "Nouvelle quantité:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        new_qty_var = tk.StringVar(value=str(qte_affichee))
        entry_qty = entry(input_frame, width=12, textvariable=new_qty_var, font=("Segoe UI", 11, "bold"))
        entry_qty.pack(side="left", padx=10)
        entry_qty.focus_set()
        entry_qty.select_range(0, tk.END)
        
        # ✅ Message de statut (au lieu de messagebox)
        status_var = tk.StringVar(value="")
        status_label = tk.Label(main_frame, textvariable=status_var, bg=CLR_BG, 
                            fg=CLR_GREEN, font=("Segoe UI", 9, "bold"))
        status_label.pack(pady=5)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        def valider_modification():
            try:
                nouvelle_qty = parse_decimal(new_qty_var.get())
                if nouvelle_qty <= 0:
                    status_var.set("❌ La quantité doit être > 0")
                    status_label.config(fg=CLR_RED)
                    return
            except ValueError:
                status_var.set("❌ Quantité invalide")
                status_label.config(fg=CLR_RED)
                return
            
            # Mettre à jour la ligne
            facteur_ligne = ligne.get("facteur", 1)
            nouvelle_qty_base = nouvelle_qty * facteur_ligne
            ligne["quantite"] = nouvelle_qty
            ligne["quantite_base"] = nouvelle_qty_base
            ligne["total"] = nouvelle_qty_base * ligne["prix"]
            
            # ✅ Rafraîchir la treeview principale AVANT de fermer
            self._refresh_tree()
            
            # ✅ Afficher le succès dans le label avant de fermer
            status_var.set(f"✅ Quantité mise à jour: {nouvelle_qty:.2f}")
            status_label.config(fg=CLR_GREEN)
            
            # ✅ Fermer après un court délai pour que l'utilisateur voie le message
            self.after(500, dlg.destroy)
        
        def annuler_modification():
            dlg.destroy()
        
        # Bind Entrée pour valider
        entry_qty.bind('<Return>', lambda e: valider_modification())
        entry_qty.bind('<Escape>', lambda e: annuler_modification())
        
        tk.Button(btn_frame, text="✅ Valider (Entrée)", command=valider_modification,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ Annuler (Echap)", command=annuler_modification,
                bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
    
    def modifier_prix_produit(self):
        """Modifier le prix unitaire d'une ligne et recalculer total/TVA/TTC"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]

        nouveau_prix = simpledialog.askfloat(
            "💵 Modifier le prix",
            f"Produit: {ligne['designation']}\n"
            f"Prix actuel: {ligne['prix']:.2f} DA\n\n"
            f"Nouveau prix unitaire (DA):",
            initialvalue=ligne['prix'],
            minvalue=0.01,
            parent=self
        )
        if nouveau_prix is None:
            return
        if nouveau_prix <= 0:
            messagebox.showerror("Erreur", "Le prix doit être > 0")
            return

        # Mettre à jour le prix de base
        ligne["prix"] = nouveau_prix

        # Recalculer en tenant compte d'une éventuelle remise
        remise = ligne.get("remise_produit", 0)
        if remise > 0:
            prix_remise = nouveau_prix * (1 - remise / 100)
        else:
            prix_remise = nouveau_prix

        qte_base = ligne.get("quantite_base", ligne["quantite"])
        total_ht_brut = qte_base * nouveau_prix
        total_ht = qte_base * prix_remise

        ligne["prix_remise"] = prix_remise
        ligne["total_ht_brut"] = total_ht_brut
        ligne["remise_montant"] = total_ht_brut - total_ht
        ligne["total_ht"] = total_ht
        ligne["total"] = total_ht

        tva_taux = ligne.get("tva", 0)
        ligne["total_tva"] = total_ht * tva_taux / 100
        ligne["total_ttc"] = total_ht + ligne["total_tva"]

        # ✅ Recalcule immédiatement le total du bon (HT/TVA/TTC)
        self._refresh_tree()

        messagebox.showinfo("Succès",
            f"✅ Prix mis à jour: {nouveau_prix:.2f} DA\n"
            f"Nouveau total ligne: {total_ht:,.2f} DA")
    def load_tiers_list(self):
        conn = get_conn()
        try:
            if self.bon_type == "achat":
                tiers = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            else:
                tiers = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
        finally:
            conn.close()
        self.tiers_map = {r["nom"]: r["id"] for r in tiers}
        self.tiers_list = list(self.tiers_map.keys())

    def ajouter_tiers(self):
        if self.bon_type == "achat":
            dialog = TiersDialog(self, "fournisseur", data=None)
        else:
            dialog = TiersDialog(self, "client", data=None)
        self.wait_window(dialog)
        self.load_tiers_list()
        self.tiers_combo['values'] = self.tiers_list
        if self.tiers_list:
            self.tiers_var.set(self.tiers_list[-1])
            messagebox.showinfo("Succès", f"{'Fournisseur' if self.bon_type=='achat' else 'Client'} ajouté avec succès !")

    def _search_prod_by_barcode(self):
        raw = self.barcode_var.get().strip()
        if not raw:
            messagebox.showwarning("Recherche code-barre", "Entrez un code-barre à rechercher")
            return
        normalized = normalize_barcode_input(raw)
        if not normalized:
            messagebox.showwarning("Recherche code-barre", "Code-barre invalide après normalisation")
            return
        conn = get_conn()
        try:
            produit = conn.execute("SELECT * FROM produits WHERE barcode = ? OR code = ?", (normalized, normalized)).fetchone()
            if not produit:
                produit = conn.execute("SELECT * FROM produits WHERE barcode LIKE ? OR code LIKE ? LIMIT 1", (f"%{normalized}%", f"%{normalized}%")).fetchone()
        finally:
            conn.close()
        if produit:
            display_key = f"{produit['code']} - {produit['designation']}"
            if display_key in self.prod_map:
                self.prod_var.set(display_key)
            else:
                self.prod_map[display_key] = dict(produit)
                self.prod_var.set(display_key)
            px = produit['prix_achat'] if self.bon_type == 'achat' else produit['prix_vente']
            self.prix_var.set(str(px))
            self.qty_var.set('1')
            messagebox.showinfo("Produit trouvé", f"Produit trouvé: {produit['designation']}")
        else:
            messagebox.showinfo("Non trouvé", f"Aucun produit trouvé pour: {normalized}")

    def _on_prod_change(self, *a):
        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            unite = p["unite"] if p["unite"] else "Pcs"
            self.unite_label.config(text=unite)
            facteur = p["facteur_conversion"] if p["facteur_conversion"] else 1
            self.facteur_label.config(text=f"{facteur:.0f}")

            if hasattr(self, 'prix_selector'):
                self.prix_selector.set_produit(p)
            else:
                if self.bon_type == "achat":
                    px = p.get("prix_achat", 0)
                else:
                    px = p.get("prix_detail") or p.get("prix_vente", 0)
                self.prix_var.set(str(px))
            
            # ✅ Réinitialiser la remise quand on change de produit
            if hasattr(self, 'remise_produit_var'):
                self.remise_produit_var.set("0")

    def on_tiers_change(self, event=None):
        """Met à jour le numéro de bon ET le niveau de prix quand le client change"""
        tiers_nom = self.tiers_var.get()
        if tiers_nom in self.tiers_map:
            tiers_id = self.tiers_map[tiers_nom]
            prefix = "BA" if self.bon_type == "achat" else "BV"
            self.num_var.set(next_numero_tiers(prefix, tiers_id))
        
        # Mise à jour des prix (logique existante)
        if self.bon_type != "vente":
            return
        if not hasattr(self, 'prix_selector'):
            return
        
        key = self.prod_var.get()
        if key and key in self.prod_map:
            self.prix_selector.client_id_fn = self._get_client_id
            self.prix_selector.set_produit(self.prod_map[key])

    def add_ligne(self, demander_remise=False):
        """
        Ajoute une ligne au panier
        demander_remise: True = demande la remise, False = utilise la valeur du champ
        """
        key = self.prod_var.get()
        if key not in self.prod_map:
            messagebox.showerror("Erreur", "Produit invalide")
            return
        try:
            qty = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide")
            return
        
        if qty <= 0:
            messagebox.showerror("Erreur", "Quantité doit être > 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix doit être > 0")
            return
        
        prod = self.prod_map[key]
        facteur = prod["facteur_conversion"] if prod["facteur_conversion"] else 1
        unite = prod["unite"] if prod["unite"] else "Pcs"
        
        # ✅ Quantité en unité de base (pour le stock)
        quantite_en_unite_base = qty * facteur
        
        # ✅ Calcul du total HT brut (sans remise) en unité de base
        total_ht_brut = quantite_en_unite_base * prix
        
        # ✅ TVA RÉELLE du produit
        tva_taux = float(prod.get("tva") or 0)
        
        # ✅ Gestion de la remise
        remise_produit = 0
        
        if demander_remise:
            # ✅ BOUTON "Ajouter avec remise" → demande la remise
            remise_input = simpledialog.askfloat(
                "💰 Remise sur ce produit",
                f"Entrez le pourcentage de remise pour '{key}':\n\n"
                f"Prix unitaire: {prix:.2f} DA\n"
                f"Quantité: {qty:.2f}\n"
                f"Facteur de conversion: {facteur}\n"
                f"Quantité en unité de base: {quantite_en_unite_base:.2f}\n"
                f"Total HT brut: {total_ht_brut:,.2f} DA\n\n"
                f"Remise (%):",
                minvalue=0,
                maxvalue=100,
                parent=self
            )
            if remise_input is None:
                return
            if remise_input > 0:
                remise_produit = remise_input
        else:
            # ✅ BOUTON "AJOUTER" normal → utilise la valeur du champ
            try:
                remise_produit = parse_decimal(self.remise_produit_var.get() or "0")
                if remise_produit < 0 or remise_produit > 100:
                    messagebox.showerror("Erreur", "La remise doit être entre 0 et 100%")
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Remise invalide")
                return
        
        # ✅ Calcul avec remise
        if remise_produit > 0:
            prix_remise = prix * (1 - remise_produit / 100)
            total_ht = quantite_en_unite_base * prix_remise
            remise_montant = total_ht_brut - total_ht
        else:
            prix_remise = prix
            total_ht = total_ht_brut
            remise_montant = 0
        
        total_tva = total_ht * tva_taux / 100
        total_ttc = total_ht + total_tva

        # ✅ VÉRIFIER SI LE PRODUIT EXISTE DÉJÀ
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                # ✅ Calculer la quantité actuelle en unité d'affichage
                qty_actuelle = ligne["quantite"] / ligne["facteur"] if ligne["facteur"] else ligne["quantite"]
                
                reponse = messagebox.askyesno(
                    "Produit déjà ajouté",
                    f"Le produit '{key}' est déjà dans le bon.\n"
                    f"Quantité actuelle: {qty_actuelle:.2f}\n"
                    f"Nouvelle quantité: {qty:.2f}\n\n"
                    f"Voulez-vous CUMULER les quantités ?"
                )
                if reponse:
                    # ✅ CUMULER CORRECTEMENT avec le facteur de conversion
                    # Mettre à jour la quantité affichée (en cartons/kg)
                    ligne["quantite"] += qty
                    # Mettre à jour la quantité en unité de base
                    ligne["quantite_base"] += quantite_en_unite_base
                    
                    # ✅ Recalculer les totaux avec la nouvelle quantité totale
                    quantite_base_totale = ligne["quantite_base"]
                    
                    # ✅ Calculer le nouveau total HT avec remise
                    if ligne.get("remise_produit", 0) > 0:
                        # Si le produit a une remise, l'appliquer sur le total
                        prix_remise_cumule = ligne["prix"] * (1 - ligne["remise_produit"] / 100)
                        ligne["total_ht"] = quantite_base_totale * prix_remise_cumule
                        ligne["prix_remise"] = prix_remise_cumule
                        ligne["remise_montant"] = (quantite_base_totale * ligne["prix"]) - ligne["total_ht"]
                    else:
                        # Sans remise
                        ligne["total_ht"] = quantite_base_totale * ligne["prix"]
                    
                    # ✅ Recalculer TVA et TTC
                    tva_taux_ligne = ligne.get("tva", 0)
                    ligne["total_tva"] = ligne["total_ht"] * tva_taux_ligne / 100
                    ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]
                    ligne["total"] = ligne["total_ht"]
                    
                    # ✅ Mettre à jour le prix_remise si la remise est active
                    if ligne.get("remise_produit", 0) > 0:
                        if ligne["quantite_base"] > 0:
                            ligne["prix_remise"] = ligne["total_ht"] / ligne["quantite_base"]
                    
                    messagebox.showinfo("Succès", 
                        f"✅ Quantité mise à jour\n"
                        f"Nouvelle quantité: {ligne['quantite']:.2f}\n"
                        f"Nouveau total: {ligne['total_ht']:,.2f} DA")
                else:
                    messagebox.showinfo("Info", "Ajout annulé")
                self._refresh_tree()
                self.qty_var.set("1")
                self.prix_var.set("")
                self.remise_produit_var.set("0")
                return

        # ✅ NOUVEAU PRODUIT
        self.lignes.append({
            "produit_id":    prod["id"],
            "designation":   key,
            "barcode":       prod.get("barcode", ""),
            "quantite":      qty,  # ✅ Quantité en unité d'affichage (cartons)
            "unite":         unite,
            "facteur":       facteur,
            "quantite_base": quantite_en_unite_base,  # ✅ Quantité en unité de stock
            "prix":          prix,
            "prix_remise":   prix_remise,
            "remise_produit": remise_produit,
            "remise_montant": remise_montant,
            "total_ht_brut": total_ht_brut,
            "total_ht":      total_ht,
            "tva":           tva_taux,
            "total_tva":     total_tva,
            "total_ttc":     total_ttc,
            "total":         total_ht,
        })
        self._refresh_tree()
        
        # ✅ Réinitialiser les champs
        self.qty_var.set("1")
        self.prix_var.set("")
        self.remise_produit_var.set("0")
        
        if demander_remise and remise_produit > 0:
            messagebox.showinfo("Succès", 
                            f"✅ Produit ajouté avec remise de {remise_produit:.0f}%\n"
                            f"Nouveau prix: {prix_remise:.2f} DA")

    def remove_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne à supprimer")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_tree()
    def vider_panier(self):
        """Vider toutes les lignes du panier"""
        if not self.lignes:
            messagebox.showinfo("Information", "Le panier est déjà vide")
            return
        
        if messagebox.askyesno("Confirmation", 
                            "⚠️ Vider tout le panier ?\n\n"
                            "Toutes les lignes seront supprimées."):
            self.lignes = []
            self._refresh_tree()
            
            # Réinitialiser la remise
            if hasattr(self, 'remise_type_var'):
                self.remise_type_var.set("aucune")
            if hasattr(self, 'remise_valeur_var'):
                self.remise_valeur_var.set("0")
            if hasattr(self, 'remise_motif_var'):
                self.remise_motif_var.set("")
            
            # Réappliquer la remise (pour remettre à zéro)
            if hasattr(self, 'appliquer_remise'):
                self.appliquer_remise()
            
            messagebox.showinfo("Succès", "🗑 Panier vidé avec succès")
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        total_ht = 0
        total_tva = 0
        total_ttc = 0
        total_remise = 0
        
        for i, l in enumerate(self.lignes):
            facteur = l.get("facteur", 1) or 1
            # Utiliser la quantité en unité de base pour les calculs
            qte_base = l.get("quantite_base", l["quantite"])
            qte_carton = l["quantite"]
            
            # Quantité affichée (avec cartons)
            qty_display = l["quantite"] 
            qty_text = f"{qty_display:.2f}" if facteur > 1 else f"{qty_display:.2f}"
            
            tva_taux = l.get("tva", 0)
            # ✅ PRIX ORIGINAL (avant remise) pour l'affichage
            prix_original = l["prix"]  # Le prix original sans remise
            
            # ✅ PRIX AVEC REMISE pour le calcul du total
            prix_remise = l.get("prix_remise", l["prix"])
            
            # Calculer le HT en utilisant la quantité de base
            ht_ligne = qte_base * prix_remise
            remise = l.get("remise_produit", 0)
            remise_montant = l.get("remise_montant", 0)
            
            remise_affichage = f"{remise:.0f}%" if remise > 0 else "-"
            
            tva_ligne = ht_ligne * tva_taux / 100
            ttc_ligne = ht_ligne + tva_ligne
            
            self.tree.insert("", "end", iid=str(i),
                values=(
                    l["designation"], 
                    qty_text,
                    l.get("unite", "Pcs"),
                    f"{prix_original:.2f}",
                    remise_affichage,
                    f"{ht_ligne:.2f}",
                    f"{tva_taux:.0f}%",
                    f"{ttc_ligne:.2f}"
                ))
            
            total_ht += ht_ligne
            total_tva += tva_ligne
            total_ttc += ttc_ligne
            total_remise += remise_montant
            
            # Mettre à jour les valeurs dans la ligne
            l["total_ht"] = ht_ligne
            l["total_tva"] = tva_ligne
            l["total_ttc"] = ttc_ligne
        
        # Mise à jour des totaux
        if self.bon_type == "achat":
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            self.tva_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
        else:
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            if total_remise > 0:
                self.tva_var.set(f"Remises: {total_remise:,.2f} DA")
            else:
                self.tva_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
    def appliquer_remise(self, event=None):
        """Appliquer une remise sur le total en tenant compte du facteur de conversion"""
        if self.bon_type != "vente":
            return
        
        # Calculer le total HT en tenant compte du facteur de conversion
        total_ht = 0
        for l in self.lignes:
            # Utiliser la quantité en unité de base (facteur * quantité)
            qte_base = l.get("quantite_base", l["quantite"])
            prix = l.get("prix_remise", l["prix"])
            ht_ligne = qte_base * prix
            total_ht += ht_ligne
        
        self.total_avant_remise = total_ht
        
        if not self.lignes:
            self.total_ht_var.set("0.00 DA")
            self.tva_var.set("0.00 DA")
            self.total_ttc_var.set("0.00 DA")
            return
        
        remise_type = self.remise_type_var.get()
        try:
            remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
        except ValueError:
            remise_valeur = 0
        
        self.remise_type = remise_type
        self.remise_valeur = remise_valeur
        
        # Calculer le total après remise
        if remise_type == "aucune" or remise_valeur <= 0:
            total_apres = total_ht
            remise_montant = 0
            self.remise_appliquee = False
        elif remise_type == "pourcentage":
            remise_montant = total_ht * remise_valeur / 100
            total_apres = total_ht - remise_montant
            self.remise_appliquee = True
        else:  # montant fixe
            remise_montant = min(remise_valeur, total_ht)
            total_apres = total_ht - remise_montant
            self.remise_appliquee = True
        
        self.total_apres_remise = total_apres
        
        # Mettre à jour l'affichage avec le TTC (si TVA)
        total_ttc = total_apres
        
        self.total_ht_var.set(f"{total_apres:,.2f} DA")
        
        if self.remise_appliquee:
            remise_text = f"{remise_montant:,.2f} DA"
            if remise_type == "pourcentage":
                remise_text = f"{remise_valeur:.1f}% ({remise_montant:,.2f} DA)"
            self.tva_var.set(f"Remise: {remise_text}")
            self.total_ttc_var.set(f"{total_apres:,.2f} DA")
            
            self.remise_motif = self.remise_motif_var.get().strip()
        else:
            self.tva_var.set("0.00 DA")
            self.total_ttc_var.set(f"{total_apres:,.2f} DA")
    def modifier_remise_produit(self):
        """Modifier la remise d'un produit sélectionné"""
        if self.bon_type != "vente":
            messagebox.showinfo("Information", "La remise est uniquement disponible pour les ventes")
            return
        
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        
        idx = int(sel[0])
        ligne = self.lignes[idx]
        
        remise_actuelle = ligne.get('remise_produit', 0)
        
        nouvelle_remise = simpledialog.askfloat(
            "💰 Modifier la remise",
            f"Produit: {ligne['designation']}\n"
            f"Prix unitaire original: {ligne['prix']:.2f} DA\n"
            f"Prix actuel: {ligne.get('prix_remise', ligne['prix']):.2f} DA\n"
            f"Remise actuelle: {remise_actuelle:.1f}%\n\n"
            f"Nouvelle remise (%):",
            initialvalue=remise_actuelle,
            minvalue=0,
            maxvalue=100,
            parent=self
        )
        
        if nouvelle_remise is None:
            return
        
        if nouvelle_remise < 0 or nouvelle_remise > 100:
            messagebox.showerror("Erreur", "La remise doit être entre 0 et 100%")
            return
        
        # ✅ Recalculer avec la nouvelle remise
        prix_original = ligne['prix']
        prix_remise = prix_original * (1 - nouvelle_remise / 100)
        total_ht_brut = ligne['quantite_base'] * prix_original
        total_ht = ligne['quantite_base'] * prix_remise
        remise_montant = total_ht_brut - total_ht
        
        # ✅ Mettre à jour la ligne
        ligne['remise_produit'] = nouvelle_remise
        ligne['prix_remise'] = prix_remise
        ligne['total_ht'] = total_ht
        ligne['remise_montant'] = remise_montant
        ligne['total_ht_brut'] = total_ht_brut
        
        # ✅ Recalculer TVA et TTC
        tva_taux = ligne.get('tva', 0)
        ligne['total_tva'] = total_ht * tva_taux / 100
        ligne['total_ttc'] = total_ht + ligne['total_tva']
        
        self._refresh_tree()
        messagebox.showinfo("Succès", 
                        f"✅ Remise mise à jour: {nouvelle_remise:.1f}%\n"
                        f"Nouveau prix: {prix_remise:.2f} DA\n"
                        f"Nouveau total: {total_ht:,.2f} DA")  
    def imprimer_ticket_rapide(self):
        """Afficher un aperçu du ticket de caisse"""
        if not self.lignes:
            messagebox.showwarning("Avertissement", "Le panier est vide")
            return
        
        # Calculer le total
        total = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        total_tva = sum(l.get("total_tva", 0) for l in self.lignes)
        
        # Vérifier s'il y a une remise globale
        remise_globale = 0
        remise_type = ""
        remise_valeur = 0
        
        if hasattr(self, 'remise_appliquee') and self.remise_appliquee:
            remise_type = self.remise_type_var.get()
            remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
            
            if remise_type == "pourcentage":
                remise_globale = total * remise_valeur / 100
            elif remise_type == "montant":
                remise_globale = min(remise_valeur, total)
        
        total_apres = total - remise_globale
        client_nom = self.tiers_var.get() if hasattr(self, 'tiers_var') else "COMPTOIR"
        
        # Créer la fenêtre d'aperçu
        preview = tk.Toplevel(self)
        preview.title("🧾 Aperçu Ticket")
        preview.configure(bg="white")
        preview.geometry("400x650")
        preview.transient(self)
        preview.grab_set()
        center_window(preview, 400, 650)
        
        # Contenu du ticket
        ticket_frame = tk.Frame(preview, bg="white", padx=20, pady=20)
        ticket_frame.pack(fill="both", expand=True)
        
        # En-tête
        tk.Label(ticket_frame, text="VOTRE MAGASIN", 
                font=("Courier", 14, "bold"), bg="white").pack()
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Infos
        tk.Label(ticket_frame, text=f"Client: {client_nom}", 
                font=("Courier", 9), bg="white", anchor="w").pack(fill="x")
        tk.Label(ticket_frame, text=f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                font=("Courier", 8), bg="white", anchor="w").pack(fill="x")
        tk.Label(ticket_frame, text="-"*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Lignes de produits
        for l in self.lignes:
            designation = l.get("designation", "Produit")
            if len(designation) > 25:
                designation = designation[:22] + "..."
            
            qty = l.get("quantite", 0)
            prix = l.get("prix_remise", l.get("prix", 0))
            total_ligne = l.get("total_ht", l["total"])
            remise_produit = l.get("remise_produit", 0)
            
            # Ligne produit
            line_text = f"{qty:.0f} x {designation}"
            tk.Label(ticket_frame, text=line_text, font=("Courier", 8), 
                    bg="white", anchor="w").pack(fill="x")
            
            # Prix avec remise si applicable
            if remise_produit > 0:
                prix_text = f"  {prix:.2f} DA (-{remise_produit:.0f}%)"
            else:
                prix_text = f"  {prix:.2f} DA"
            tk.Label(ticket_frame, text=prix_text, font=("Courier", 8), 
                    bg="white", anchor="w").pack(fill="x")
        
        tk.Label(ticket_frame, text="-"*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Totaux
        tk.Label(ticket_frame, text=f"TOTAL HT: {total:,.2f} DA", 
                font=("Courier", 9), bg="white", anchor="e").pack(fill="x")
        
        if total_tva > 0:
            tk.Label(ticket_frame, text=f"TVA: {total_tva:,.2f} DA", 
                    font=("Courier", 9), bg="white", anchor="e").pack(fill="x")
        
        if remise_globale > 0:
            tk.Label(ticket_frame, text=f"Remise: -{remise_globale:,.2f} DA", 
                    font=("Courier", 9), bg="white", fg="red", anchor="e").pack(fill="x")
            if remise_type == "pourcentage":
                tk.Label(ticket_frame, text=f"  ({remise_valeur:.0f}%)", 
                        font=("Courier", 7), bg="white", fg="red", anchor="e").pack(fill="x")
        
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=3)
        tk.Label(ticket_frame, text=f"⭐ TOTAL TTC: {total_apres + total_tva:,.2f} DA", 
                font=("Courier", 12, "bold"), bg="white", fg="green", anchor="e").pack(fill="x")
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        tk.Label(ticket_frame, text="MERCI DE VOTRE VISITE !", 
                font=("Courier", 10, "bold"), bg="white").pack()
        tk.Label(ticket_frame, text=f"Généré le {datetime.now().strftime('%H:%M:%S')}", 
                font=("Courier", 7), bg="white").pack()
        
        # Boutons
        btn_frame = tk.Frame(preview, bg="white", pady=10)
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="❌ Fermer", command=preview.destroy, 
                bg=CLR_RED, fg="white", font=("Segoe UI", 9, "bold"),
                padx=15, pady=5, cursor="hand2").pack(side="left", padx=5, expand=True)
        
        tk.Button(btn_frame, text="🖨 Imprimer", 
                command=lambda: self._imprimer_ticket_html(preview),
                bg=CLR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                padx=15, pady=5, cursor="hand2").pack(side="left", padx=5, expand=True)

    def _imprimer_ticket_html(self, preview_window):
        """Imprimer le ticket via HTML"""
        try:
            # Récupérer tout le texte du ticket
            content = ""
            for child in preview_window.winfo_children():
                if isinstance(child, tk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            text = subchild.cget("text")
                            if text:
                                content += text + "\n"
            
            # Créer un fichier HTML pour impression
            html_content = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Ticket de caisse</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        font-size: 10pt;
                        padding: 20px;
                        margin: 0;
                        white-space: pre-wrap;
                        max-width: 380px;
                        margin: 0 auto;
                    }}
                    @media print {{
                        body {{ padding: 10px; }}
                    }}
                </style>
            </head>
            <body>
                <pre>{content}</pre>
                <script>
                    window.onload = function() {{
                        window.print();
                        setTimeout(function() {{ window.close(); }}, 1000);
                    }}
                </script>
            </body>
            </html>
            """
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                                    delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            webbrowser.open(temp_file.name)
            
            messagebox.showinfo("Impression", 
                            "Ticket ouvert dans le navigateur.\n"
                            "Utilisez Ctrl+P pour imprimer.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'impression: {str(e)}")

    def creer_facture_rapide(self):
        """Créer une facture à partir du bon en cours"""
        if not self.lignes:
            messagebox.showwarning("Avertissement", "Le panier est vide")
            return
        
        # Vérifier si un client est sélectionné
        tiers_nom = self.tiers_var.get() if hasattr(self, 'tiers_var') else ""
        if not tiers_nom or tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", 
                                "Sélectionnez un client pour créer une facture.\n"
                                "Le client COMPTOIR n'est pas éligible pour une facture.")
            return
        
        # Vérifier que ce n'est pas le client COMPTOIR
        if tiers_nom == "COMPTOIR":
            messagebox.showerror("Erreur", 
                                "Impossible de créer une facture pour le client COMPTOIR.\n"
                                "Veuillez sélectionner un client avec des informations fiscales.")
            return
        
        # Calculer le total
        total = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        
        # Demander confirmation
        if messagebox.askyesno("Confirmation", 
                            f"Créer une facture pour le client {tiers_nom} ?\n\n"
                            f"Total HT: {total:,.2f} DA\n"
                            f"Total TTC: {self.total_ttc_var.get() if hasattr(self, 'total_ttc_var') else 'N/A'}"):
            # Sauvegarder d'abord le bon
            self.save()
            messagebox.showinfo("Info", 
                            "✅ Le bon a été sauvegardé.\n\n"
                            "Vous pouvez maintenant créer la facture depuis la page Factures,\n"
                            "ou utiliser le bouton '🧾 Créer Facture' dans la liste des bons.")             
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins une ligne")
            return
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", "Sélectionnez un tiers")
            return
        tiers_id = self.tiers_map[tiers_nom]
        
        # Calculer les totaux HT et TTC
        total_ht_brut = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        
        # ✅ CORRECTION : Vérifier si les attributs de remise existent
        remise_montant = 0
        remise_type = "aucune"
        remise_valeur = 0
        motif_remise = ""
        
        if self.bon_type == "vente" and hasattr(self, 'remise_type_var'):
            remise_type = self.remise_type_var.get()
            try:
                remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
            except ValueError:
                remise_valeur = 0
            
            if remise_type != "aucune" and remise_valeur > 0:
                if remise_type == "pourcentage":
                    remise_montant = total_ht_brut * remise_valeur / 100
                else:  # montant fixe
                    remise_montant = min(remise_valeur, total_ht_brut)
                
                total_ht = total_ht_brut - remise_montant
                motif_remise = self.remise_motif_var.get().strip() or "Remise accordée"
            else:
                total_ht = total_ht_brut
        else:
            total_ht = total_ht_brut
        
        # Calculer la TVA et le TTC
        total_tva = 0
        total_ttc = 0
        
        for l in self.lignes:
            tva_taux = l.get("tva", 0)
            ht_ligne = l.get("total_ht", l["total"])
            
            if self.bon_type == "vente" and remise_montant > 0 and total_ht_brut > 0:
                # ✅ Répartir la remise proportionnellement sur chaque ligne
                proportion = ht_ligne / total_ht_brut
                ht_avec_remise = ht_ligne - (remise_montant * proportion)
            else:
                ht_avec_remise = ht_ligne
            
            tva_ligne = ht_avec_remise * tva_taux / 100
            ttc_ligne = ht_avec_remise + tva_ligne
            
            total_tva += tva_ligne
            total_ttc += ttc_ligne
            
            # ✅ STOCKER LE HT AVEC REMISE POUR L'ENREGISTREMENT
            l["total_ht_avec_remise"] = ht_avec_remise
            l["total_ttc_avec_remise"] = ttc_ligne
            l["tva_ligne"] = tva_ligne
        
        # Régénérer le numéro avec l'ID du tiers au moment de valider
        tiers_id_local = self.tiers_map[tiers_nom]
        prefix = "BA" if self.bon_type == "achat" else "BV"
        num = next_numero_tiers(prefix, tiers_id_local)
        self.num_var.set(num)      
        dt = self.date_var.get()

        if not valider_date(self.date_var.get()):
            messagebox.showerror("Erreur", "Format de date invalide.\nUtilisez le format YYYY-MM-DD\nExemple: 2026-06-04")
            return

        # Vérification du stock pour les ventes
        if self.bon_type == "vente":
            conn_verif = get_conn()
            alertes = []
            for l in self.lignes:
                quantite_a_verifier = l.get("quantite_base", l["quantite"])
                produit = conn_verif.execute(
                    "SELECT designation, stock_actuel FROM produits WHERE id=?", 
                    (l["produit_id"],)
                ).fetchone()
                
                if produit and produit["stock_actuel"] < quantite_a_verifier:
                    alertes.append(
                        f"⚠️ {produit['designation']}: Stock actuel={produit['stock_actuel']:.2f}, "
                        f"Vente={quantite_a_verifier:.2f} → Nouveau stock={produit['stock_actuel'] - quantite_a_verifier:.2f}"
                    )
            conn_verif.close()
            
            if alertes:
                messagebox.showwarning(
                    "⚠️ ALERTE STOCK INSUFFISANT",
                    "Les produits suivants ont un stock insuffisant :\n\n" + 
                    "\n".join(alertes) +
                    "\n\n➡ Le bon sera quand même enregistré avec un stock négatif."
                )

        # ✅ Confirmation avec affichage de la remise
        if self.bon_type == "achat":
            if not messagebox.askyesno("Confirmation", 
                f"Valider ce bon d'achat ?\n"
                f"Numéro: {num}\n"
                f"Total HT: {total_ht:,.2f} DA\n"
                f"Total TTC: {total_ttc:,.2f} DA"):
                return
        else:
            msg_confirmation = f"Valider ce bon de vente ?\n\n"
            msg_confirmation += f"Numéro: {num}\n"
            msg_confirmation += f"Client: {tiers_nom}\n"
            msg_confirmation += f"Total HT brut: {total_ht_brut:,.2f} DA\n"
            
            if remise_montant > 0:
                msg_confirmation += f"Remise: {remise_montant:,.2f} DA ({remise_type} {remise_valeur}%)\n"
                msg_confirmation += f"Motif: {motif_remise}\n"
            
            msg_confirmation += f"Total HT après remise: {total_ht:,.2f} DA\n"
            msg_confirmation += f"TVA: {total_tva:,.2f} DA\n"
            msg_confirmation += f"Total TTC: {total_ttc:,.2f} DA"
            
            if not messagebox.askyesno("Confirmation", msg_confirmation):
                return

        conn = get_conn()
        try:
            if self.bon_type == "achat":
                # ... (votre code achat inchangé)
                date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_livraison = self.date_livraison_var.get() if hasattr(self, 'date_livraison_var') else None
                num_facture = self.num_facture_fournisseur_var.get() if hasattr(self, 'num_facture_fournisseur_var') else None
                num_bl = self.num_bl_fournisseur_var.get() if hasattr(self, 'num_bl_fournisseur_var') else None
                
                fournisseur = conn.execute("SELECT solde FROM fournisseurs WHERE id=?", (tiers_id,)).fetchone()
                ancien_solde = fournisseur["solde"] if fournisseur else 0
                
                nouveau_solde = ancien_solde + total_ttc
                
                conn.execute(
                    """INSERT INTO bons_achat(numero, date_bon, date_creation, date_livraison, 
                    fournisseur_id, total, statut, num_facture_fournisseur, num_bl_fournisseur,
                    ancien_solde, nouveau_solde) 
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (num, dt, date_creation, date_livraison, tiers_id, total_ttc, "Validé", 
                    num_facture, num_bl, ancien_solde, nouveau_solde)
                )
                bon_id = conn.execute(
                    "SELECT id FROM bons_achat WHERE numero=?", (num,)
                ).fetchone()["id"]

                for l in self.lignes:
                    quantite_achat = l.get("quantite_base", l["quantite"])
                    ht_l = l.get("total_ht", l["total"])
                    taux = float(l.get("tva", 0))
                    tva_l = l.get("total_tva", ht_l * taux / 100)
                    ttc_l = l.get("total_ttc", ht_l + tva_l)

                    conn.execute(
                        """INSERT INTO lignes_achat
                        (bon_id, produit_id, quantite, prix_unitaire,
                            total_ht, tva_taux, total_ttc, total)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (bon_id, l["produit_id"], quantite_achat, l["prix"],
                        ht_l, taux, ttc_l, ht_l)
                    )
                    nouveau_pmp, nouveau_cout = calculer_pmp(
                        conn, l["produit_id"], quantite_achat, l["prix"]
                    )
                    conn.execute(
                        """UPDATE produits
                        SET stock_actuel = stock_actuel + ?,
                            prix_moyen_pondere = ?,
                            cout_total_stock = ?,
                            prix_achat = ?
                        WHERE id = ?""",
                        (quantite_achat, nouveau_pmp, nouveau_cout, l["prix"], l["produit_id"])
                    )
                    conn.execute(
                        """INSERT INTO historique_prix
                        (produit_id, date_achat, quantite, prix_unitaire, prix_moyen_apres)
                        VALUES(?,?,?,?,?)""",
                        (l["produit_id"], dt, quantite_achat, l["prix"], nouveau_pmp)
                    )
                conn.execute("UPDATE fournisseurs SET solde = solde + ? WHERE id=?", (total_ttc, tiers_id))
                
            else:
                # ✅ VENTE : Enregistrement du bon
                conn.execute("INSERT INTO bons_vente(numero,date_bon,client_id,total,statut) VALUES(?,?,?,?,?)",
                            (num, dt, tiers_id, total_ht, "Validé"))
                bon_id = conn.execute("SELECT id FROM bons_vente WHERE numero=?", (num,)).fetchone()["id"]
                
                # ✅ ENREGISTRER LES REMISES PAR PRODUIT
                for l in self.lignes:
                    remise_produit = l.get("remise_produit", 0)
                    if remise_produit > 0:
                        conn.execute("""
                            INSERT INTO remises(vente_id, achat_id, produit_id, type, valeur, motif, total_avant, total_apres, reference)
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            bon_id,  # vente_id
                            None,    # achat_id
                            l["produit_id"],  # ✅ produit_id
                            "produit",
                            remise_produit, 
                            f"Remise sur {l['designation']}",
                            l.get("total_ht_brut", l["total_ht"]),
                            l["total_ht"],
                            f"Ligne {l['designation']}"
                        ))
                
                # ✅ Enregistrer les lignes de vente AVEC les remises
                for l in self.lignes:
                    quantite_vente = l.get("quantite_base", l["quantite"])
                    ht_avec_remise = l.get("total_ht", l["total"])
                    
                    conn.execute("""
                        INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total)
                        VALUES(?, ?, ?, ?, ?)
                    """, (bon_id, l["produit_id"], quantite_vente, l["prix"], ht_avec_remise))
                    
                    # ✅ CORRECTION : réduire le coût du stock AVANT de réduire le stock
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], quantite_vente)
                    
                
                # ✅ Mise à jour du solde client
                conn.execute("UPDATE clients SET solde = solde + ? WHERE id=?", (total_ht, tiers_id))
            
            conn.commit()
            conn.close()
            
            # ✅ Message de succès avec détails
            msg_succes = f"✅ Bon {num} enregistré avec succès !\n\n"
            msg_succes += f"Client: {tiers_nom}\n"
            msg_succes += f"Total HT: {total_ht:,.2f} DA\n"
            if remise_montant > 0:
                msg_succes += f"Remise: {remise_montant:,.2f} DA\n"
            msg_succes += f"TTC: {total_ttc:,.2f} DA"
            
            messagebox.showinfo("Succès", msg_succes)
            self.destroy()
            
        except sqlite3.IntegrityError:
            prefix = "BA" if self.bon_type == "achat" else "BV"
            nouveau_num = next_numero_tiers(prefix, tiers_id)
            self.num_var.set(nouveau_num)
            messagebox.showwarning(
                "Numéro dupliqué",
                f"Le numéro {num} existait déjà.\n"
                f"Nouveau numéro généré : {nouveau_num}\n"
                "Veuillez valider à nouveau."
            )
            if conn:
                conn.rollback()
                conn.close()
        except Exception as ex:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {str(ex)}")
            if conn:
                conn.rollback()
                conn.close()

# ========== DIALOGUE MODIFICATION BON ==========

class BonEditDialog(tk.Toplevel):
    def __init__(self, parent, bon_type, bon_id, bon_data, lignes):
        super().__init__(parent)
        self.bon_type = bon_type
        self.bon_id = bon_id
        self.bon_data = bon_data
        self.lignes_originales = list(lignes)
        self.lignes = []
        self.title(f"✏ Modification Bon d'{bon_type.capitalize()}")
        self.bind("<<ProduitsModifies>>", lambda e: self.refresh_produits())
        self.configure(bg=CLR_BG)
        self.state('zoomed')  # Pour Windows

        self.geometry("900x750")

        # Charger le solde actuel du tiers
        conn = get_conn()
        if self.bon_type == "achat":
            tiers_row = conn.execute("SELECT solde FROM fournisseurs WHERE id=?", (self.bon_data["fournisseur_id"],)).fetchone()
        else:
            tiers_row = conn.execute("SELECT solde FROM clients WHERE id=?", (self.bon_data["client_id"],)).fetchone()
        conn.close()
        self.solde_tiers_actuel = tiers_row["solde"] if tiers_row else 0

        self._build()
        self._charger_lignes()
        center_window(self, 900, 750)
    def refresh_produits(self):
        """✅ Rafraîchit la liste des produits dans le combobox pour BonEditDialog"""
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                               prix_achat, prix_vente, barcode,
                               prix_detail, prix_gros, prix_super_gros, prix_special,
                               tva
                        FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        old_selection = self.prod_var.get() if hasattr(self, 'prod_var') else ""
        self.prod_map = {}
        new_prod_list = []
        
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
            new_prod_list.append(key)
        
        # Mettre à jour la combobox des produits
        self._update_combobox_produits(new_prod_list, old_selection)
        
        if old_selection in self.prod_map:
            p = self.prod_map[old_selection]
            px = p["prix_achat"] if self.bon_type == "achat" else p["prix_vente"]
            self.prix_var.set(str(px))
        elif new_prod_list:
            self.prod_var.set(new_prod_list[0])
    
    def _update_combobox_produits(self, new_prod_list, old_selection):
        """Met à jour la combobox des produits"""
        for child in self.winfo_children():
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_children'):
                        for grandchild in subchild.winfo_children():
                            if isinstance(grandchild, ttk.Combobox):
                                if grandchild['values'] and len(grandchild['values']) > 0:
                                    if hasattr(self, 'prod_var') and grandchild.cget('textvariable') == str(self.prod_var):
                                        grandchild['values'] = new_prod_list
                                        if old_selection in new_prod_list:
                                            self.prod_var.set(old_selection)
                                        elif new_prod_list:
                                            self.prod_var.set(new_prod_list[0])
                                        return
    def _build(self):
        # ========== EN-TÊTE PRINCIPAL ==========
        top = tk.Frame(self, bg=CLR_CARD, padx=15, pady=12)
        top.pack(fill="x", padx=15, pady=(15,5))

        # Ligne 1: Numéro, Date, Statut, Total actuel
        lbl(top, "Numéro:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4, pady=3)

        self.num_var = tk.StringVar(value=self.bon_data["numero"])
        entry(top, width=18, textvariable=self.num_var).grid(row=0, column=1, padx=8, pady=3)

        lbl(top, "Date:", color=CLR_MUTED).grid(row=0, column=2, sticky="w", padx=4)
        self.date_var = tk.StringVar(value=self.bon_data["date_bon"])
        DateEntry(top, self.date_var, width=12).grid(row=0, column=3, padx=8)

        lbl(top, "Statut:", color=CLR_MUTED).grid(row=0, column=4, sticky="w", padx=4)
        statut_color = CLR_GREEN if self.bon_data["statut"] == "Validé" else CLR_RED
        tk.Label(top, text=self.bon_data["statut"], bg=CLR_CARD, fg=statut_color,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=5, sticky="w", padx=8)

        lbl(top, "Total actuel:", color=CLR_MUTED).grid(row=0, column=6, sticky="w", padx=(20,4))
        tk.Label(top, text=f"{self.bon_data['total']:,.2f} DA", bg=CLR_CARD, fg=CLR_GREEN,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=7, sticky="w", padx=8)

        # Ligne 2: Fournisseur/Client + Solde actuel
        tiers_label = "Fournisseur:" if self.bon_type == "achat" else "Client:"
        lbl(top, tiers_label, color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=3)
        
        conn = get_conn()
        if self.bon_type == "achat":
            tiers = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            tiers_id = self.bon_data["fournisseur_id"]
        else:
            tiers = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
            tiers_id = self.bon_data["client_id"]
        conn.close()
        
        self.tiers_map = {r["nom"]: r["id"] for r in tiers}
        self.tiers_reverse = {r["id"]: r["nom"] for r in tiers}
        self.tiers_var = tk.StringVar(value=self.tiers_reverse.get(tiers_id, ""))
        cb = combo(top, list(self.tiers_map.keys()), width=22, textvariable=self.tiers_var)
        cb.grid(row=1, column=1, padx=8, pady=3)

        lbl(top, "Solde actuel:", color=CLR_MUTED).grid(row=1, column=2, sticky="w", padx=(20,4))
        solde_color = CLR_RED if self.solde_tiers_actuel < 0 else CLR_TEXT
        tk.Label(top, text=f"{self.solde_tiers_actuel:,.2f} DA", bg=CLR_CARD, fg=solde_color,
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=3, sticky="w", padx=8)

        # ========== INFOS SPÉCIFIQUES ACHAT ==========
        if self.bon_type == "achat":
            line3 = tk.Frame(self, bg=CLR_CARD, padx=15, pady=8)
            line3.pack(fill="x", padx=15, pady=(0,5))

            lbl(line3, "📅 Date livraison:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4)
            self.date_livraison_var = tk.StringVar(value=self.bon_data.get("date_livraison") or "")
            entry(line3, width=14, textvariable=self.date_livraison_var).grid(row=0, column=1, padx=8)

            lbl(line3, "📄 N° Facture Fourn.:", color=CLR_MUTED).grid(row=0, column=2, sticky="w", padx=(20,4))
            self.num_facture_fournisseur_var = tk.StringVar(value=self.bon_data.get("num_facture_fournisseur") or "")
            entry(line3, width=18, textvariable=self.num_facture_fournisseur_var).grid(row=0, column=3, padx=8)

            lbl(line3, "🚚 N° BL Fournisseur:", color=CLR_MUTED).grid(row=0, column=4, sticky="w", padx=(20,4))
            self.num_bl_fournisseur_var = tk.StringVar(value=self.bon_data.get("num_bl_fournisseur") or "")
            entry(line3, width=18, textvariable=self.num_bl_fournisseur_var).grid(row=0, column=5, padx=8)

            lbl(line3, "Ancien solde:", color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=(6,0))
            tk.Label(line3, text=f"{self.bon_data.get('ancien_solde', 0):,.2f} DA", bg=CLR_CARD, fg=CLR_ORANGE,
                     font=("Segoe UI", 9, "bold")).grid(row=1, column=1, sticky="w", padx=8, pady=(6,0))

            lbl(line3, "Nouveau solde (au moment du bon):", color=CLR_MUTED).grid(row=1, column=2, sticky="w", padx=(20,4), pady=(6,0))
            tk.Label(line3, text=f"{self.bon_data.get('nouveau_solde', 0):,.2f} DA", bg=CLR_CARD, fg=CLR_GREEN,
                     font=("Segoe UI", 9, "bold")).grid(row=1, column=3, sticky="w", padx=8, pady=(6,0))

        mid = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        mid.pack(fill="x")
        
        lbl(mid, "Produit:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4)
        
        conn = get_conn()
        prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                               prix_achat, prix_vente, barcode,
                               prix_detail, prix_gros, prix_super_gros, prix_special,
                               tva  -- ✅ AJOUTER LA TVA ICI
                        FROM produits ORDER BY designation""").fetchall()
        conn.close()
        self.prod_map = {f"{r['code']} - {r['designation']}": r for r in prods}
        self.prod_var = tk.StringVar()
        pcb = combo(mid, list(self.prod_map.keys()), width=30, textvariable=self.prod_var)
        pcb.grid(row=0, column=1, padx=8)
        # ✅ AJOUT DU BOUTON RAFRAÎCHIR
        btn_refresh = tk.Button(mid, text="🔄", command=self.refresh_produits,
                                bg=CLR_ACCENT, fg="white", relief="flat",
                                font=("Segoe UI", 10, "bold"), padx=6, pady=2,
                                cursor="hand2", width=3)
        btn_refresh.grid(row=0, column=2, padx=2, pady=2)

        self.prod_var.trace_add("write", self._on_prod_change)


        lbl(mid, "Code Barre:", color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.barcode_var = tk.StringVar()
        self.barcode_entry = entry(mid, width=18, textvariable=self.barcode_var)
        self.barcode_entry.grid(row=1, column=1, padx=8, pady=4)
        self.barcode_entry.bind("<Return>", lambda e: self._search_prod_by_barcode())
        tk.Button(mid, text="🔎 Chercher", width=10, command=self._search_prod_by_barcode,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2").grid(row=1, column=2, padx=8, pady=4)

        lbl(mid, "Qté:", color=CLR_MUTED).grid(row=0, column=2, padx=4)
        self.qty_var = tk.StringVar(value="1")
        entry(mid, width=8, textvariable=self.qty_var).grid(row=0, column=3, padx=4)

        lbl(mid, "Prix:", color=CLR_MUTED).grid(row=0, column=4, padx=4)
        self.prix_var = tk.StringVar()
        entry(mid, width=10, textvariable=self.prix_var).grid(row=0, column=5, padx=4)

        tk.Button(mid, text="➕ Ajouter ligne", command=self.add_ligne, 
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=5, 
                  cursor="hand2").grid(row=0, column=6, padx=10)

        if self.prod_map:
            self.prod_var.set(list(self.prod_map.keys())[0])

        cols = ["Code", "Produit", "Qté", "Qté Carton", "Unité", "Prix Unit.", "TVA", "Total HT", "Total TTC"]
        widths = [80, 180, 60, 70, 60, 80, 60, 90, 110]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=15, pady=10)

        total_frame = tk.Frame(self, bg=CLR_BG, padx=15, pady=5)
        total_frame.pack(fill="x")
        self.total_var = tk.StringVar(value="Total: 0.00 DA")
        tk.Label(total_frame, textvariable=self.total_var, bg=CLR_BG, fg=CLR_GREEN, font=("Segoe UI", 14, "bold")).pack(side="right", padx=10)

        action_frame = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        action_frame.pack(fill="x", side="bottom")
        
        tk.Button(action_frame, text="✏ Modifier ligne", command=self.edit_ligne,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(action_frame, text="💵 Modifier Prix", command=self.modifier_prix_ligne,
                bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(action_frame, text="🗑 Supprimer ligne", command=self.remove_ligne,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)

        tk.Button(action_frame, text="✅ VALIDER LES MODIFICATIONS", command=self.save,
                  bg=CLR_GREEN, fg="white", relief="flat", 
                  font=("Segoe UI", 10, "bold"),
                  padx=20, pady=6, cursor="hand2").pack(side="left", padx=20)
        
        tk.Button(action_frame, text="❌ ANNULER", command=self.destroy,
                  bg=CLR_RED, fg="white", relief="flat", 
                  font=("Segoe UI", 10, "bold"),
                  padx=14, pady=6, cursor="hand2").pack(side="left", padx=4)
    def modifier_prix_ligne(self):
        """Modifier le prix unitaire d'une ligne existante"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]

        nouveau_prix = simpledialog.askfloat(
            "💵 Modifier le prix",
            f"Produit: {ligne['designation']}\n"
            f"Prix actuel: {ligne['prix']:.2f} DA\n\n"
            f"Nouveau prix unitaire (DA):",
            initialvalue=ligne['prix'],
            minvalue=0.01,
            parent=self
        )
        if nouveau_prix is None:
            return
        if nouveau_prix <= 0:
            messagebox.showerror("Erreur", "Le prix doit être > 0")
            return

        ligne["prix"] = nouveau_prix
        ligne["total_ht"] = ligne["quantite"] * nouveau_prix   # quantite = quantité en unité de base ici
        ligne["total"] = ligne["total_ht"]

        tva_taux = ligne.get("tva", 0)
        ligne["total_tva"] = ligne["total_ht"] * tva_taux / 100
        ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]

        self._refresh_tree()
        messagebox.showinfo("Succès", f"✅ Prix mis à jour: {nouveau_prix:.2f} DA")
    def _charger_lignes(self):
        for ligne in self.lignes_originales:
            prod_info = None
            designation_key = None
            for key, val in self.prod_map.items():
                if val["id"] == ligne["produit_id"]:
                    prod_info = val
                    designation_key = key
                    break
            if not prod_info:
                continue
            try:
                facteur = float(prod_info["facteur_conversion"]) if prod_info["facteur_conversion"] else 1
            except (KeyError, IndexError, TypeError):
                facteur = 1

            # ✅ Récupérer le taux TVA réel de la ligne (ou du produit à défaut)
            tva_ligne = ligne["tva_taux"] if "tva_taux" in ligne.keys() and ligne["tva_taux"] is not None else float(prod_info["tva"] or 0)

            self.lignes.append({
                "produit_id": ligne["produit_id"],
                "designation": designation_key,
                "code": prod_info["code"] if prod_info["code"] else "",
                "unite": prod_info["unite"] if prod_info["unite"] else "Pcs",
                "barcode": prod_info["barcode"] if prod_info["barcode"] else "",
                "quantite": ligne["quantite"],
                "facteur": facteur,
                "prix": ligne["prix_unitaire"],
                "total": ligne["total"],
                "tva": tva_ligne,   # ✅ ajouté
            })
        self._refresh_tree()
    
    def _on_prod_change(self, *a):
        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            px = p["prix_achat"] if self.bon_type == "achat" else p["prix_vente"]
            self.prix_var.set(str(px))

    def _search_prod_by_barcode(self):
        raw = self.barcode_var.get().strip()
        if not raw:
            messagebox.showwarning("Recherche code-barre", "Entrez un code-barre à rechercher")
            return
        normalized = normalize_barcode_input(raw)
        if not normalized:
            messagebox.showwarning("Recherche code-barre", "Code-barre invalide après normalisation")
            return
        conn = get_conn()
        try:
            produit = conn.execute("SELECT * FROM produits WHERE barcode = ? OR code = ?", (normalized, normalized)).fetchone()
            if not produit:
                produit = conn.execute("SELECT * FROM produits WHERE barcode LIKE ? OR code LIKE ? LIMIT 1", (f"%{normalized}%", f"%{normalized}%")).fetchone()
        finally:
            conn.close()
        if produit:
            display_key = f"{produit['code']} - {produit['designation']}"
            if display_key in self.prod_map:
                self.prod_var.set(display_key)
            else:
                self.prod_map[display_key] = dict(produit)
                self.prod_var.set(display_key)
            px = produit['prix_achat'] if self.bon_type == 'achat' else produit['prix_vente']
            self.prix_var.set(str(px))
            self.qty_var.set('1')
            self.remise_produit_var.set("0")  # ✅ Réinitialiser la remise
            self.barcode_var.set('')
            messagebox.showinfo("Produit trouvé", f"Produit trouvé: {produit['designation']}")
        else:
            messagebox.showinfo("Non trouvé", f"Aucun produit trouvé pour: {normalized}")

    def edit_ligne(self):
        """Modifier la quantité d'une ligne sélectionnée"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne à modifier")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]
        
        # ✅ Fenêtre de dialogue dédiée
        dlg = tk.Toplevel(self)
        dlg.title("Modifier la quantité")
        dlg.configure(bg=CLR_BG)
        dlg.geometry("400x300")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, True)
        center_window(dlg, 400, 300)
        
        main_frame = tk.Frame(dlg, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏️ Modifier la quantité", 12, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # Informations du produit
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=5)
        
        facteur = ligne.get("facteur", 1)
        qte_affichee = ligne["quantite"] / facteur if facteur else ligne["quantite"]
        
        lbl(info_frame, f"Produit: {ligne['designation']}", 10, True, CLR_TEXT).pack(anchor="w")
        lbl(info_frame, f"Quantité actuelle: {qte_affichee:.2f} {ligne.get('unite', 'Pcs')}", 9, False, CLR_MUTED).pack(anchor="w")
        lbl(info_frame, f"Prix unitaire: {ligne['prix']:.2f} DA", 9, False, CLR_MUTED).pack(anchor="w")
        if ligne.get("remise_produit", 0) > 0:
            lbl(info_frame, f"Remise: {ligne['remise_produit']:.0f}%", 9, False, CLR_ORANGE).pack(anchor="w")
        
        # Champ de saisie
        input_frame = tk.Frame(main_frame, bg=CLR_BG)
        input_frame.pack(fill="x", pady=10)
        
        lbl(input_frame, "Nouvelle quantité:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        new_qty_var = tk.StringVar(value=str(qte_affichee))
        entry_qty = entry(input_frame, width=12, textvariable=new_qty_var, font=("Segoe UI", 11, "bold"))
        entry_qty.pack(side="left", padx=10)
        entry_qty.focus_set()
        entry_qty.select_range(0, tk.END)
        
        # ✅ Message de statut
        status_var = tk.StringVar(value="")
        status_label = tk.Label(main_frame, textvariable=status_var, bg=CLR_BG, 
                            fg=CLR_GREEN, font=("Segoe UI", 9, "bold"))
        status_label.pack(pady=5)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        def valider_modification():
            try:
                nouvelle_qty = parse_decimal(new_qty_var.get())
                if nouvelle_qty <= 0:
                    status_var.set("❌ La quantité doit être > 0")
                    status_label.config(fg=CLR_RED)
                    return
            except ValueError:
                status_var.set("❌ Quantité invalide")
                status_label.config(fg=CLR_RED)
                return
            
            # Mettre à jour la ligne
            facteur_ligne = ligne.get("facteur", 1)
            nouvelle_qty_base = nouvelle_qty * facteur_ligne
            ligne["quantite"] = nouvelle_qty_base
            ligne["total_ht"] = nouvelle_qty_base * ligne["prix"]
            ligne["total"] = ligne["total_ht"]
            
            tva_taux = ligne.get("tva", 0)
            ligne["total_tva"] = ligne["total_ht"] * tva_taux / 100
            ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]
            
            if ligne.get("remise_produit", 0) > 0:
                ligne["prix_remise"] = ligne["prix"] * (1 - ligne["remise_produit"] / 100)
                ligne["total_ht"] = nouvelle_qty_base * ligne["prix_remise"]
            
            # ✅ Rafraîchir AVANT de fermer
            self._refresh_tree()
            
            # ✅ Message de succès
            status_var.set(f"✅ Quantité mise à jour: {nouvelle_qty:.2f}")
            status_label.config(fg=CLR_GREEN)
            
            # ✅ Fermer après un délai
            self.after(500, dlg.destroy)
        
        def annuler_modification():
            dlg.destroy()
        
        # Bind Entrée pour valider
        entry_qty.bind('<Return>', lambda e: valider_modification())
        entry_qty.bind('<Escape>', lambda e: annuler_modification())
        
        tk.Button(btn_frame, text="✅ Valider (Entrée)", command=valider_modification,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ Annuler (Echap)", command=annuler_modification,
                bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
    
    def add_ligne(self):
        key = self.prod_var.get()
        if key not in self.prod_map:
            messagebox.showerror("Erreur", "Veuillez sélectionner un produit")
            return
        try:
            qty = float(self.qty_var.get())
            prix = float(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité et prix doivent être des nombres")
            return
        if qty <= 0:
            messagebox.showerror("Erreur", "La quantité doit être supérieure à 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Le prix doit être supérieur à 0")
            return

        prod = self.prod_map[key]
        facteur = float(prod["facteur_conversion"]) if prod["facteur_conversion"] else 1.0
        
        # ✅ CORRECTION : Utiliser l'indexation directe pour sqlite3.Row
        tva_taux = float(prod["tva"] or 0)
        barcode = prod["barcode"] if prod["barcode"] else ""
        
        quantite_base = qty * facteur
        total_ht = quantite_base * prix
        total_tva = total_ht * tva_taux / 100
        total_ttc = total_ht + total_tva

        # ✅ VÉRIFIER SI LE PRODUIT EXISTE DÉJÀ
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                reponse = messagebox.askyesno(
                    "Produit existant",
                    f"Le produit '{key}' existe déjà dans le bon.\n"
                    f"Quantité actuelle: {ligne['quantite'] / ligne['facteur']:.2f}\n"
                    f"Nouvelle quantité: {qty:.2f}\n\n"
                    f"Voulez-vous cumuler les quantités ?"
                )
                if reponse:
                    ligne["quantite"] += quantite_base
                    ligne["total_ht"] += total_ht
                    ligne["total_tva"] += total_tva
                    ligne["total_ttc"] += total_ttc
                    ligne["total"] = ligne["total_ht"]
                    ligne["tva"] = tva_taux
                    messagebox.showinfo("Succès", 
                        f"Quantité mise à jour: {ligne['quantite'] / ligne['facteur']:.2f}")
                else:
                    messagebox.showinfo("Info", "Ligne non ajoutée")
                self._refresh_tree()
                self.qty_var.set("1")
                self.prix_var.set("")
                return

        # ✅ NOUVEAU PRODUIT - Utiliser l'indexation directe partout
        self.lignes.append({
            "produit_id": prod["id"],
            "designation": key,
            "code": prod["code"],
            "unite": prod["unite"] or "Pcs",
            "barcode": barcode,  # ✅ Déjà récupéré avec l'indexation directe
            "quantite": quantite_base,
            "facteur": facteur,
            "prix": prix,
            "total_ht": total_ht,
            "tva": tva_taux,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
            "total": total_ht,
        })
        self._refresh_tree()
        self.qty_var.set("1")
        self.prix_var.set("")
        messagebox.showinfo("Succès", "Ligne ajoutée avec succès")
    
    def remove_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne à supprimer")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_tree()
        messagebox.showinfo("Succès", "Ligne supprimée")
    
    # Dans _refresh_tree() de BonDialog et BonEditDialog (vers ligne 2760)
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        total_ht = 0
        total_tva = 0
        total_ttc = 0

        for i, l in enumerate(self.lignes):
            facteur = l.get("facteur", 1) or 1
            qte_carton = l["quantite"] / facteur if facteur else l["quantite"]
            
            # ✅ Afficher la quantité avec les cartons
            qty_text = f"{l['quantite']:.2f} ({qte_carton:.2f} cartons)" if facteur > 1 else f"{l['quantite']:.2f}"
            
            tva_taux = l.get("tva", 19)
            ht_ligne = l["total"]
            tva_ligne = ht_ligne * tva_taux / 100
            ttc_ligne = ht_ligne + tva_ligne
            
            self.tree.insert("", "end", iid=str(i),
                values=(
                    l.get("code", ""),
                    l["designation"],
                    qty_text,  # ✅ Quantité avec cartons
                    f"{qte_carton:.2f}",  # ✅ Garder la colonne Qté Carton séparée
                    l.get("unite", "Pcs"),
                    f"{l['prix']:.2f}",
                    f"{tva_taux:.0f}%",
                    f"{ht_ligne:.2f}",
                    f"{ttc_ligne:.2f}"
                ))
            
            total_ht += ht_ligne
            total_tva += tva_ligne
            total_ttc += ttc_ligne

        self.total_var.set(f"Total HT: {total_ht:,.2f} DA  |  TVA: {total_tva:,.2f} DA  |  TTC: {total_ttc:,.2f} DA")
    
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins une ligne")
            return
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", "Sélectionnez un fournisseur/client")
            return
        tiers_id = self.tiers_map[tiers_nom]
        total = sum(l["total"] for l in self.lignes)
        dt = self.date_var.get()
        
        # ✅ Récupérer le nouveau numéro
        nouveau_numero = self.num_var.get().strip()
        if not nouveau_numero:
            messagebox.showerror("Erreur", "Le numéro ne peut pas être vide")
            return
        
        # ✅ Vérifier que le numéro n'est pas déjà utilisé (sauf par ce bon)
        conn_check = get_conn()
        table = "bons_achat" if self.bon_type == "achat" else "bons_vente"
        existing = conn_check.execute(
            f"SELECT id FROM {table} WHERE numero = ? AND id != ?",
            (nouveau_numero, self.bon_id)
        ).fetchone()
        conn_check.close()
        
        if existing:
            messagebox.showerror(
                "Numéro déjà utilisé",
                f"Le numéro '{nouveau_numero}' est déjà utilisé par un autre bon.\n"
                "Veuillez choisir un autre numéro."
            )
            return
        
        conn = get_conn()
        try:
            if self.bon_type == "achat":
                if self.bon_data["statut"] != "Annulé":
                    anciennes_lignes = conn.execute(
                        "SELECT * FROM lignes_achat WHERE bon_id=?", (self.bon_id,)
                    ).fetchall()
                    for l in anciennes_lignes:
                        recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])
                       
                        produit = conn.execute(
                            "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
                            (l["produit_id"],)
                        ).fetchone()
                        if produit["stock_actuel"] > 0:
                            pmp = produit["cout_total_stock"] / produit["stock_actuel"]
                            conn.execute(
                                "UPDATE produits SET prix_moyen_pondere = ? WHERE id=?",
                                (pmp, l["produit_id"])
                            )
                        else:
                            conn.execute(
                                "UPDATE produits SET prix_moyen_pondere = 0, cout_total_stock = 0 WHERE id=?",
                                (l["produit_id"],)
                            )
                    conn.execute(
                        "UPDATE fournisseurs SET solde = solde - ? WHERE id=?",
                        (self.bon_data["total"], self.bon_data["fournisseur_id"])
                    )
                conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (self.bon_id,))
                
                # ✅ AJOUTER numero=? DANS L'UPDATE
                conn.execute(
                    """UPDATE bons_achat 
                    SET numero=?, date_bon=?, fournisseur_id=?, total=?, 
                        date_livraison=?, num_facture_fournisseur=?, num_bl_fournisseur=?
                    WHERE id=?""",
                    (nouveau_numero, dt, tiers_id, total,
                    self.date_livraison_var.get() or None,
                    self.num_facture_fournisseur_var.get() or None,
                    self.num_bl_fournisseur_var.get() or None,
                    self.bon_id)
                )
                for l in self.lignes:
                    tva_taux = float(l.get("tva", 0))
                    ht_l = l["total"]
                    tva_l = ht_l * tva_taux / 100
                    ttc_l = ht_l + tva_l

                    conn.execute(
                        """INSERT INTO lignes_achat
                        (bon_id, produit_id, quantite, prix_unitaire, total, total_ht, tva_taux, total_ttc)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (self.bon_id, l["produit_id"], l["quantite"], l["prix"], l["total"], ht_l, tva_taux, ttc_l)
                    )
                    nouveau_pmp, nouveau_cout = calculer_pmp(
                        conn, l["produit_id"], l["quantite"], l["prix"]
                    )
                    conn.execute(
                        """UPDATE produits
                        SET stock_actuel       = stock_actuel + ?,
                            prix_moyen_pondere = ?,
                            cout_total_stock   = ?,
                            prix_achat         = ?
                        WHERE id = ?""",
                        (l["quantite"], nouveau_pmp, nouveau_cout, l["prix"], l["produit_id"])
                    )
                    conn.execute(
                        """INSERT INTO historique_prix
                        (produit_id, date_achat, quantite, prix_unitaire, prix_moyen_apres)
                        VALUES(?,?,?,?,?)""",
                        (l["produit_id"], dt, l["quantite"], l["prix"], nouveau_pmp)
                    )
                conn.execute(
                    "UPDATE fournisseurs SET solde = solde + ? WHERE id=?", (total, tiers_id)
                )
            else:
                # Vérification du stock : on alerte mais on ne bloque plus la modification
                alertes = []
                for l in self.lignes:
                    stk = conn.execute(
                        "SELECT stock_actuel FROM produits WHERE id=?", (l["produit_id"],)
                    ).fetchone()
                    ancienne_qty = sum(
                        lq["quantite"] for lq in self.lignes_originales
                        if lq["produit_id"] == l["produit_id"]
                    )
                    stock_reel = (stk["stock_actuel"] if stk else 0) + ancienne_qty
                    if stock_reel < l["quantite"]:
                        alertes.append(
                            f"⚠️ {l['designation']}: Disponible={stock_reel:.2f}, "
                            f"Demandé={l['quantite']:.2f} → Nouveau stock={stock_reel - l['quantite']:.2f}"
                        )
                if alertes:
                    messagebox.showwarning(
                        "⚠️ ALERTE STOCK INSUFFISANT",
                        "Les produits suivants ont un stock insuffisant :\n\n" +
                        "\n".join(alertes) +
                        "\n\n➡ Le bon sera quand même modifié (le stock peut devenir négatif)."
                    )
                if self.bon_data["statut"] != "Annulé":
                    anciennes_lignes = conn.execute(
                        "SELECT * FROM lignes_vente WHERE bon_id=?", (self.bon_id,)
                    ).fetchall()
                    for l in anciennes_lignes:
                        # ✅ CORRECTION : réintégrer le stock au PMP courant (pas au prix de vente)
                        # et ajuster cout_total_stock en conséquence
                        entree_stock_annulation_vente(conn, l["produit_id"], l["quantite"])
                    conn.execute(
                        "UPDATE clients SET solde = solde - ? WHERE id=?",
                        (self.bon_data["total"], self.bon_data["client_id"])
                    )
                conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (self.bon_id,))
                
                # ✅ AJOUTER numero=? DANS L'UPDATE
                conn.execute(
                    "UPDATE bons_vente SET numero=?, date_bon=?, client_id=?, total=? WHERE id=?",
                    (nouveau_numero, dt, tiers_id, total, self.bon_id)
                )
                for l in self.lignes:
                    conn.execute(
                        """INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total)
                        VALUES(?,?,?,?,?)""",
                        (self.bon_id, l["produit_id"], l["quantite"], l["prix"], l["total"])
                    )
                    # ✅ CORRECTION : sortie de stock avec ajustement du cout_total_stock
                    # AVANT de décrémenter stock_actuel (sinon cout_total_stock ne bouge jamais)
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])
                   
                conn.execute(
                    "UPDATE clients SET solde = solde + ? WHERE id=?", (total, tiers_id)
                )
            conn.commit()
            messagebox.showinfo("Succès", "Bon modifié avec succès !")
            self.destroy()
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "numero" in str(e):
                messagebox.showerror(
                    "Erreur",
                    f"Le numéro '{nouveau_numero}' existe déjà.\n"
                    "Veuillez choisir un autre numéro."
                )
            else:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            conn.rollback()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {str(ex)}")
        finally:
            conn.close()


# ========== DIALOGUE DÉTAIL BON ==========

class BonDetailDialog(tk.Toplevel):
    def __init__(self, parent, bon_type, bon_id):
        super().__init__(parent)
        self.bon_type = bon_type
        self.title("Détail du Bon")
        self.configure(bg=CLR_BG)
        self.geometry("800x750")
        self.bon_id = bon_id
        self._load(bon_id)
        center_window(self, 800, 600)

    def _load(self, bon_id):
        conn = get_conn()
        if self.bon_type == "achat":
            bon = conn.execute("""SELECT b.*, f.nom as tiers, 
                                        b.date_creation, b.date_livraison, 
                                        b.num_facture_fournisseur, b.num_bl_fournisseur,
                                        b.ancien_solde, b.nouveau_solde
                                FROM bons_achat b
                                JOIN fournisseurs f ON b.fournisseur_id = f.id 
                                WHERE b.id = ?""", (bon_id,)).fetchone()
            lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.unite, p.facteur_conversion
                                    FROM lignes_achat l
                                    JOIN produits p ON l.produit_id = p.id 
                                    WHERE l.bon_id = ?""", (bon_id,)).fetchall()
            # ✅ Récupérer les remises par produit pour les achats
            remises = conn.execute("""
                SELECT * FROM remises WHERE achat_id = ?
            """, (bon_id,)).fetchall()
        else:
            bon = conn.execute("""SELECT b.*, c.nom as tiers 
                                FROM bons_vente b
                                JOIN clients c ON b.client_id = c.id 
                                WHERE b.id = ?""", (bon_id,)).fetchone()
            lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.unite, p.facteur_conversion
                                    FROM lignes_vente l
                                    JOIN produits p ON l.produit_id = p.id 
                                    WHERE l.bon_id = ?""", (bon_id,)).fetchall()
            # ✅ Récupérer les remises par produit pour les ventes
            remises = conn.execute("""
                SELECT * FROM remises WHERE vente_id = ?""", (bon_id,)).fetchall()
        conn.close()

        self.bon_data = dict(bon) if bon else {}
        self.lignes_data = lignes
        self.remises_data = remises

        # ========== EN-TÊTE ==========
        f = tk.Frame(self, bg=CLR_CARD, padx=20, pady=15)
        f.pack(fill="x", padx=15, pady=15)

        titre = "BON D'ACHAT" if self.bon_type == "achat" else "BON DE VENTE"
        lbl(f, f"📄 {titre} N° {bon['numero']}", 14, True, CLR_ACCENT).pack(anchor="w", pady=(0,8))

        ligne1 = tk.Frame(f, bg=CLR_CARD)
        ligne1.pack(fill="x", pady=2)
        lbl(ligne1, "Date:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["date_bon"], 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

        tiers_label = "Fournisseur:" if self.bon_type == "achat" else "Client:"
        lbl(ligne1, tiers_label, 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["tiers"], 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

        statut_color = CLR_GREEN if bon["statut"] == "Validé" else CLR_RED
        lbl(ligne1, "Statut:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["statut"], 9, True, statut_color).pack(side="left")

        if self.bon_type == "achat":
            ligne2 = tk.Frame(f, bg=CLR_CARD)
            ligne2.pack(fill="x", pady=2)
            lbl(ligne2, "📅 Date livraison:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["date_livraison"] or "-", 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

            lbl(ligne2, "📄 N° Facture Fourn.:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["num_facture_fournisseur"] or "-", 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

            lbl(ligne2, "🚚 N° BL Fournisseur:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["num_bl_fournisseur"] or "-", 9, False, CLR_TEXT).pack(side="left")

            ligne3 = tk.Frame(f, bg=CLR_CARD)
            ligne3.pack(fill="x", pady=2)
            lbl(ligne3, "Ancien solde:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne3, f"{bon['ancien_solde']:,.2f} DA", 9, False, CLR_ORANGE).pack(side="left", padx=(0,20))

            lbl(ligne3, "Nouveau solde:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne3, f"{bon['nouveau_solde']:,.2f} DA", 9, False, CLR_GREEN).pack(side="left")

        # ✅ Tableau des produits AVEC colonne Remise
        cols = ["Code", "Produit", "Qté unités", "Qté cartons", "Unité", "Prix Unit.", "Remise", "Total"]
        widths = [100, 180, 80, 80, 60, 100, 70, 120]
        tf, tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=15, pady=5)
        
        # ✅ Créer un dictionnaire des remises par produit
        remises_dict = {}
        for remise in self.remises_data:
            remise = dict(remise)
            # Si la remise est liée à un produit, on la stocke
            produit_id = remise.get("produit_id")
            if produit_id:
                remises_dict[produit_id] = remise
        
        for l in lignes:
            facteur = l["facteur_conversion"] or 1
            qte_carton = l["quantite"] / facteur if facteur else l["quantite"]
            
            # ✅ Vérifier si ce produit a une remise
            remise_info = remises_dict.get(l["produit_id"])
            if remise_info:
                remise_valeur = remise_info.get("valeur", 0)
                remise_affichage = f"{remise_valeur:.0f}%"
            else:
                remise_affichage = "-"
            
            tree.insert("", "end", values=(
                l["code"],
                l["designation"],
                f"{l['quantite']:.2f}",
                f"{qte_carton:.2f}",
                l["unite"],
                f"{l['prix_unitaire']:.2f}",
                remise_affichage,  # ✅ Nouvelle colonne Remise
                f"{l['total']:.2f}"
            ))

        # ========== FOOTER ==========
        foot = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        foot.pack(fill="x")
        
        # ✅ Calcul des totaux
        total_ttc = self.bon_data['total']
        total_ht = sum(l["total"] for l in self.lignes_data)
        
        # ✅ Calcul de la TVA
        tva_montant = 0
        for l in self.lignes_data:
            conn_tmp = get_conn()
            p = conn_tmp.execute("SELECT tva FROM produits WHERE id=?", (l["produit_id"],)).fetchone()
            conn_tmp.close()
            tva_taux = p["tva"] if p else 19
            if self.bon_type == "vente":
                tva_taux = 0
            ht_l = l["total"]
            tva_montant += ht_l * tva_taux / 100
        
        total_ttc_calc = total_ht + tva_montant
        
        # ✅ Total HT
        row_ht = tk.Frame(foot, bg=CLR_BG)
        row_ht.pack(side="left", padx=10)
        lbl(row_ht, "Total HT:", 10, True, CLR_MUTED).pack(side="left", padx=5)
        lbl(row_ht, f"{total_ht:,.2f} DA", 10, True, CLR_TEXT).pack(side="left", padx=5)
        
        # ✅ TVA
        if tva_montant > 0:
            row_tva = tk.Frame(foot, bg=CLR_BG)
            row_tva.pack(side="left", padx=20)
            lbl(row_tva, "TVA:", 10, True, CLR_MUTED).pack(side="left", padx=5)
            lbl(row_tva, f"{tva_montant:,.2f} DA", 10, True, CLR_ORANGE).pack(side="left", padx=5)
        
        # ✅ Total TTC
        lbl(foot, f"⭐ TOTAL TTC:  {total_ttc_calc:,.2f} DA", 12, True, CLR_GREEN).pack(side="right", padx=10)
        
        # ✅ Boutons
        btn_frame = tk.Frame(foot, bg=CLR_BG)
        btn_frame.pack(side="left", pady=(10,0))
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bon,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="📄 Exporter PDF", command=self.export_pdf,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=14, pady=6, cursor="hand2").pack(side="left", padx=4)
    def _get_html(self) -> str:
        """Génère le HTML via le module centralisé."""
        from gestion_stock import get_profil_by_type, get_conn
        profil = get_profil_by_type("bon_livraison")
        conn = get_conn()
        remises = conn.execute(
            "SELECT * FROM remises WHERE vente_id = ?" if self.bon_type == "vente"
            else "SELECT * FROM remises WHERE achat_id = ?",
            (self.bon_id,)
        ).fetchall()
        conn.close()
        remises_dicts = [dict(r) for r in remises]
        
        # ============================================================
        # ✅ SUPPRIMER COMPLÈTEMENT LA COLONNE "code"
        # ============================================================
        lignes_sans_code = []
        for l in self.lignes_data:
            l_dict = dict(l)
            # Supprimer la clé "code" (supprime aussi l'en-tête)
            l_dict.pop("code", None)  # pop() supprime la clé si elle existe
            lignes_sans_code.append(l_dict)
        
        html = hr.build_bon_html(
            profil        = profil,
            bon_data      = self.bon_data,
            lignes        = lignes_sans_code,  # ✅ Lignes sans la clé "code"
            remises       = remises_dicts,
            bon_type      = self.bon_type,
        )
        
        # ✅ STYLES D'IMPRESSION (déjà dans votre code)
        print_styles = """
        <style>
            @media print {
                * {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    box-shadow: none !important;
                    text-shadow: none !important;
                    background-image: none !important;
                    filter: none !important;
                    -webkit-filter: none !important;
                    opacity: 1 !important;
                }
                
                body {
                    background-color: #ffffff !important;
                    margin: 15px !important;
                    font-size: 11pt !important;
                    color: #000000 !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                }
                
                th {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    font-weight: 700 !important;
                    font-size: 11pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    border: 2px solid #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                    text-align: center !important;
                    padding: 8px 12px !important;
                    vertical-align: middle !important;
                    page-break-inside: avoid !important;
                }
                
                td {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border: 1px solid #888888 !important;
                    padding: 6px 10px !important;
                    font-size: 10pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    text-align: center !important;
                }
                
                tr:nth-child(even) td {
                    background-color: #f5f5f5 !important;
                }
                
                .header-section, .header, .bg-primary, .bg-dark {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                }
                
                .header-section h1, .header-section h2, .header-section h3 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                h1, h2, h3, h4, h5 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                table {
                    border-collapse: collapse !important;
                    width: 100% !important;
                    page-break-inside: auto !important;
                }
                
                thead {
                    display: table-header-group !important;
                }
                
                tr {
                    page-break-inside: avoid !important;
                    page-break-after: auto !important;
                }
                
                .total-row td, .grand-total td {
                    font-weight: 700 !important;
                    border-top: 3px solid #000000 !important;
                }
                
                .footer, .footer p, .footer div {
                    color: #000000 !important;
                    border-top: 2px solid #000000 !important;
                    padding-top: 10px !important;
                    margin-top: 15px !important;
                }
            }
        </style>
        """
        
        if '</head>' in html:
            html = html.replace('</head>', print_styles + '</head>')
        else:
            html = html.replace('<body>', print_styles + '<body>')
        
        return html
        
    def print_bon(self):
        viewer = hr.DocumentViewer(self)
        viewer.show(self._get_html(), f"BON N°{self.bon_data['numero']}")
 
    def export_pdf(self):
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(
            self._get_html(),
            default_name=f"Bon_{self.bon_data['numero']}.pdf",
        )

# ========== APPLICATION PRINCIPALE ==========

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📦 Gestion de Stock — v1.0")
        self.configure(bg=CLR_BG)
        
        # Plein écran par défaut
        # self.attributes('-fullscreen', True)
        self.state('zoomed')  # Pour Windows
        # Liaison de la touche F11 pour basculer le plein écran
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.quit_fullscreen)
        self.bind("<<ProduitsModifies>>", self.on_produits_modifies)
        init_db()
        self._pages = {}
        self._build()
    def on_produits_modifies(self, event):
        """✅ Relayé l'événement à toutes les fenêtres Toplevel ouvertes"""
        print("📢 Événement ProduitsModifies reçu dans App !")  # Pour debug
        
        # Notifier toutes les pages ouvertes
        for page in self._pages.values():
            if hasattr(page, 'refresh_produits'):
                try:
                    page.refresh_produits()
                except Exception as e:
                    print(f"Erreur refresh page: {e}")
        
        # Notifier toutes les fenêtres Toplevel ouvertes (BonDialog, BonEditDialog, etc.)
        for fenetre in self.winfo_children():
            if isinstance(fenetre, tk.Toplevel):
                if hasattr(fenetre, 'refresh_produits'):
                    try:
                        fenetre.refresh_produits()
                    except Exception as e:
                        print(f"Erreur refresh Toplevel: {e}")
                else:
                    # Chercher récursivement dans les enfants de la Toplevel
                    self._chercher_refresh_dans_enfants(fenetre)
    
    def _chercher_refresh_dans_enfants(self, widget):
        """Recherche récursivement un widget avec refresh_produits"""
        if hasattr(widget, 'refresh_produits'):
            try:
                widget.refresh_produits()
            except Exception as e:
                print(f"Erreur refresh enfant: {e}")
            return True
        
        if hasattr(widget, 'winfo_children'):
            for enfant in widget.winfo_children():
                if self._chercher_refresh_dans_enfants(enfant):
                    return True
        return False
    def toggle_fullscreen(self, event=None):
        """Basculer entre plein écran et mode fenêtré"""
        self.attributes('-fullscreen', not self.attributes('-fullscreen'))
        if not self.attributes('-fullscreen'):
            self.geometry("1200x720")
            center_window(self, 1200, 720)
    
    def quit_fullscreen(self, event=None):
        """Quitter le plein écran (touche Echap)"""
        if self.attributes('-fullscreen'):
            self.attributes('-fullscreen', False)
            self.geometry("1200x720")
            center_window(self, 1200, 720)

    def _build(self):
        # ✅ SIDEBAR AVEC SCROLL
        self.sidebar = tk.Frame(self, bg=CLR_SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # ✅ CANVAS + SCROLLBAR POUR LA SIDEBAR
        sidebar_canvas = tk.Canvas(self.sidebar, bg=CLR_SIDEBAR, highlightthickness=0, width=220)
        sidebar_scrollbar = tk.Scrollbar(self.sidebar, orient="vertical", command=sidebar_canvas.yview)
        sidebar_inner = tk.Frame(sidebar_canvas, bg=CLR_SIDEBAR)
        
        sidebar_inner.bind(
            "<Configure>",
            lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        )
        sidebar_canvas.create_window((0, 0), window=sidebar_inner, anchor="nw", width=218)
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scrollbar.pack(side="right", fill="y")
        
        # ✅ Raccourci pour la molette de souris dans la sidebar
        def _on_mousewheel_sidebar(event):
            sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        sidebar_canvas.bind("<MouseWheel>", _on_mousewheel_sidebar)
        sidebar_inner.bind("<MouseWheel>", _on_mousewheel_sidebar)
        
        # ✅ Utiliser sidebar_inner au lieu de sidebar pour le contenu
        logo_frame = tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, pady=20)
        logo_frame.pack(fill="x")
        lbl(logo_frame, "📦", 28).pack()
        lbl(logo_frame, "Gestion Stock", 12, True).pack()

        ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=5)

        self.nav_btns = {}
        nav_items = [
            ("🏠", "Tableau de Bord", "dashboard"),
            ("📦", "Produits", "produits"),
            ("💲", "Grille des Prix", "grille_prix"),
            ("👥", "Clients", "clients"),
            ("🏭", "Fournisseurs", "fournisseurs"),
            None,
            ("🧾", "Factures", "factures"),
            ("🛒", "Bons d'Achat", "bons_achat"),
            ("🏷️", "Bons de Vente", "bons_vente"),
            None,
            ("💳", "Versements Clients", "vers_clients"),
            ("💳", "Versements Fournis.", "vers_fourn"),
            None,
            ("↩️", "Retours Vente", "retours_vente"),
            ("↩️", "Retours Achat", "retours_achat"),
            None,
            ("📊", "Situation Clients", "sit_clients"),
            ("📊", "Situation Fournis.", "sit_fourn"),
            ("📊", "Stats Achats", "stats_achats"),
            ("📊", "Stats Ventes", "stats_ventes"),
            ("📊", "Analyse Produits", "analyse_produits"),  # NOUVEAU
            None,
            ("🏢", "Profils Entreprise", "profils")
        ]

        for item in nav_items:
            if item is None:
                ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=3)
                continue
            icon, label, key = item
            btn = tk.Button(sidebar_inner, text=f"  {icon}  {label}",
                anchor="w", bg=CLR_SIDEBAR, fg=CLR_MUTED,
                relief="flat", font=("Segoe UI", 8),
                padx=8, pady=4,
                cursor="hand2",
                command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=6, pady=1)
            btn.bind("<Enter>", lambda e,b=btn: b.config(bg=CLR_CARD, fg=CLR_TEXT) if self._active != b else None)
            btn.bind("<Leave>", lambda e,b=btn: b.config(bg=CLR_SIDEBAR, fg=CLR_MUTED) if self._active != b else None)
            self.nav_btns[key] = btn

        # ✅ Ajouter un espace en bas pour le scroll
        tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, height=20).pack()

        self._active = None
        self.main = tk.Frame(self, bg=CLR_BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.show_page("dashboard")

    def show_page(self, key):
        if self._active:
            self._active.config(bg=CLR_SIDEBAR, fg=CLR_MUTED)
        btn = self.nav_btns.get(key)
        if btn:
            btn.config(bg=CLR_ACCENT, fg="white")
            self._active = btn

        for w in self.main.winfo_children():
            w.pack_forget()

        if key not in self._pages:
            if key == "dashboard":
                self._pages[key] = DashboardPage(self.main)
            elif key == "produits":
                self._pages[key] = ProduitPage(self.main)
            elif key == "grille_prix":  # AJOUTER CE BLOC
                self._pages[key] = prix_niveaux.GrillePrixPage(self.main)
            elif key == "clients":
                self._pages[key] = TiersPage(self.main, "client")
            elif key == "fournisseurs":
                self._pages[key] = TiersPage(self.main, "fournisseur")
            elif key == "bons_achat":
                self._pages[key] = BonAchatPage(self.main)
            elif key == "bons_vente":
                self._pages[key] = BonVentePage(self.main)
            elif key == "factures":
                self._pages[key] = FacturePage(self.main)
            elif key == "vers_clients":
                self._pages[key] = VersementPage(self.main, "client")
            elif key == "vers_fourn":
                self._pages[key] = VersementPage(self.main, "fournisseur")
            elif key == "retours_vente":
                self._pages[key] = RetourPage(self.main, "vente")
            elif key == "retours_achat":
                self._pages[key] = RetourPage(self.main, "achat")
            elif key == "sit_clients":
                self._pages[key] = SituationPage(self.main, "client")
            elif key == "sit_fourn":
                self._pages[key] = SituationPage(self.main, "fournisseur")
            elif key == "profils":
                self._pages[key] = GestionProfilsPage(self.main)
            elif key == "stats_ventes":
                self._pages[key] = StatistiquesVentesPage(self.main)    
            elif key == "stats_achats":  # <-- NOUVEAU
                self._pages[key] = StatistiquesAchatsPage(self.main)
            elif key == "analyse_produits":
                self._pages[key] = AnalyseProduitsPage(self.main)    
        page = self._pages[key]
        page.pack(fill="both", expand=True)
        if hasattr(page, "refresh"):
            page.refresh()


class VersementPage(tk.Frame):
    """Page de gestion des versements clients/fournisseurs"""
    
    def __init__(self, parent, vers_type="client"):
        self.vers_type = vers_type  # "client" ou "fournisseur"
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.prefix = "VC" if vers_type == "client" else "VF"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        title = f"💳 Versements {self.tiers_label}s" if self.vers_type == "client" else f"💳 Versements Fournisseurs"
        lbl(hdr, title, 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Versement", command=self.nouveau_versement,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Filtres
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        lbl(sf, f"{self.tiers_label}:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.tiers_filter_var = tk.StringVar(value="Tous")
        self.load_tiers_list()
        tiers_combo = combo(sf, ["Tous"] + self.tiers_list, width=20, textvariable=self.tiers_filter_var)
        tiers_combo.pack(side="left", padx=5)
        tiers_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        lbl(sf, "Mode:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.mode_filter_var = tk.StringVar(value="Tous")
        mode_combo = combo(sf, ["Tous", "Espèces", "Chèque", "Virement", "Carte"], width=12, textvariable=self.mode_filter_var)
        mode_combo.pack(side="left", padx=5)
        mode_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Tableau
        cols = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        widths = [120, 100, 200, 120, 100, 150]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_versement,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_versement,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_versement,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_versements,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def load_tiers_list(self):
        conn = get_conn()
        tiers = conn.execute(f"SELECT nom FROM {self.tiers_table} ORDER BY nom").fetchall()
        conn.close()
        self.tiers_list = [t["nom"] for t in tiers]
    
    def refresh(self):
        q = self.search_var.get().lower()
        tiers_filter = self.tiers_filter_var.get()
        mode_filter = self.mode_filter_var.get()
        
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if self.vers_type == "client":
            query = f"""
                SELECT v.*, c.nom as tiers_nom
                FROM {self.table} v
                JOIN {self.tiers_table} c ON v.client_id = c.id
                ORDER BY v.date_vers DESC
            """
        else:
            query = f"""
                SELECT v.*, f.nom as tiers_nom
                FROM {self.table} v
                JOIN {self.tiers_table} f ON v.fournisseur_id = f.id
                ORDER BY v.date_vers DESC
            """
        rows = conn.execute(query).fetchall()
        conn.close()
        
        for r in rows:
            if q and q not in r["numero"].lower() and q not in r["tiers_nom"].lower():
                continue
            if tiers_filter != "Tous" and r["tiers_nom"] != tiers_filter:
                continue
            if mode_filter != "Tous" and r["mode"] != mode_filter:
                continue
            
            self.tree.insert("", "end", iid=r["id"], values=(
                r["numero"], r["date_vers"], r["tiers_nom"],
                f"{r['montant']:,.2f} DA", r["mode"], r["reference"] or ""
            ))
    
    def nouveau_versement(self):
        d = VersementDialog(self, self.vers_type)
        self.wait_window(d)
        self.load_tiers_list()
        self.refresh()
    
    def view_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        d = VersementDetailDialog(self, self.vers_type, sel[0])
        self.wait_window(d)
    
    def edit_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        d = VersementEditDialog(self, self.vers_type, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        
        if messagebox.askyesno("Confirmation", "⚠️ Supprimer ce versement ?\nLe solde sera recalculé."):
            conn = get_conn()
            try:
                vers_id = sel[0]
                # Récupérer les infos avant suppression
                if self.vers_type == "client":
                    vers = conn.execute(f"SELECT client_id, montant FROM {self.table} WHERE id=?", (vers_id,)).fetchone()
                    if vers:
                        # Recalculer le solde client
                        conn.execute(f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?", 
                                   (vers["montant"], vers["client_id"]))
                else:
                    vers = conn.execute(f"SELECT fournisseur_id, montant FROM {self.table} WHERE id=?", (vers_id,)).fetchone()
                    if vers:
                        conn.execute(f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?", 
                                   (vers["montant"], vers["fournisseur_id"]))
                
                conn.execute(f"DELETE FROM {self.table} WHERE id=?", (vers_id,))
                conn.commit()
                messagebox.showinfo("Succès", "Versement supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                conn.rollback()
            finally:
                conn.close()
    
    def print_versements(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        headers = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        print_preview(data, f"LISTE DES VERSEMENTS {self.tiers_label.upper()}S", headers)


class VersementDialog(tk.Toplevel):
    """Dialogue de création de versement"""
    
    def __init__(self, parent, vers_type):
        super().__init__(parent)
        self.vers_type = vers_type
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.prefix = "VC" if vers_type == "client" else "VF"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        
        self.title(f"Nouveau Versement - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        self.geometry("500x450")
        self._build()
        center_window(self, 500, 450)
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"💰 NOUVEAU VERSEMENT {self.tiers_label.upper()}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Formulaire
        form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="x", pady=10)
        
        # Numéro (auto)
        row1 = tk.Frame(form_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        lbl(row1, "Numéro:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.num_var = tk.StringVar(value=next_numero(self.prefix, self.table))
        entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
        
        # Date
        lbl(row1, "Date:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        entry(row1, width=15, textvariable=self.date_var).pack(side="left", padx=10)
        
        # Sélection tiers
        row2 = tk.Frame(form_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        lbl(row2, f"{self.tiers_label}:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.tiers_table} ORDER BY nom").fetchall()
        conn.close()
        
        self.tiers_map = {t["nom"]: {"id": t["id"], "solde": t["solde"]} for t in tiers}
        self.tiers_var = tk.StringVar()
        tiers_combo = combo(row2, list(self.tiers_map.keys()), width=30, textvariable=self.tiers_var)
        tiers_combo.pack(side="left", padx=10)
        self.tiers_var.trace_add("write", self.on_tiers_selected)
        
        # Solde affiché
        row3 = tk.Frame(form_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        lbl(row3, "Solde actuel:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.solde_var = tk.StringVar(value="0.00 DA")
        # CORRECTION ICI - Utiliser tk.Label au lieu de lbl()
        tk.Label(row3, textvariable=self.solde_var, bg=CLR_CARD, fg=CLR_ORANGE, 
                font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        
        # Montant
        row4 = tk.Frame(form_frame, bg=CLR_CARD)
        row4.pack(fill="x", pady=5)
        lbl(row4, "Montant:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.montant_var = tk.StringVar()
        entry(row4, width=15, textvariable=self.montant_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        lbl(row4, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        # Mode de paiement
        row5 = tk.Frame(form_frame, bg=CLR_CARD)
        row5.pack(fill="x", pady=5)
        lbl(row5, "Mode:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.mode_var = tk.StringVar(value="Espèces")
        mode_combo = combo(row5, ["Espèces", "Chèque", "Virement", "Carte"], width=15, textvariable=self.mode_var)
        mode_combo.pack(side="left", padx=10)
        
        # Référence
        row6 = tk.Frame(form_frame, bg=CLR_CARD)
        row6.pack(fill="x", pady=5)
        lbl(row6, "Référence:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.ref_var = tk.StringVar()
        entry(row6, width=30, textvariable=self.ref_var).pack(side="left", padx=10)
        
        # Nouveau solde après versement
        row7 = tk.Frame(form_frame, bg=CLR_CARD)
        row7.pack(fill="x", pady=(10,5))
        lbl(row7, "Nouveau solde:", 10, True, CLR_MUTED).pack(side="left", padx=5)
        self.nouveau_solde_var = tk.StringVar(value="0.00 DA")
        # CORRECTION ICI - Utiliser tk.Label au lieu de lbl()
        tk.Label(row7, textvariable=self.nouveau_solde_var, bg=CLR_CARD, fg=CLR_GREEN,
                font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        
        self.montant_var.trace_add("write", self.calculer_nouveau_solde)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="✅ ENREGISTRER", command=self.save,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    def on_tiers_selected(self, *args):
        tiers_nom = self.tiers_var.get()
        if tiers_nom in self.tiers_map:
            solde = self.tiers_map[tiers_nom]["solde"]
            self.solde_var.set(f"{solde:,.2f} DA")
            self.calculer_nouveau_solde()
    
    def calculer_nouveau_solde(self, *args):
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            return
        try:
            montant = parse_decimal(self.montant_var.get() or "0")
            solde_actuel = self.tiers_map[tiers_nom]["solde"]
            if self.vers_type == "client":
                nouveau_solde = solde_actuel - montant
            else:
                nouveau_solde = solde_actuel - montant
            self.nouveau_solde_var.set(f"{nouveau_solde:,.2f} DA")
        except (ValueError, KeyError):
            pass
    
    def save(self):
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", f"Sélectionnez un {self.tiers_label.lower()}")
            return
        
        try:
            montant = parse_decimal(self.montant_var.get() or "0")
            if montant <= 0:
                messagebox.showerror("Erreur", "Montant invalide")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide")
            return
        
        if not valider_date(self.date_var.get()):
            messagebox.showerror("Erreur", "Format de date invalide (YYYY-MM-DD)")
            return
        
        tiers_id = self.tiers_map[tiers_nom]["id"]
        
        conn = get_conn()
        try:
            # Insérer le versement
            if self.vers_type == "client":
                conn.execute(f"""
                    INSERT INTO {self.table}(numero, date_vers, client_id, montant, mode, reference)
                    VALUES(?, ?, ?, ?, ?, ?)
                """, (self.num_var.get(), self.date_var.get(), tiers_id, montant, 
                      self.mode_var.get(), self.ref_var.get() or None))
            else:
                conn.execute(f"""
                    INSERT INTO {self.table}(numero, date_vers, fournisseur_id, montant, mode, reference)
                    VALUES(?, ?, ?, ?, ?, ?)
                """, (self.num_var.get(), self.date_var.get(), tiers_id, montant,
                      self.mode_var.get(), self.ref_var.get() or None))
            
            # Mettre à jour le solde
            conn.execute(f"UPDATE {self.tiers_table} SET solde = solde - ? WHERE id=?", (montant, tiers_id))
            
            conn.commit()
            messagebox.showinfo("Succès", f"Versement {self.num_var.get()} enregistré !")
            self.destroy()
        except sqlite3.IntegrityError:
            nouveau_num = next_numero(self.prefix, self.table)
            self.num_var.set(nouveau_num)
            messagebox.showwarning("Numéro dupliqué", f"Nouveau numéro: {nouveau_num}")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()


class VersementEditDialog(tk.Toplevel):
    """Dialogue de modification de versement"""
    
    def __init__(self, parent, vers_type, vers_id):
        super().__init__(parent)
        self.vers_type = vers_type
        self.vers_id = vers_id
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        
        self.title(f"Modifier Versement - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        self.geometry("500x450")
        self._load_data()
        self._build()
        center_window(self, 500, 450)
    
    def _load_data(self):
        conn = get_conn()
        self.versement = conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (self.vers_id,)).fetchone()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏ MODIFIER VERSEMENT", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="x", pady=10)
        
        # Numéro (non modifiable)
        row1 = tk.Frame(form_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        lbl(row1, "Numéro:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.num_var = tk.StringVar(value=self.versement["numero"])
        entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
        
        # Date
        lbl(row1, "Date:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
        self.date_var = tk.StringVar(value=self.versement["date_vers"])
        entry(row1, width=15, textvariable=self.date_var).pack(side="left", padx=10)
        
        # Montant
        row2 = tk.Frame(form_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        lbl(row2, "Montant:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.montant_var = tk.StringVar(value=f"{self.versement['montant']:.2f}")
        entry(row2, width=15, textvariable=self.montant_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        lbl(row2, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        # Mode
        row3 = tk.Frame(form_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        lbl(row3, "Mode:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.mode_var = tk.StringVar(value=self.versement["mode"])
        mode_combo = combo(row3, ["Espèces", "Chèque", "Virement", "Carte"], width=15, textvariable=self.mode_var)
        mode_combo.pack(side="left", padx=10)
        
        # Référence
        row4 = tk.Frame(form_frame, bg=CLR_CARD)
        row4.pack(fill="x", pady=5)
        lbl(row4, "Référence:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.ref_var = tk.StringVar(value=self.versement["reference"] or "")
        entry(row4, width=30, textvariable=self.ref_var).pack(side="left", padx=10)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def save(self):
        try:
            montant = parse_decimal(self.montant_var.get() or "0")
            if montant <= 0:
                messagebox.showerror("Erreur", "Montant invalide")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide")
            return
        
        if not valider_date(self.date_var.get()):
            messagebox.showerror("Erreur", "Format de date invalide")
            return
        
        conn = get_conn()
        try:
            # Récupérer l'ancien montant
            old_vers = conn.execute(f"SELECT montant FROM {self.table} WHERE id=?", (self.vers_id,)).fetchone()
            delta = montant - old_vers["montant"]
            
            # Mettre à jour le versement
            conn.execute(f"""
                UPDATE {self.table} 
                SET date_vers=?, montant=?, mode=?, reference=?
                WHERE id=?
            """, (self.date_var.get(), montant, self.mode_var.get(), 
                  self.ref_var.get() or None, self.vers_id))
            
            # Ajuster le solde du tiers
            if self.vers_type == "client":
                conn.execute(f"UPDATE {self.tiers_table} SET solde = solde - ? WHERE id=?", 
                           (delta, self.versement["client_id"]))
            else:
                conn.execute(f"UPDATE {self.tiers_table} SET solde = solde - ? WHERE id=?", 
                           (delta, self.versement["fournisseur_id"]))
            
            conn.commit()
            messagebox.showinfo("Succès", "Versement modifié !")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()


class VersementDetailDialog(tk.Toplevel):
    """Dialogue de détail de versement"""
    
    def __init__(self, parent, vers_type, vers_id):
        super().__init__(parent)
        self.vers_type = vers_type
        self.vers_id = vers_id
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        
        self.title(f"Détail Versement - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        self.geometry("600x400")
        self._load_data()
        self._build()
        center_window(self, 600, 400)
    
    def _load_data(self):
        conn = get_conn()
        if self.vers_type == "client":
            self.versement = conn.execute(f"""
                SELECT v.*, c.nom as tiers_nom, c.solde
                FROM {self.table} v
                JOIN {self.tiers_table} c ON v.client_id = c.id
                WHERE v.id = ?
            """, (self.vers_id,)).fetchone()
        else:
            self.versement = conn.execute(f"""
                SELECT v.*, f.nom as tiers_nom, f.solde
                FROM {self.table} v
                JOIN {self.tiers_table} f ON v.fournisseur_id = f.id
                WHERE v.id = ?
            """, (self.vers_id,)).fetchone()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"📄 DÉTAIL VERSEMENT", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        info_frame.pack(fill="x", pady=10)
        
        details = [
            ("Numéro:", self.versement["numero"]),
            ("Date:", self.versement["date_vers"]),
            (f"{self.tiers_label}:", self.versement["tiers_nom"]),
            ("Montant:", f"{self.versement['montant']:,.2f} DA"),
            ("Mode:", self.versement["mode"]),
            ("Référence:", self.versement["reference"] or "-"),
            ("Solde après versement:", f"{self.versement['solde']:,.2f} DA"),
        ]
        
        for i, (label, value) in enumerate(details):
            row = tk.Frame(info_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=4)
            lbl(row, label, 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            lbl(row, str(value), 9, False, CLR_TEXT).pack(side="left", padx=5)
        
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_versement,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="right", padx=10)
    
    def print_versement(self):
        data = [[
            self.versement["numero"],
            self.versement["date_vers"],
            self.versement["tiers_nom"],
            f"{self.versement['montant']:,.2f} DA",
            self.versement["mode"],
            self.versement["reference"] or "-"
        ]]
        headers = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        print_preview(data, f"VERSEMENT N°{self.versement['numero']}", headers)

class RetourPage(tk.Frame):
    """Page de gestion des retours (vente/achat)"""
    
    def __init__(self, parent, retour_type="vente"):
        self.retour_type = retour_type  # "vente" ou "achat"
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        self.bons_table = "bons_vente" if retour_type == "vente" else "bons_achat"
        self.tiers_table = "clients" if retour_type == "vente" else "fournisseurs"
        self.produits_table = "produits"
        self.prefix = "RV" if retour_type == "vente" else "RA"
        self.tiers_label = "Client" if retour_type == "vente" else "Fournisseur"
        
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        title = f"↩️ Retours {self.tiers_label}s" if self.retour_type == "vente" else "↩️ Retours Fournisseurs"
        lbl(hdr, title, 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Retour", command=self.nouveau_retour,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Recherche
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        # Tableau
        cols = ["Numéro", "Date", self.tiers_label, "Total", "Motif", "Bon associé"]
        widths = [120, 100, 200, 100, 150, 120]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_retour,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_retour,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_retour,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_retours,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def refresh(self):
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if self.retour_type == "vente":
            query = f"""
                SELECT r.*, c.nom as tiers_nom, bv.numero as bon_numero
                FROM {self.table} r
                JOIN {self.tiers_table} c ON r.client_id = c.id
                LEFT JOIN {self.bons_table} bv ON r.bon_vente_id = bv.id
                ORDER BY r.date_retour DESC
            """
        else:
            query = f"""
                SELECT r.*, f.nom as tiers_nom, ba.numero as bon_numero
                FROM {self.table} r
                JOIN {self.tiers_table} f ON r.fournisseur_id = f.id
                LEFT JOIN {self.bons_table} ba ON r.bon_achat_id = ba.id
                ORDER BY r.date_retour DESC
            """
        rows = conn.execute(query).fetchall()
        conn.close()
        
        for r in rows:
            if q and q not in r["numero"].lower() and q not in r["tiers_nom"].lower():
                continue
            
            self.tree.insert("", "end", iid=r["id"], values=(
                r["numero"], r["date_retour"], r["tiers_nom"],
                f"{r['total']:,.2f} DA", r["motif"] or "-", r["bon_numero"] or "-"
            ))
    
    def nouveau_retour(self):
        d = RetourDialog(self, self.retour_type)
        self.wait_window(d)
        self.refresh()
    
    def view_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return
        d = RetourDetailDialog(self, self.retour_type, sel[0])
        self.wait_window(d)
    
    def edit_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return
        d = RetourEditDialog(self, self.retour_type, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return

        if not messagebox.askyesno("Confirmation", "⚠️ Supprimer ce retour ?\nLe stock sera recalculé."):
            return

        conn = get_conn()
        try:
            retour_id = sel[0]

            # Récupérer le retour AVANT de supprimer les lignes
            retour = conn.execute(
                f"SELECT * FROM {self.table} WHERE id=?", (retour_id,)
            ).fetchone()

            lignes = conn.execute(
                f"SELECT * FROM {self.lignes_table} WHERE retour_id=?", (retour_id,)
            ).fetchall()

            for l in lignes:
                if self.retour_type == "vente":
                    # ✅ CORRECTION : supprimer un retour vente = annuler ce retour
                    # Le retour avait remis les articles EN stock → on les ressort
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])
                    
                    # Recalculer le PMP après la sortie
                    produit = conn.execute(
                        "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
                        (l["produit_id"],)
                    ).fetchone()
                    if produit["stock_actuel"] > 0:
                        nouveau_pmp = produit["cout_total_stock"] / produit["stock_actuel"]
                        conn.execute(
                            "UPDATE produits SET prix_moyen_pondere = ? WHERE id=?",
                            (nouveau_pmp, l["produit_id"])
                        )
                    else:
                        conn.execute(
                            "UPDATE produits SET prix_moyen_pondere = 0, cout_total_stock = 0 WHERE id=?",
                            (l["produit_id"],)
                        )

                else:
                    # ✅ CORRECTION : supprimer un retour achat = annuler ce retour
                    # Le retour avait retiré les articles du stock → on les remet
                    nouveau_pmp, nouveau_cout = calculer_pmp(
                        conn, l["produit_id"], l["quantite"], l["prix_unitaire"]
                    )
                    conn.execute(
                        """UPDATE produits
                        SET stock_actuel       = stock_actuel + ?,
                            prix_moyen_pondere = ?,
                            cout_total_stock   = ?
                        WHERE id = ?""",
                        (l["quantite"], nouveau_pmp, nouveau_cout, l["produit_id"])
                    )

            # ✅ CORRECTION : ajuster le solde dans le bon sens selon le type
            if self.retour_type == "vente":
                # Le retour avait diminué le solde client → supprimer le retour
                # remet le client débiteur → solde remonte
                conn.execute(
                    f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?",
                    (retour["total"], retour["client_id"])
                )
            else:
                # Le retour avait diminué le solde fournisseur → supprimer le retour
                # remet le fournisseur créditeur → solde remonte
                conn.execute(
                    f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?",
                    (retour["total"], retour["fournisseur_id"])
                )

            # Supprimer les lignes puis le retour
            conn.execute(f"DELETE FROM {self.lignes_table} WHERE retour_id=?", (retour_id,))
            conn.execute(f"DELETE FROM {self.table} WHERE id=?", (retour_id,))

            conn.commit()
            messagebox.showinfo("Succès", "Retour supprimé et stock recalculé")
            self.refresh()

        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def print_retours(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        headers = ["Numéro", "Date", self.tiers_label, "Total", "Motif", "Bon associé"]
        print_preview(data, f"LISTE DES RETOURS", headers)

class RetourDialog(tk.Toplevel):
    """Dialogue de création de retour"""
    
    def __init__(self, parent, retour_type):
        super().__init__(parent)
        self.retour_type = retour_type
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        self.bons_table = "bons_vente" if retour_type == "vente" else "bons_achat"
        self.tiers_table = "clients" if retour_type == "vente" else "fournisseurs"
        self.prefix = "RV" if retour_type == "vente" else "RA"
        self.tiers_label = "Client" if retour_type == "vente" else "Fournisseur"
        
        self.lignes = []
        self.bon_selected = None
        
        self.title(f"Nouveau Retour - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        
        # MAXIMISER AVEC BARRE DES TÂCHES VISIBLE
        self.state('zoomed')
        
        self._build()
        self.update_idletasks()
    
    def _build(self):
        # CONTENEUR PRINCIPAL
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True)
        
        # CONTENU PRINCIPAL AVEC PADDING
        main_frame = tk.Frame(main_container, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"↩️ NOUVEAU RETOUR {self.tiers_label.upper()}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Section bon associé
        bon_frame = tk.LabelFrame(main_frame, text="1. Bon associé (optionnel)", 
                                  bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                  padx=15, pady=10)
        bon_frame.pack(fill="x", pady=10)
        
        lbl(bon_frame, f"Bon de {self.tiers_label}:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        if self.retour_type == "vente":
            bons = conn.execute(f"""
                SELECT b.id, b.numero, c.nom as tiers_nom, b.total, b.date_bon
                FROM {self.bons_table} b
                JOIN {self.tiers_table} c ON b.client_id = c.id
                WHERE b.statut = 'Validé'
                ORDER BY b.date_bon DESC
            """).fetchall()
        else:
            bons = conn.execute(f"""
                SELECT b.id, b.numero, f.nom as tiers_nom, b.total, b.date_bon
                FROM {self.bons_table} b
                JOIN {self.tiers_table} f ON b.fournisseur_id = f.id
                WHERE b.statut = 'Validé'
                ORDER BY b.date_bon DESC
            """).fetchall()
        conn.close()
        
        self.bons_map = {}
        bon_liste = ["-- Aucun --"]
        for b in bons:
            display = f"{b['numero']} - {b['tiers_nom']} - {b['total']:,.2f} DA"
            self.bons_map[display] = dict(b)
            bon_liste.append(display)
        
        self.bon_var = tk.StringVar(value="-- Aucun --")
        bon_combo = combo(bon_frame, bon_liste, width=40, textvariable=self.bon_var)
        bon_combo.pack(side="left", padx=10, fill="x", expand=True)
        self.bon_var.trace_add("write", self.on_bon_selected)
        
        # Sélecteur de tiers direct
        tiers_direct_frame = tk.Frame(bon_frame, bg=CLR_CARD)
        tiers_direct_frame.pack(fill="x", pady=5)

        lbl(tiers_direct_frame, f"— ou choisir {self.tiers_label} directement:", 
            9, False, CLR_MUTED).pack(side="left", padx=5)

        conn = get_conn()
        tiers_rows = conn.execute(
            f"SELECT id, nom FROM {self.tiers_table} ORDER BY nom"
        ).fetchall()
        conn.close()

        self.tiers_direct_map = {t["nom"]: t["id"] for t in tiers_rows}
        self.tiers_id_sans_bon = None
        self.tiers_direct_var = tk.StringVar()

        tiers_direct_combo = combo(
            tiers_direct_frame,
            list(self.tiers_direct_map.keys()),
            width=25,
            textvariable=self.tiers_direct_var
        )
        tiers_direct_combo.pack(side="left", padx=10)

        def on_tiers_direct(*_):
            nom = self.tiers_direct_var.get()
            self.tiers_id_sans_bon = self.tiers_direct_map.get(nom)

        self.tiers_direct_var.trace_add("write", on_tiers_direct)
        
        # ✅ Section produit à retourner - TOUT SUR UNE SEULE LIGNE
        prod_frame = tk.LabelFrame(main_frame, text="2. Produit à retourner", 
                                   bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                   padx=15, pady=10)
        prod_frame.pack(fill="x", pady=10)
        
        # ✅ LIGNE UNIQUE POUR TOUS LES CHAMPS + BOUTON AJOUTER
        row_saisie = tk.Frame(prod_frame, bg=CLR_CARD)
        row_saisie.pack(fill="x", pady=5)
        
        # Produit
        lbl(row_saisie, "Produit:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        prods = conn.execute("SELECT id, code, designation, prix_vente, unite, stock_actuel FROM produits WHERE actif = 1 ORDER BY designation").fetchall()
        conn.close()
        
        self.prod_map = {}
        prod_liste = []
        for p in prods:
            display = f"{p['code']} - {p['designation']}"
            self.prod_map[display] = dict(p)
            prod_liste.append(display)
        
        self.prod_var = tk.StringVar()
        prod_combo = combo(row_saisie, prod_liste, width=25, textvariable=self.prod_var)
        prod_combo.pack(side="left", padx=5)
        
        # Quantité
        lbl(row_saisie, "Qté:", 9, False, CLR_MUTED).pack(side="left", padx=(10,5))
        self.qty_var = tk.StringVar(value="1")
        entry(row_saisie, width=6, textvariable=self.qty_var).pack(side="left", padx=5)
        
        # Prix unitaire
        lbl(row_saisie, "Prix:", 9, False, CLR_MUTED).pack(side="left", padx=(10,5))
        self.prix_var = tk.StringVar()
        entry(row_saisie, width=10, textvariable=self.prix_var).pack(side="left", padx=5)
        lbl(row_saisie, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        # ✅ BOUTON AJOUTER EN LIGNE (à droite)
        btn_ajouter = tk.Button(row_saisie, text="➕ AJOUTER", command=self.ajouter_ligne,
                               bg=CLR_GREEN, fg="white", relief="flat", 
                               font=("Segoe UI", 9, "bold"),
                               padx=12, pady=4, cursor="hand2")
        btn_ajouter.pack(side="right", padx=5)
        
        # ✅ Motif sur une ligne séparée (en dessous)
        row_motif = tk.Frame(prod_frame, bg=CLR_CARD)
        row_motif.pack(fill="x", pady=5)
        lbl(row_motif, "Motif du retour:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.motif_var = tk.StringVar()
        entry(row_motif, width=60, textvariable=self.motif_var).pack(side="left", padx=10, fill="x", expand=True)
        
        # ✅ CONTENEUR TABLEAU + BOUTONS DROITE (Layout horizontal)
        content_frame = tk.Frame(main_frame, bg=CLR_BG)
        content_frame.pack(fill="both", expand=True, pady=10)
        
        # ✅ TABLEAU À GAUCHE
        tableau_frame = tk.Frame(content_frame, bg=CLR_BG)
        tableau_frame.pack(side="left", fill="both", expand=True)
        
        cols = ["Produit", "Quantité", "Prix unitaire", "Total"]
        widths = [400, 100, 120, 150]
        tf, self.tree = make_tree(tableau_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # ✅ PANEL DES BOUTONS À DROITE
        panel_droite = tk.Frame(content_frame, bg=CLR_BG, width=250)
        panel_droite.pack(side="right", fill="y", padx=(10, 0))
        panel_droite.pack_propagate(False)
        
        # ✅ CADRE DES BOUTONS D'ACTION
        actions_frame = tk.LabelFrame(panel_droite, text="⚡ ACTIONS", 
                                     bg=CLR_CARD, fg=CLR_ACCENT,
                                     font=("Segoe UI", 10, "bold"),
                                     padx=10, pady=8)
        actions_frame.pack(fill="x", pady=5)
        
        # Bouton Retirer ligne
        btn_retirer = tk.Button(actions_frame, text="🗑 Retirer ligne", command=self.retirer_ligne,
                               bg=CLR_RED, fg="white", relief="flat", 
                               font=("Segoe UI", 9, "bold"), padx=10, pady=6,
                               cursor="hand2", width=16)
        btn_retirer.pack(pady=3)
        
        # Bouton Vider tout
        btn_vider = tk.Button(actions_frame, text="🗑 Vider tout", command=self.vider_panier,
                             bg=CLR_ORANGE, fg="white", relief="flat", 
                             font=("Segoe UI", 9, "bold"), padx=10, pady=6,
                             cursor="hand2", width=16)
        btn_vider.pack(pady=3)
        
        # ✅ CADRE RÉCAPITULATIF
        recap_frame = tk.LabelFrame(panel_droite, text="📊 RÉCAPITULATIF", 
                                   bg=CLR_CARD, fg=CLR_GREEN,
                                   font=("Segoe UI", 10, "bold"),
                                   padx=10, pady=8)
        recap_frame.pack(fill="x", pady=5)
        
        # Total
        row_total = tk.Frame(recap_frame, bg=CLR_CARD)
        row_total.pack(fill="x", pady=3)
        lbl(row_total, "Total:", 10, True, CLR_MUTED).pack(side="left")
        self.total_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_total, textvariable=self.total_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 14, "bold")).pack(side="right")
        
        # Nombre de lignes
        row_nb = tk.Frame(recap_frame, bg=CLR_CARD)
        row_nb.pack(fill="x", pady=3)
        lbl(row_nb, "Lignes:", 9, True, CLR_MUTED).pack(side="left")
        self.nb_lignes_var = tk.StringVar(value="0")
        tk.Label(row_nb, textvariable=self.nb_lignes_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 11, "bold")).pack(side="right")
        
        # ✅ CADRE BOUTONS DE VALIDATION
        validation_frame = tk.LabelFrame(panel_droite, text="✅ VALIDATION", 
                                        bg=CLR_CARD, fg=CLR_GREEN,
                                        font=("Segoe UI", 10, "bold"),
                                        padx=10, pady=8)
        validation_frame.pack(fill="x", pady=5)
        
        # Bouton VALIDER
        btn_valider = tk.Button(validation_frame, text="✅ VALIDER", 
                               command=self.save,
                               bg=CLR_GREEN, fg="white", relief="flat", 
                               font=("Segoe UI", 10, "bold"),
                               padx=15, pady=10, cursor="hand2", width=16)
        btn_valider.pack(pady=3)
        
        # Bouton ANNULER
        btn_annuler = tk.Button(validation_frame, text="❌ ANNULER", 
                               command=self.destroy,
                               bg=CLR_RED, fg="white", relief="flat", 
                               font=("Segoe UI", 10, "bold"),
                               padx=15, pady=10, cursor="hand2", width=16)
        btn_annuler.pack(pady=3)
        
        # ✅ Raccourcis clavier
        shortcuts_frame = tk.Frame(panel_droite, bg=CLR_BG)
        shortcuts_frame.pack(fill="x", pady=(5, 0))
        tk.Label(shortcuts_frame, 
                text="Entrée (Ajouter) | Suppr (Retirer)", 
                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 8)).pack()
        
        # Bindings des raccourcis clavier
        self.bind('<Return>', lambda e: self.ajouter_ligne())
        self.bind('<Delete>', lambda e: self.retirer_ligne())
        
        # ✅ Initialisation
        self.refresh_panier()
    
    def on_bon_selected(self, *args):
        key = self.bon_var.get()
        if key != "-- Aucun --" and key in self.bons_map:
            self.bon_selected = self.bons_map[key]
    
    def ajouter_ligne(self):
        prod_key = self.prod_var.get()
        if not prod_key or prod_key not in self.prod_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit")
            return
        
        try:
            qty = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide")
            return
        
        if qty <= 0:
            messagebox.showerror("Erreur", "Quantité > 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix > 0")
            return
        
        prod = self.prod_map[prod_key]

        
        total = qty * prix
        
        self.lignes.append({
            "produit_id": prod["id"],
            "designation": prod_key,
            "quantite": qty,
            "prix": prix,
            "total": total
        })
        
        self.refresh_panier()
        self.qty_var.set("1")
        self.prix_var.set("")
    
    def retirer_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self.refresh_panier()
    
    def vider_panier(self):
        if not self.lignes:
            messagebox.showinfo("Information", "Le panier est déjà vide")
            return
        if messagebox.askyesno("Confirmation", "Vider tout le panier ?"):
            self.lignes = []
            self.refresh_panier()
    
    def refresh_panier(self):
        self.tree.delete(*self.tree.get_children())
        total = 0
        for i, l in enumerate(self.lignes):
            self.tree.insert("", "end", iid=str(i), values=(
                l["designation"],
                f"{l['quantite']:.2f}",
                f"{l['prix']:.2f}",
                f"{l['total']:.2f}"
            ))
            total += l["total"]
        self.total_var.set(f"{total:,.2f} DA")
        self.nb_lignes_var.set(str(len(self.lignes)))
    
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins un produit")
            return
        
        total = sum(l["total"] for l in self.lignes)
        num = next_numero(self.prefix, self.table)
        dt = date.today().strftime("%Y-%m-%d")
        motif = self.motif_var.get().strip()
        
        # Distinguer ID du bon et ID du tiers
        if self.bon_selected:
            bon_id = self.bon_selected["id"]
            
            conn_tmp = get_conn()
            if self.retour_type == "vente":
                row = conn_tmp.execute(
                    "SELECT client_id FROM bons_vente WHERE id=?", (bon_id,)
                ).fetchone()
                tiers_id = row["client_id"] if row else None
            else:
                row = conn_tmp.execute(
                    "SELECT fournisseur_id FROM bons_achat WHERE id=?", (bon_id,)
                ).fetchone()
                tiers_id = row["fournisseur_id"] if row else None
            conn_tmp.close()
            
            if not tiers_id:
                messagebox.showerror("Erreur", "Impossible de retrouver le tiers du bon")
                return
        else:
            if not hasattr(self, 'tiers_id_sans_bon') or not self.tiers_id_sans_bon:
                messagebox.showerror(
                    "Erreur",
                    f"Sélectionnez un {self.tiers_label} ou un bon associé."
                )
                return
            tiers_id = self.tiers_id_sans_bon
            bon_id = None
        
        conn = get_conn()
        try:
            if self.retour_type == "vente":
                conn.execute(
                    "INSERT INTO retours_vente(numero, date_retour, bon_vente_id, "
                    "client_id, total, motif) VALUES(?,?,?,?,?,?)",
                    (num, dt, bon_id, tiers_id, total, motif)
                )
            else:
                conn.execute(
                    "INSERT INTO retours_achat(numero, date_retour, bon_achat_id, "
                    "fournisseur_id, total, motif) VALUES(?,?,?,?,?,?)",
                    (num, dt, bon_id, tiers_id, total, motif)
                )
            
            retour_id = conn.execute(
                f"SELECT id FROM {self.table} WHERE numero=?", (num,)
            ).fetchone()["id"]
            
            for l in self.lignes:
                conn.execute(
                    f"INSERT INTO {self.lignes_table}"
                    "(retour_id, produit_id, quantite, prix_unitaire, total) "
                    "VALUES(?,?,?,?,?)",
                    (retour_id, l["produit_id"], l["quantite"], l["prix"], l["total"])
                )
                if self.retour_type == "vente":
                    # ✅ CORRECTION : réintégrer au PMP réel du produit, pas au prix de vente
                    # (le prix de vente inclut la marge, il ne représente pas le coût du stock)
                    entree_stock_annulation_vente(conn, l["produit_id"], l["quantite"])
                    # Diminuer le solde client (retour = moins de dette)
                    conn.execute(
                        "UPDATE clients SET solde = solde - ? WHERE id=?",
                        (l["total"], tiers_id)
                    )
                else:  # Retour achat
                    # ✅ CORRECTION : Utiliser recalculer_cout_stock_apres_sortie()
                    conn.execute(
                        "UPDATE produits SET stock_actuel = stock_actuel - ? WHERE id=?",
                        (l["quantite"], l["produit_id"])
                    )
                    # Recalculer le cout et le PMP après la sortie
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])
                    # Recalculer le PMP
                    recalculer_pmp_apres_sortie_complete(conn, l["produit_id"])
                    # Diminuer le solde fournisseur (retour = moins de dette)
                    conn.execute(
                        "UPDATE fournisseurs SET solde = solde - ? WHERE id=?",
                        (l["total"], tiers_id)
                    )
                
                conn.commit()
                messagebox.showinfo("Succès", f"Retour {num} enregistré avec succès !")
                self.destroy()
        except Exception as e:
                messagebox.showerror("Erreur", str(e))
                conn.rollback()
        finally:
                conn.close()

class RetourDetailDialog(tk.Toplevel):
    """Dialogue de détail d'un retour"""
    
    def __init__(self, parent, retour_type, retour_id):
        super().__init__(parent)
        self.retour_type = retour_type
        self.retour_id = retour_id
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        self.tiers_table = "clients" if retour_type == "vente" else "fournisseurs"
        
        self.title(f"Détail Retour")
        self.configure(bg=CLR_BG)
        self.geometry("800x600")
        self._load_data()
        self._build()
        center_window(self, 800, 600)
    
    def _load_data(self):
        conn = get_conn()
        if self.retour_type == "vente":
            self.retour = conn.execute(f"""
                SELECT r.*, c.nom as tiers_nom
                FROM {self.table} r
                JOIN {self.tiers_table} c ON r.client_id = c.id
                WHERE r.id = ?
            """, (self.retour_id,)).fetchone()
            
            self.lignes = conn.execute(f"""
                SELECT l.*, p.designation, p.unite
                FROM {self.lignes_table} l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.retour_id = ?
            """, (self.retour_id,)).fetchall()
        else:
            self.retour = conn.execute(f"""
                SELECT r.*, f.nom as tiers_nom
                FROM {self.table} r
                JOIN {self.tiers_table} f ON r.fournisseur_id = f.id
                WHERE r.id = ?
            """, (self.retour_id,)).fetchone()
            
            self.lignes = conn.execute(f"""
                SELECT l.*, p.designation, p.unite
                FROM {self.lignes_table} l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.retour_id = ?
            """, (self.retour_id,)).fetchall()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        title = "RETOUR CLIENT" if self.retour_type == "vente" else "RETOUR FOURNISSEUR"
        lbl(main_frame, f"📄 {title}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Informations
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        info_frame.pack(fill="x", pady=10)
        
        details = [
            ("Numéro:", self.retour["numero"]),
            ("Date:", self.retour["date_retour"]),
            (f"{'Client' if self.retour_type == 'vente' else 'Fournisseur'}:", self.retour["tiers_nom"]),
            ("Total:", f"{self.retour['total']:,.2f} DA"),
            ("Motif:", self.retour["motif"] or "-"),
        ]
        
        for i, (label, value) in enumerate(details):
            row = tk.Frame(info_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=4)
            lbl(row, label, 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            lbl(row, str(value), 9, False, CLR_TEXT).pack(side="left", padx=5)
        
        # Tableau des produits retournés
        table_frame = tk.LabelFrame(main_frame, text="Produits retournés", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ["Produit", "Quantité", "Unité", "Prix unitaire", "Total"]
        widths = [350, 80, 60, 100, 120]
        tf, tree = make_tree(table_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        for l in self.lignes:
            tree.insert("", "end", values=(
                l["designation"],
                f"{l['quantite']:.2f}",
                l["unite"] or "-",
                f"{l['prix_unitaire']:.2f}",
                f"{l['total']:.2f}"
            ))
        
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_retour,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="right", padx=10)
    
    def print_retour(self):
        data = [[
            self.retour["numero"],
            self.retour["date_retour"],
            self.retour["tiers_nom"],
            f"{self.retour['total']:,.2f} DA",
            self.retour["motif"] or "-"
        ]]
        headers = ["Numéro", "Date", "Tiers", "Total", "Motif"]
        print_preview(data, f"RETOUR N°{self.retour['numero']}", headers)


class RetourEditDialog(tk.Toplevel):
    """Dialogue de modification de retour - simplifié"""
    
    def __init__(self, parent, retour_type, retour_id):
        super().__init__(parent)
        self.retour_type = retour_type
        self.retour_id = retour_id
        # ✅ AJOUT — ces attributs manquaient
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        
        self.title("Modifier Retour")
        self.configure(bg=CLR_BG)
        self.geometry("600x500")
        self._load_data()
        self._build()
        center_window(self, 600, 500)
    
    def _load_data(self):
        conn = get_conn()
        self.retour = conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (self.retour_id,)).fetchone()
        self.lignes = conn.execute(f"SELECT * FROM {self.lignes_table} WHERE retour_id=?", (self.retour_id,)).fetchall()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏ MODIFIER LE MOTIF", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="x", pady=10)
        
        # Numéro (non modifiable)
        row1 = tk.Frame(form_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        lbl(row1, "Numéro:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        lbl(row1, self.retour["numero"], 9, False, CLR_TEXT).pack(side="left", padx=10)
        
        # Motif
        row2 = tk.Frame(form_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=10)
        lbl(row2, "Motif:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        self.motif_var = tk.StringVar(value=self.retour["motif"] or "")
        entry(row2, width=50, textvariable=self.motif_var).pack(side="left", padx=10, fill="x", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def save(self):
        conn = get_conn()
        try:
            conn.execute(f"UPDATE {self.table} SET motif=? WHERE id=?", 
                       (self.motif_var.get().strip(), self.retour_id))
            conn.commit()
            messagebox.showinfo("Succès", "Motif modifié")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()

class SituationPage(tk.Frame):
    """Page de situation des comptes clients/fournisseurs avec filtres"""
    
    def __init__(self, parent, sit_type="client"):
        self.sit_type = sit_type
        self.tiers_table = "clients" if sit_type == "client" else "fournisseurs"
        self.versements_table = "versements_clients" if sit_type == "client" else "versements_fournisseurs"
        self.bons_table = "bons_vente" if sit_type == "client" else "bons_achat"
        self.retours_table = "retours_vente" if sit_type == "client" else "retours_achat"
        self.tiers_label = "Client" if sit_type == "client" else "Fournisseur"
        
        super().__init__(parent, bg=CLR_BG)
        self.current_tiers_id = None
        self.tiers_combo = None
        
        # Variables pour les filtres
        self.date_debut_var = tk.StringVar(value=date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.type_filter_var = tk.StringVar(value="Tous")
        
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        title = f"📊 Situation des {self.tiers_label}s"
        lbl(hdr, title, 16, True).pack(side="left")
        
        # Sélection du tiers
        select_frame = tk.Frame(self, bg=CLR_BG)
        select_frame.pack(fill="x", padx=20, pady=5)
        
        lbl(select_frame, f"Sélectionner un {self.tiers_label}:", 10, True, CLR_MUTED).pack(side="left", padx=5)
        
        self.load_tiers_list()
        self.tiers_var = tk.StringVar()
        self.tiers_combo = combo(select_frame, self.tiers_list, width=30, textvariable=self.tiers_var)
        self.tiers_combo.pack(side="left", padx=10)
        self.tiers_combo.bind("<<ComboboxSelected>>", self.on_tiers_selected)
        
        tk.Button(select_frame, text="Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=10)
        
        # ========== SECTION FILTRES ==========
        filter_frame = tk.LabelFrame(self, text="🔍 Filtres", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        filter_frame.pack(fill="x", padx=20, pady=10)
        
        # Ligne 1: Période avec calendrier
        row1 = tk.Frame(filter_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        
        # ✅ CORRECTION : Instancier DateEntry correctement
        date_debut_entry = DateEntry(row1, self.date_debut_var, label_text="📅 Du:", width=12)
        date_debut_entry.pack(side="left", padx=5)
        
        lbl(row1, "Au:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        date_fin_entry = DateEntry(row1, self.date_fin_var, width=12)
        date_fin_entry.pack(side="left", padx=5)
        
        # Bouton appliquer les filtres
        tk.Button(row1, text="📊 Appliquer", command=self.apply_filters,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=20)
        
        # Bouton réinitialiser
        tk.Button(row1, text="🔄 Réinitialiser", command=self.reset_filters,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        # Ligne 2: Type de transaction
        row2 = tk.Frame(filter_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        
        lbl(row2, "📌 Type:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        if self.sit_type == "client":
            types = ["Tous", "VENTE", "RETOUR", "VERSEMENT"]
        else:
            types = ["Tous", "ACHAT", "RETOUR", "VERSEMENT"]
        
        type_combo = combo(row2, types, width=15, textvariable=self.type_filter_var)
        type_combo.pack(side="left", padx=5)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Ligne 3: Boutons d'export
        row3 = tk.Frame(filter_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        
        tk.Button(row3, text="📥 Exporter CSV", command=self.export_filtered_csv,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(row3, text="📄 Exporter HTML", command=self.export_filtered_html,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(row3, text="🖨 Imprimer", command=self.print_filtered,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        # Notebook pour les onglets
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Onglet Synthèse
        self.synthese_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.synthese_frame, text="📈 Synthèse")
        
        # Onglet Historique
        self.histo_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.histo_frame, text="📜 Historique transactions")
        
        # Onglet Versements
        self.versements_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.versements_frame, text="💳 Versements")
        
        self._build_synthese()
        self._build_historique()
        self._build_versements()
    
    def load_tiers_list(self):
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.tiers_table} ORDER BY nom").fetchall()
        conn.close()
        self.tiers_list = [f"{t['nom']} (Solde: {t['solde']:,.2f} DA)" for t in tiers]
        self.tiers_data = {f"{t['nom']} (Solde: {t['solde']:,.2f} DA)": {"id": t["id"], "nom": t["nom"], "solde": t["solde"]} 
                          for t in tiers}
    
    def on_tiers_selected(self, event=None):
        key = self.tiers_var.get()
        if key and key in self.tiers_data:
            self.current_tiers_id = self.tiers_data[key]["id"]
            self.current_tiers_nom = self.tiers_data[key]["nom"]
            self.refresh_situation()
    def modifier_observation_avoir(self):
        """Modifier l'observation d'un avoir (AVOIR-C ou AVOIR-F)"""
        # Récupérer la sélection dans l'historique
        sel = self.histo_tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne dans l'historique")
            return
        
        # Récupérer les valeurs de la ligne sélectionnée
        values = self.histo_tree.item(sel[0])["values"]
        if len(values) < 3:
            messagebox.showwarning("Avertissement", "Ligne invalide")
            return
        
        type_transaction = values[1]  # Type (AVOIR, SOLDE INITIAL, etc.)
        document = values[2]          # Document (numéro ou observation)
        
        # Vérifier que c'est bien un AVOIR ou SOLDE INITIAL
        if type_transaction not in ["AVOIR", "SOLDE INITIAL"]:
            messagebox.showwarning("Avertissement", 
                "Cette fonction n'est disponible que pour les AVOIR et SOLDE INITIAL")
            return
        
        # Récupérer le numéro du document (si c'est une observation, il faut retrouver le bon)
        conn = get_conn()
        
        # Chercher le bon correspondant
        if self.sit_type == "client":
            # Chercher dans les bons de vente
            bon = conn.execute("""
                SELECT id, numero, observations 
                FROM bons_vente 
                WHERE client_id=? AND (numero LIKE 'AVOIR-C-%' OR numero LIKE 'SI-C-%')
                AND (numero = ? OR observations = ?)
                ORDER BY date_bon DESC
            """, (self.current_tiers_id, document, document)).fetchone()
        else:
            # Chercher dans les bons d'achat
            bon = conn.execute("""
                SELECT id, numero, observations 
                FROM bons_achat 
                WHERE fournisseur_id=? AND (numero LIKE 'AVOIR-F-%' OR numero LIKE 'SI-F-%')
                AND (numero = ? OR observations = ?)
                ORDER BY date_bon DESC
            """, (self.current_tiers_id, document, document)).fetchone()
        
        conn.close()
        
        if not bon:
            messagebox.showwarning("Avertissement", "Document non trouvé")
            return
        
        # Demander la nouvelle observation
        nouvelle_obs = simpledialog.askstring(
            "Modifier l'observation",
            f"Document: {bon['numero']}\n"
            f"Observation actuelle: {bon['observations'] or '(vide)'}\n\n"
            f"Nouvelle observation:",
            initialvalue=bon['observations'] or "",
            parent=self
        )
        
        if nouvelle_obs is None:
            return  # L'utilisateur a annulé
        
        # Mettre à jour dans la base de données
        conn = get_conn()
        try:
            if self.sit_type == "client":
                conn.execute(
                    "UPDATE bons_vente SET observations = ? WHERE id = ?",
                    (nouvelle_obs.strip(), bon["id"])
                )
            else:
                conn.execute(
                    "UPDATE bons_achat SET observations = ? WHERE id = ?",
                    (nouvelle_obs.strip(), bon["id"])
                )
            conn.commit()
            messagebox.showinfo("Succès", "✅ Observation mise à jour avec succès")
            self.refresh_situation()  # Rafraîchir l'affichage
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour: {str(e)}")
        finally:
            conn.close()
    def refresh(self):
        self.load_tiers_list()
        if self.tiers_combo:
            self.tiers_combo['values'] = self.tiers_list

        if self.current_tiers_id is not None:
            nouvelle_cle = next(
                (k for k, v in self.tiers_data.items() if v["id"] == self.current_tiers_id),
                None
            )
            if nouvelle_cle:
                self.tiers_var.set(nouvelle_cle)
                self.refresh_situation()
            elif self.tiers_list:
                self.tiers_var.set(self.tiers_list[0])
                self.on_tiers_selected()
        elif self.tiers_list:
            self.tiers_var.set(self.tiers_list[0])
            self.on_tiers_selected()
    
    def apply_filters(self):
        """Appliquer les filtres et rafraîchir l'affichage"""
        if self.current_tiers_id:
            self.refresh_situation()
    
    def reset_filters(self):
        """Réinitialiser les filtres"""
        self.date_debut_var.set(date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.date_fin_var.set(date.today().strftime("%Y-%m-%d"))
        self.type_filter_var.set("Tous")
        self.apply_filters()
    
    def _build_synthese(self):
        """Construit l'interface de synthèse avec des widgets modernes"""
        main_frame = tk.Frame(self.synthese_frame, bg=CLR_BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Carte d'identité du client
        card_info = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
        card_info.pack(fill="x", pady=(0, 15))
        
        header_frame = tk.Frame(card_info, bg=CLR_CARD)
        header_frame.pack(fill="x", pady=(0, 10))
        lbl(header_frame, "INFORMATIONS", 11, True, CLR_ACCENT).pack(side="left")
        
        separator = tk.Frame(header_frame, bg=CLR_BORDER, height=2)
        separator.pack(fill="x", pady=5)
        
        self.info_frame = tk.Frame(card_info, bg=CLR_CARD)
        self.info_frame.pack(fill="x")
        
        # Indicateurs de performance
        kpi_frame = tk.Frame(main_frame, bg=CLR_BG)
        kpi_frame.pack(fill="x", pady=(0, 15))
        
        self.kpi_cards = {}
        if self.sit_type == "client":
            kpi_titles = ["Total Ventes HT", "Total Retours", "Total Versements", "Solde"]
        else:
            kpi_titles = ["Total Achats TTC", "Total Retours", "Total Versements", "Solde"]
        colors = [CLR_ACCENT, CLR_ORANGE, CLR_RED, CLR_GREEN]
        
        for i, (title, color) in enumerate(zip(kpi_titles, colors)):
            card = tk.Frame(kpi_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
            card.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            kpi_frame.grid_columnconfigure(i, weight=1)
            
            lbl(card, title, 9, color=CLR_MUTED).pack(anchor="w")
            
            var_name = f"kpi_var_{i}"
            setattr(self, var_name, tk.StringVar(value="0 DA"))
            label = tk.Label(card, textvariable=getattr(self, var_name), 
                            bg=CLR_CARD, fg=color, font=("Segoe UI", 16, "bold"))
            label.pack(anchor="w", pady=(5, 0))
            self.kpi_cards[f"title_{i}"] = label
        
        # Cadre des soldes
        solde_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
        solde_frame.pack(fill="x", pady=(0, 15))
        
        lbl(solde_frame, "SITUATION FINANCIÈRE", 11, True, CLR_ACCENT).pack(anchor="w")
        tk.Frame(solde_frame, bg=CLR_BORDER, height=2).pack(fill="x", pady=5)
        
        soldes_grid = tk.Frame(solde_frame, bg=CLR_CARD)
        soldes_grid.pack(fill="x", pady=10)
        
        lbl(soldes_grid, "Solde calculé:", 10, True, CLR_MUTED).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.solde_calcule_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.solde_calcule_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        lbl(soldes_grid, "Solde enregistré:", 10, True, CLR_MUTED).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.solde_enregistre_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.solde_enregistre_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        lbl(soldes_grid, "Écart:", 10, True, CLR_MUTED).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.ecart_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.ecart_var, bg=CLR_CARD, 
                fg=CLR_RED, font=("Segoe UI", 11, "bold")).grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        # Indicateur de statut
        self.status_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=10, relief="flat")
        self.status_frame.pack(fill="x")
        self.status_label = lbl(self.status_frame, "", 10, True)
        self.status_label.pack()
    
    def _build_historique(self):
        histo_frame = tk.Frame(self.histo_frame, bg=CLR_BG)
        histo_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = ["Date", "Type", "Document", "Montant", "Solde après"]
        widths = [100, 100, 120, 120, 120]
        tf, self.histo_tree = make_tree(histo_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        self.histo_tree.bind("<Double-1>", lambda e: self.modifier_observation_avoir())

    
    def _build_versements(self):
        vers_frame = tk.Frame(self.versements_frame, bg=CLR_BG)
        vers_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = ["Date", "Numéro", "Montant", "Mode", "Référence"]
        widths = [100, 120, 120, 100, 150]
        tf, self.vers_tree = make_tree(vers_frame, cols, widths)
        tf.pack(fill="both", expand=True)
    
    def get_filtered_transactions(self):
        """Récupère les transactions filtrées par date et type"""
        if not self.current_tiers_id:
            return [], 0, 0, 0
        
        conn = get_conn()
        
        # Récupérer les dates
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        type_filter = self.type_filter_var.get()
        
        transactions = []
        
        # Construire la clause WHERE pour les dates
        date_condition = ""
        if date_debut and date_fin:
            date_condition = f"AND date BETWEEN '{date_debut}' AND '{date_fin}'"
        
        # 1. Bons (Ventes ou Achats)
        if self.sit_type == "client":
            # ✅ Clients
            bons = conn.execute(f"""
                SELECT date_bon as date, 
                    CASE 
                        WHEN numero LIKE 'SI-C-%' THEN 'SOLDE INITIAL'
                        WHEN numero LIKE 'AVOIR-%' THEN 'AVOIR'
                        ELSE 'VENTE' 
                    END as type,
                    CASE 
                        WHEN numero LIKE 'SI-C-%' OR numero LIKE 'AVOIR-%' 
                        THEN COALESCE(observations, numero)
                        ELSE numero 
                    END as document,
                    total as montant,
                    observations as motif,
                    '' as mode, '' as reference
                FROM {self.bons_table}
                WHERE client_id=? AND statut='Validé'
                {date_condition}
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        else:
            # ✅ Fournisseurs
            bons = conn.execute(f"""
                SELECT date_bon as date, 
                    CASE 
                        WHEN numero LIKE 'SI-F-%' THEN 'SOLDE INITIAL'
                        WHEN numero LIKE 'AVOIR-%' THEN 'AVOIR'
                        ELSE 'ACHAT' 
                    END as type,
                    CASE 
                        WHEN numero LIKE 'SI-F-%' OR numero LIKE 'AVOIR-%' 
                        THEN COALESCE(observations, numero)  -- ✅ Afficher observations ou le numéro par défaut
                        ELSE numero 
                    END as document,
                    total as montant,
                    observations as motif,
                    '' as mode, '' as reference
                FROM {self.bons_table}
                WHERE fournisseur_id=? AND statut='Validé'
                {date_condition}
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        
        # ✅ Convertir les bons en dictionnaires
        for b in bons:
            transactions.append(dict(b))
        
        # 2. Retours
        if self.sit_type == "client":
            retours = conn.execute(f"""
                SELECT date_retour as date, 'RETOUR' as type, numero as document, -total as montant,
                    motif, '' as mode, '' as reference
                FROM {self.retours_table}
                WHERE client_id=?
                {date_condition}
                ORDER BY date_retour
            """, (self.current_tiers_id,)).fetchall()
        else:
            retours = conn.execute(f"""
                SELECT date_retour as date, 'RETOUR' as type, numero as document, -total as montant,
                    motif, '' as mode, '' as reference
                FROM {self.retours_table}
                WHERE fournisseur_id=?
                {date_condition}
                ORDER BY date_retour
            """, (self.current_tiers_id,)).fetchall()
        
        for r in retours:
            transactions.append(dict(r))
        
        # 3. Versements
        if self.sit_type == "client":
            versements = conn.execute(f"""
                SELECT date_vers as date, 'VERSEMENT' as type, numero as document, -montant as montant,
                    '' as motif, mode, reference
                FROM {self.versements_table}
                WHERE client_id=?
                {date_condition}
                ORDER BY date_vers
            """, (self.current_tiers_id,)).fetchall()
        else:
            versements = conn.execute(f"""
                SELECT date_vers as date, 'VERSEMENT' as type, numero as document, -montant as montant,
                    '' as motif, mode, reference
                FROM {self.versements_table}
                WHERE fournisseur_id=?
                {date_condition}
                ORDER BY date_vers
            """, (self.current_tiers_id,)).fetchall()
        
        for v in versements:
            transactions.append(dict(v))
        
        conn.close()
        
        # Filtrer par type
        if type_filter != "Tous":
            transactions = [t for t in transactions if t["type"] == type_filter]
        
        # Trier par date
        transactions.sort(key=lambda x: x["date"])
        
        # Calculer les totaux
        total_operations = 0
        total_retours = 0
        total_versements = 0
        
        for t in transactions:
            if t["type"] in ("VENTE", "ACHAT", "AVOIR", "REMBOURSEMENT"):
                total_operations += t["montant"]
            elif t["type"] == "RETOUR":
                total_retours += abs(t["montant"])
            elif t["type"] == "VERSEMENT":
                total_versements += abs(t["montant"])
        
        return transactions, total_operations, total_retours, total_versements

    def refresh_situation(self):
        if not self.current_tiers_id:
            return

        conn = get_conn()
        tiers = conn.execute(
            f"SELECT * FROM {self.tiers_table} WHERE id=?",
            (self.current_tiers_id,)
        ).fetchone()

        # ✅ RÉCUPÉRER LES SOLDES INITIAUX POUR LES KPI (TOTAL GLOBAL UNIQUEMENT)
        if self.sit_type == "client":
            total_si_global = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
            """, (self.current_tiers_id,)).fetchone()[0]
            
            total_ventes_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM bons_vente "
                "WHERE client_id=? AND statut='Validé' AND numero NOT LIKE 'SI-C-%'",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_retours_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM retours_vente "
                "WHERE client_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_versements_global = conn.execute(
                "SELECT COALESCE(SUM(montant),0) FROM versements_clients "
                "WHERE client_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
        else:
            total_si_global = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
            """, (self.current_tiers_id,)).fetchone()[0]
            
            total_ventes_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM bons_achat "
                "WHERE fournisseur_id=? AND statut='Validé' AND numero NOT LIKE 'SI-F-%'",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_retours_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM retours_achat "
                "WHERE fournisseur_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_versements_global = conn.execute(
                "SELECT COALESCE(SUM(montant),0) FROM versements_fournisseurs "
                "WHERE fournisseur_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]

        # ✅ Solde calculé GLOBAL (tout l'historique)
        solde_calcule_global = (
            total_ventes_global 
            + total_si_global
            - total_retours_global 
            - total_versements_global
        )

        # ✅ Mettre à jour les labels de solde
        self.solde_calcule_var.set(f"{solde_calcule_global:,.2f} DA")
        self.solde_enregistre_var.set(f"{tiers['solde']:,.2f} DA")

        ecart = abs(solde_calcule_global - tiers["solde"])
        if ecart > 0.01:
            self.ecart_var.set(f"⚠️ {ecart:,.2f} DA")
            self.status_label.config(
                text="⚠️ ATTENTION : Écart détecté entre le solde calculé et enregistré !",
                fg=CLR_RED
            )
            self.status_frame.config(bg=CLR_RED)
        else:
            self.ecart_var.set(f"✅ {ecart:,.2f} DA")
            self.status_label.config(
                text="✅ Compte équilibré - Tout est en ordre",
                fg=CLR_GREEN
            )
            self.status_frame.config(bg=CLR_GREEN)

        # ✅ RÉCUPÉRER LES TRANSACTIONS FILTRÉES (ELLES INCLUENT DÉJÀ LES SOLDES INITIAUX)
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ RÉCUPÉRER LE TOTAL DES SOLDES INITIAUX DANS LA PÉRIODE (pour les KPI uniquement)
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        conn2 = get_conn()
        if self.sit_type == "client":
            total_si_periode = conn2.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        else:
            total_si_periode = conn2.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        conn2.close()

        # ✅ Mettre à jour les KPI
        if hasattr(self, 'kpi_var_0'):
            self.kpi_var_0.set(f"{total_ops:,.2f} DA")
            self.kpi_var_1.set(f"{total_ret:,.2f} DA")
        if hasattr(self, 'kpi_var_2'):
            self.kpi_var_2.set(f"{total_vers:,.2f} DA")
        if hasattr(self, 'kpi_var_3'):
            solde_periode = total_si_periode + total_ops - total_ret - total_vers
            self.kpi_var_3.set(f"{solde_periode:,.2f} DA")

        # ========== HISTORIQUE (UNIQUEMENT AVEC transactions) ==========
        self.histo_tree.delete(*self.histo_tree.get_children())

        # ✅ Utiliser directement les transactions (elles contiennent déjà TOUS les soldes initiaux)
        all_transactions = transactions.copy()

        # Trier par date
        all_transactions.sort(key=lambda x: x["date"])

        # ✅ Calculer le solde cumulé
        solde_cumule = 0

        # ✅ Ajouter l'en-tête de période
        period_text = f"Période: {date_debut} → {date_fin}"
        if self.type_filter_var.get() != "Tous":
            period_text += f" | Type: {self.type_filter_var.get()}"

        self.histo_tree.insert("", "end", values=(
            f"📅 {period_text}", "", "", "", ""
        ), tags=("header",))

        # ✅ Afficher les transactions (sans duplication)
        for t in all_transactions:
            solde_cumule += t["montant"]
            
            # ✅ Déterminer le type d'affichage
            if t["type"] == "SOLDE INITIAL":
                type_affichage = "SOLDE INITIAL"
                tag = "solde_initial"
            elif t["type"] == "AVOIR":
                type_affichage = "AVOIR"
                tag = "avoir"
            elif t["type"] == "REMBOURSEMENT":
                type_affichage = "REMBOURSEMENT"
                tag = "remboursement"
            else:
                type_affichage = t["type"]
                if t["type"] in ("VENTE", "ACHAT"):
                    tag = "operation"
                elif t["type"] == "RETOUR":
                    tag = "retour"
                else:  # VERSEMENT
                    tag = "versement"
            
            self.histo_tree.insert("", "end", values=(
                t["date"],
                type_affichage,
                t["document"],
                f"{t['montant']:+,.2f} DA",
                f"{solde_cumule:,.2f} DA"
            ), tags=(tag,))

        # ✅ CONFIGURER LES COULEURS
        self.histo_tree.tag_configure(
            "header", foreground=CLR_ACCENT, font=("Segoe UI", 10, "bold"))
        self.histo_tree.tag_configure(
            "operation", foreground=CLR_ACCENT)
        self.histo_tree.tag_configure(
            "retour", foreground=CLR_ORANGE)
        self.histo_tree.tag_configure(
            "versement", foreground=CLR_GREEN)
        self.histo_tree.tag_configure(
            "solde_initial", foreground=CLR_PURPLE, font=("Segoe UI", 9, "bold"))
        self.histo_tree.tag_configure(
            "avoir", foreground=CLR_ORANGE, font=("Segoe UI", 9, "bold"))
        self.histo_tree.tag_configure(
            "remboursement", foreground=CLR_GREEN, font=("Segoe UI", 9, "bold"))

        # ========== VERSEMENTS (filtrés par date) ==========
        self.vers_tree.delete(*self.vers_tree.get_children())
        conn3 = get_conn()

        if self.sit_type == "client":
            if date_debut and date_fin:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_clients "
                    "WHERE client_id=? AND date_vers BETWEEN ? AND ? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id, date_debut, date_fin)
                ).fetchall()
            else:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_clients WHERE client_id=? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id,)
                ).fetchall()
        else:
            if date_debut and date_fin:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_fournisseurs "
                    "WHERE fournisseur_id=? AND date_vers BETWEEN ? AND ? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id, date_debut, date_fin)
                ).fetchall()
            else:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_fournisseurs WHERE fournisseur_id=? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id,)
                ).fetchall()

        conn3.close()

        for v in vers:
            self.vers_tree.insert("", "end", values=(
                v["date_vers"], v["numero"],
                f"{v['montant']:,.2f} DA",
                v["mode"], v["reference"] or "-"
            ))
            
    def export_filtered_csv(self):
        """Exporter les données filtrées en CSV"""
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ Récupérer les soldes initiaux
        conn = get_conn()
        if self.sit_type == "client":
            soldes_initiaux = conn.execute("""
                SELECT date_bon as date, 'SOLDE INITIAL' as type, 
                    numero as document, total as montant
                FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        else:
            soldes_initiaux = conn.execute("""
                SELECT date_bon as date, 'SOLDE INITIAL' as type, 
                    numero as document, total as montant
                FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        conn.close()
        
        if not transactions and not soldes_initiaux:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"situation_{self.tiers_label}_{self.current_tiers_nom}.csv"
        )
        
        if filename:
            headers = ["Date", "Type", "Document", "Montant", "Solde Cumulé"]
            data = []
            solde_cumule = 0
            total_si = 0
            
            # ✅ Ajouter les soldes initiaux en premier
            for si in soldes_initiaux:
                solde_cumule += si["montant"]
                total_si += si["montant"]
                data.append([
                    si["date"], 
                    si["type"], 
                    si["document"],
                    f"{si['montant']:+,.2f}",
                    f"{solde_cumule:,.2f}"
                ])
            
            # Ajouter les transactions normales
            for t in transactions:
                solde_cumule += t["montant"]
                data.append([
                    t["date"], 
                    t["type"], 
                    t["document"],
                    f"{t['montant']:+,.2f}",
                    f"{solde_cumule:,.2f}"
                ])
            
            # Ajouter les totaux
            data.append(["", "", "", "", ""])
            if soldes_initiaux:
                data.append(["SOLDE INITIAL", "", "", f"{total_si:+,.2f}", ""])
            data.append(["TOTAL OPERATIONS", "", "", f"{total_ops:+,.2f}", ""])
            data.append(["TOTAL RETOURS", "", "", f"{total_ret:+,.2f}", ""])
            data.append(["TOTAL VERSEMENTS", "", "", f"{total_vers:+,.2f}", ""])
            data.append(["", "", "", "", ""])
            data.append(["SOLDE FINAL", "", "", f"{solde_cumule:,.2f}", ""])
            
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    
    def print_filtered(self):
        from gestion_stock import get_profil_by_type
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ Récupérer UNIQUEMENT le TOTAL des soldes initiaux pour les KPI
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        conn = get_conn()
        if self.sit_type == "client":
            total_si = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        else:
            total_si = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        conn.close()
        
        # ✅ Convertir transactions en dictionnaires (ils contiennent déjà les soldes initiaux)
        transactions_dicts = []
        for t in transactions:
            if hasattr(t, 'keys'):
                transactions_dicts.append(dict(t))
            else:
                transactions_dicts.append(t)
        
        # Trier par date
        transactions_dicts.sort(key=lambda x: x["date"])
        
        if not transactions_dicts:
            from tkinter import messagebox
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        profil = get_profil_by_type("situation")
        
        html = hr.build_situation_html(
            profil      = profil,
            tiers_nom   = self.current_tiers_nom,
            tiers_label = self.tiers_label,
            transactions= transactions_dicts,
            total_ops   = total_ops,
            total_ret   = total_ret,
            total_vers  = total_vers,
            date_debut  = date_debut,
            date_fin    = date_fin,
            total_si    = total_si,
        )
        
        # ✅ AJOUT DES STYLES D'IMPRESSION
        print_styles = """
        <style>
            @media print {
                * {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    box-shadow: none !important;
                    text-shadow: none !important;
                    background-image: none !important;
                    filter: none !important;
                    -webkit-filter: none !important;
                    opacity: 1 !important;
                }
                
                body {
                    background-color: #ffffff !important;
                    margin: 15px !important;
                    font-size: 11pt !important;
                    color: #000000 !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                }
                
                th {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    font-weight: 700 !important;
                    font-size: 11pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    border: 2px solid #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                    text-align: center !important;
                    padding: 8px 12px !important;
                    vertical-align: middle !important;
                    page-break-inside: avoid !important;
                }
                
                td {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border: 1px solid #888888 !important;
                    padding: 6px 10px !important;
                    font-size: 10pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    text-align: center !important;
                }
                
                tr:nth-child(even) td {
                    background-color: #f5f5f5 !important;
                }
                
                .header-section, .header, .bg-primary, .bg-dark {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                }
                
                .header-section h1, .header-section h2, .header-section h3 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                h1, h2, h3, h4, h5 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                table {
                    border-collapse: collapse !important;
                    width: 100% !important;
                    page-break-inside: auto !important;
                }
                
                thead {
                    display: table-header-group !important;
                }
                
                tr {
                    page-break-inside: avoid !important;
                    page-break-after: auto !important;
                }
                
                .total-row td, .grand-total td {
                    font-weight: 700 !important;
                    border-top: 3px solid #000000 !important;
                }
                
                .footer, .footer p, .footer div {
                    color: #000000 !important;
                    border-top: 2px solid #000000 !important;
                    padding-top: 10px !important;
                    margin-top: 15px !important;
                }
            }
        </style>
        """
        
        if '</head>' in html:
            html = html.replace('</head>', print_styles + '</head>')
        else:
            html = html.replace('<body>', print_styles + '<body>')
        
        viewer = hr.DocumentViewer(self)
        viewer.show(html, f"Situation {self.current_tiers_nom}")
 
    def export_filtered_html(self):
        from gestion_stock import get_profil_by_type
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        if not transactions:
            from tkinter import messagebox
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        profil = get_profil_by_type("situation")
        html = hr.build_situation_html(
            profil      = profil,
            tiers_nom   = self.current_tiers_nom,
            tiers_label = self.tiers_label,
            transactions= [dict(t) for t in transactions],
            total_ops   = total_ops,
            total_ret   = total_ret,
            total_vers  = total_vers,
            date_debut  = self.date_debut_var.get(),
            date_fin    = self.date_fin_var.get(),
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_html(html, f"situation_{self.current_tiers_nom}.html")
class GestionProfilsPage(tk.Frame):
    """Page de gestion des profils entreprise"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "🏢 Gestion des Profils Entreprise", 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Profil", command=self.nouveau_profil,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Configuration des types de documents
        config_frame = tk.LabelFrame(self, text="📄 Association Profil → Document", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        
        self.doc_types = [
            ("Facture", "facture"),
            ("Bon de livraison", "bon_livraison"),
            ("Devis", "devis"),
            ("Situation", "situation"),
        ]
        
        self.doc_vars = {}
        self.doc_combos = {}  # Garder une référence aux combobox
        for i, (label, key) in enumerate(self.doc_types):
            row = tk.Frame(config_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=5)
            lbl(row, f"{label}:", 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            
            self.doc_vars[key] = tk.StringVar()
            cb = combo(row, [], width=30, textvariable=self.doc_vars[key])
            cb.pack(side="left", padx=10)
            self.doc_combos[key] = cb  # Stocker la référence
        
        tk.Button(config_frame, text="💾 Enregistrer la configuration", command=self.save_config,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(pady=10)
        
        # Tableau des profils
        cols = ["Code", "Nom", "Type", "Téléphone", "Email", "Défaut"]
        widths = [100, 200, 100, 120, 180, 80]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_profil,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="⭐ Définir par défaut", command=self.set_default,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_profil,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        profils = conn.execute("SELECT * FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        for p in profils:
            default_mark = "✅" if p["est_defaut"] else ""
            self.tree.insert("", "end", iid=p["id"], values=(
                p["code"], p["nom"], p["type_profil"],
                p["telephone"] or "-", p["email"] or "-", default_mark
            ))
        
        # Charger la configuration
        self.load_config()
    
    def load_config(self):
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        conn = get_conn()
        profils = conn.execute("SELECT id, code, nom FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        profil_liste = ["-- Aucun --"] + [f"{p['code']} - {p['nom']}" for p in profils]
        
        # Mettre à jour les valeurs des combobox
        for doc_key, var in self.doc_vars.items():
            var.set(config.get(doc_key, "-- Aucun --"))
            # Mettre à jour les valeurs du combobox via la référence stockée
            if doc_key in self.doc_combos:
                self.doc_combos[doc_key]['values'] = profil_liste
    
    def save_config(self):
        config = {}
        for doc_key, var in self.doc_vars.items():
            val = var.get()
            if val and val != "-- Aucun --":
                config[doc_key] = val
        
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Succès", "Configuration enregistrée")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def nouveau_profil(self):
        d = ProfilDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def edit_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT * FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        d = ProfilDialog(self, dict(profil) if profil else None)
        self.wait_window(d)
        self.refresh()
    
    def set_default(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        try:
            conn.execute("UPDATE profils_entreprise SET est_defaut = 0")
            conn.execute("UPDATE profils_entreprise SET est_defaut = 1 WHERE id=?", (sel[0],))
            conn.commit()
            messagebox.showinfo("Succès", "Profil défini par défaut")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
    
    def delete_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT nom, est_defaut FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        
        if profil["est_defaut"]:
            messagebox.showwarning("", "Impossible de supprimer le profil par défaut")
            conn.close()
            return
        
        if messagebox.askyesno("Confirmation", f"Supprimer le profil '{profil['nom']}' ?"):
            try:
                conn.execute("DELETE FROM profils_entreprise WHERE id=?", (sel[0],))
                conn.commit()
                messagebox.showinfo("Succès", "Profil supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        conn.close()

class ProfilDialog(tk.Toplevel):
    """Dialogue de création/édition de profil entreprise"""
    
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.data = data
        self.title("Profil Entreprise")
        self.configure(bg=CLR_BG)
        self.geometry("700x650")
        self._build()
        center_window(self, 700, 650)
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, "🏢 INFORMATIONS DE L'ENTREPRISE", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Formulaire avec scroll
        canvas = tk.Canvas(main_frame, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Champs du formulaire
        form_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="both", expand=True, pady=5)
        
        fields = [
            ("Code *", "code", True),
            ("Nom de l'entreprise *", "nom", False),
            ("Type de profil", "type_profil", False, ["simple", "complet"]),
            ("Adresse", "adresse", False),
            ("Ville", "ville", False),
            ("Téléphone", "telephone", False),
            ("Email", "email", False),
            ("Site web", "site_web", False),
            ("NIF (Numéro d'Identification Fiscale)", "nif", False),
            ("NIS (Numéro d'Identification Statistique)", "nis", False),
            ("NRC (Numéro Registre de Commerce)", "nrc", False),
            ("Article d'imposition", "art_imp", False),
            ("Registre de commerce", "registre_commerce", False),
            ("Capital social", "capitale_social", False),
        ]
        
        self.vars = {}
        
        for i, field in enumerate(fields):
            if len(field) == 4:
                lbl_text, key, readonly, choices = field
            else:
                lbl_text, key, readonly = field
                choices = None
            
            row = tk.Frame(form_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=4)
            
            lbl(row, lbl_text, 9, False, CLR_MUTED).pack(side="left", padx=5, ipadx=10, anchor="w")
            
            v = tk.StringVar()
            if self.data and key in self.data and self.data[key]:
                v.set(str(self.data[key]))
            elif key == "type_profil":
                v.set("simple")
            elif key == "code" and not self.data:
                v.set(generer_code_unique("PROF", "profils_entreprise", mode="sequentiel"))
            
            if choices:
                widget = combo(row, choices, width=30, textvariable=v)
            else:
                widget = entry(row, width=40, textvariable=v)
                if key == "code" and not self.data:
                    widget.config(state="readonly", readonlybackground=CLR_INPUT)
            
            widget.pack(side="left", padx=10, fill="x", expand=True)
            self.vars[key] = v
            
            if not self.data and key == "code":
                tk.Button(row, text="🔄", command=self.regenerate_code,
                         bg=CLR_ACCENT, fg="white", relief="flat",
                         font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                         cursor="hand2").pack(side="left", padx=5)
        
        # Logo
        row_logo = tk.Frame(form_frame, bg=CLR_CARD)
        row_logo.pack(fill="x", pady=10)
        lbl(row_logo, "Logo:", 9, False, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
        self.logo_path_var = tk.StringVar(value=self.data["logo_path"] if self.data and self.data.get("logo_path") else "")
        entry(row_logo, width=30, textvariable=self.logo_path_var).pack(side="left", padx=10)
        tk.Button(row_logo, text="Parcourir", command=self.browse_logo,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                 padx=8, pady=3, cursor="hand2").pack(side="left", padx=5)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def regenerate_code(self):
        nouveau_code = generer_code_unique("PROF", "profils_entreprise", mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")
    
    def browse_logo(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner un logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Tous", "*.*")]
        )
        if filename:
            self.logo_path_var.set(filename)
    
    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        
        if not v["code"] or not v["nom"]:
            messagebox.showerror("Erreur", "Code et nom sont obligatoires")
            return
        
        conn = get_conn()
        try:
            if self.data:
                conn.execute("""
                    UPDATE profils_entreprise 
                    SET code=?, nom=?, type_profil=?, adresse=?, ville=?, 
                        telephone=?, email=?, site_web=?, nif=?, nis=?, nrc=?,
                        art_imp=?, registre_commerce=?, capitale_social=?, logo_path=?
                    WHERE id=?
                """, (v["code"], v["nom"], v["type_profil"], v["adresse"], v["ville"],
                      v["telephone"], v["email"], v["site_web"], v["nif"], v["nis"], v["nrc"],
                      v["art_imp"], v["registre_commerce"], v["capitale_social"],
                      self.logo_path_var.get(), self.data["id"]))
            else:
                conn.execute("""
                    INSERT INTO profils_entreprise(code, nom, type_profil, adresse, ville,
                        telephone, email, site_web, nif, nis, nrc, art_imp,
                        registre_commerce, capitale_social, logo_path)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (v["code"], v["nom"], v["type_profil"], v["adresse"], v["ville"],
                      v["telephone"], v["email"], v["site_web"], v["nif"], v["nis"], v["nrc"],
                      v["art_imp"], v["registre_commerce"], v["capitale_social"],
                      self.logo_path_var.get()))
            conn.commit()
            messagebox.showinfo("Succès", "Profil enregistré")
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Code déjà existant")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
class AnalyseProduitsPage(tk.Frame):
    """
    Page d'analyse personnalisée des produits
    Sélectionnez des produits → Analyse complète des ventes
    """
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.produits_selectionnes = []  # Liste des IDs de produits sélectionnés
        self._build()
        self.charger_produits()
    
    def _build(self):
        # ✅ CONTENEUR SCROLLABLE
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(main_container, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        
        def _configure_canvas(event):
            canvas.itemconfig(1, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        content = scrollable_frame
        
        # ========== EN-TÊTE ==========
        hdr = tk.Frame(content, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "📊 Analyse Personnalisée des Produits", 16, True).pack(side="left")
        
        # ========== SECTION SÉLECTION DES PRODUITS ==========
        select_frame = tk.LabelFrame(content, text="1. Sélectionner les produits à analyser", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, 
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        select_frame.pack(fill="x", padx=20, pady=10)
        
        # Barre de recherche
        search_frame = tk.Frame(select_frame, bg=CLR_CARD)
        search_frame.pack(fill="x", pady=5)
        
        lbl(search_frame, "🔍 Rechercher:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.charger_produits())
        entry(search_frame, width=30, textvariable=self.search_var).pack(side="left", padx=10)
        
        # Période
        lbl(search_frame, "📅 Du:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
        self.date_debut_var = tk.StringVar(value=date.today().replace(day=1).strftime("%Y-%m-%d"))
        entry(search_frame, width=12, textvariable=self.date_debut_var).pack(side="left", padx=5)
        
        lbl(search_frame, "Au:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        entry(search_frame, width=12, textvariable=self.date_fin_var).pack(side="left", padx=5)
        
        # Liste des produits avec checkbox
        produits_frame = tk.Frame(select_frame, bg=CLR_CARD)
        produits_frame.pack(fill="both", expand=True, pady=10)
        
        # Canvas pour la liste des produits (scrollable)
        prod_canvas = tk.Canvas(produits_frame, bg=CLR_CARD, highlightthickness=1, 
                                highlightbackground=CLR_BORDER, height=200)
        prod_scrollbar = tk.Scrollbar(produits_frame, orient="vertical", command=prod_canvas.yview)
        prod_inner = tk.Frame(prod_canvas, bg=CLR_CARD)
        
        prod_inner.bind(
            "<Configure>",
            lambda e: prod_canvas.configure(scrollregion=prod_canvas.bbox("all"))
        )
        prod_window_id = prod_canvas.create_window((0, 0), window=prod_inner, anchor="nw")
        prod_canvas.configure(yscrollcommand=prod_scrollbar.set)

        prod_canvas.pack(side="left", fill="both", expand=True)
        prod_scrollbar.pack(side="right", fill="y")

        def _configure_prod_canvas(event):
            prod_canvas.itemconfig(prod_window_id, width=event.width)
        prod_canvas.bind("<Configure>", _configure_prod_canvas)
        
        self.prod_inner = prod_inner
        self.prod_checkboxes = {}  # {produit_id: tk.IntVar}
        self.prod_labels = {}      # {produit_id: tk.Checkbutton}
        
        # Boutons d'action
        action_frame = tk.Frame(select_frame, bg=CLR_CARD)
        action_frame.pack(fill="x", pady=5)
        
        tk.Button(action_frame, text="✅ ANALYSER", command=self.analyser,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 10, "bold"), padx=20, pady=8,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(action_frame, text="🔄 Tout sélectionner", command=self.tout_selectionner,
                 bg=CLR_ACCENT, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(action_frame, text="🔄 Tout désélectionner", command=self.tout_deselectionner,
                 bg=CLR_ORANGE, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                 cursor="hand2").pack(side="left", padx=5)
        
        lbl(action_frame, f"Produits sélectionnés: 0", 9, False, CLR_MUTED).pack(side="right", padx=10)
        
        # ========== SECTION RÉSULTATS ==========
        result_frame = tk.LabelFrame(content, text="2. Résultats de l'analyse", 
                                     bg=CLR_CARD, fg=CLR_GREEN, 
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        result_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Récapitulatif global
        recap_frame = tk.Frame(result_frame, bg=CLR_CARD, padx=10, pady=8)
        recap_frame.pack(fill="x", pady=5)
        
        recap_inner = tk.Frame(recap_frame, bg=CLR_CARD)
        recap_inner.pack(fill="x")
        
        # 4 indicateurs
        lbl(recap_inner, "💰 Total ventes:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_ventes_var = tk.StringVar(value="0.00 DA")
        tk.Label(recap_inner, textvariable=self.total_ventes_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(recap_inner, "📦 Cartons:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_cartons_var = tk.StringVar(value="0.00")
        tk.Label(recap_inner, textvariable=self.total_cartons_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(recap_inner, "👥 Clients:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.nb_clients_var = tk.StringVar(value="0")
        tk.Label(recap_inner, textvariable=self.nb_clients_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(recap_inner, "📦 Produits:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.nb_produits_var = tk.StringVar(value="0")
        tk.Label(recap_inner, textvariable=self.nb_produits_var, bg=CLR_CARD, 
                fg=CLR_TEXT, font=("Segoe UI", 13, "bold")).pack(side="left")
        
        # Tableau des clients - AJOUT DES COLONNES Total HT Achat et Marge
        table_frame = tk.Frame(result_frame, bg=CLR_CARD)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # ✅ MODIFICATION: Ajout des colonnes pour le total HT achat et la marge
        cols = ["Client", "Type", "Produits", "Qté Cartons", 
                "Total HT Vente", "Total HT Achat", "Marge", "% du total"]
        widths = [180, 100, 150, 100, 120, 120, 100, 80]
        tf, self.tree = make_tree(table_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # ========== SECTION CALCUL PARTENAIRE ==========
        partenaire_frame = tk.LabelFrame(content, text="3. Calcul Partenaire", 
                                         bg=CLR_CARD, fg=CLR_ORANGE, 
                                         font=("Segoe UI", 10, "bold"),
                                         padx=15, pady=10)
        partenaire_frame.pack(fill="x", padx=20, pady=10)
        
        part_inner = tk.Frame(partenaire_frame, bg=CLR_CARD)
        part_inner.pack(fill="x", pady=5)
        
        # Vos clients
        lbl(part_inner, "🟦 VOS CLIENTS:", 10, True, CLR_ACCENT).pack(side="left", padx=(10,5))
        self.vos_total_var = tk.StringVar(value="0.00 DA")
        tk.Label(part_inner, textvariable=self.vos_total_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0,20))
        
        lbl(part_inner, "🟧 PARTENAIRE:", 10, True, CLR_ORANGE).pack(side="left", padx=(10,5))
        self.part_total_var = tk.StringVar(value="0.00 DA")
        tk.Label(part_inner, textvariable=self.part_total_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0,20))
        
        # ✅ NOUVEAU: Total HT Achat global et Marge globale
        marge_global_frame = tk.Frame(partenaire_frame, bg=CLR_CARD)
        marge_global_frame.pack(fill="x", pady=5)
        
        lbl(marge_global_frame, "📊 Total Achats (coût):", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.total_achat_global_var = tk.StringVar(value="0.00 DA")
        tk.Label(marge_global_frame, textvariable=self.total_achat_global_var, bg=CLR_CARD, 
                fg=CLR_RED, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(marge_global_frame, "💰 Marge brute:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.marge_globale_var = tk.StringVar(value="0.00 DA")
        tk.Label(marge_global_frame, textvariable=self.marge_globale_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0,20))
        
        lbl(marge_global_frame, "📈 Taux de marge:", 10, True, CLR_MUTED).pack(side="left", padx=(10,5))
        self.taux_marge_global_var = tk.StringVar(value="0%")
        tk.Label(marge_global_frame, textvariable=self.taux_marge_global_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 13, "bold")).pack(side="left")
        
        # Boutons d'export
        btn_export = tk.Frame(partenaire_frame, bg=CLR_CARD)
        btn_export.pack(fill="x", pady=10)
        
        tk.Button(btn_export, text="📄 Exporter Rapport", command=self.exporter_rapport,
                 bg=CLR_ACCENT, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_export, text="🖨 Imprimer", command=self.imprimer_analyse,
                 bg=CLR_GREEN, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_export, text="📧 Envoyer au partenaire", command=self.envoyer_partenaire,
                 bg=CLR_ORANGE, fg="white", relief="flat", 
                 font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                 cursor="hand2").pack(side="left", padx=5)
        
        # Espace en bas
        tk.Frame(content, bg=CLR_BG, height=20).pack()
    
    def charger_produits(self):
        """Charge la liste des produits avec filtrage par recherche"""
        # Vider la liste
        for widget in self.prod_inner.winfo_children():
            widget.destroy()
        
        self.prod_checkboxes = {}
        self.prod_labels = {}
        
        search = self.search_var.get().lower()
        
        conn = get_conn()
        if search:
            produits = conn.execute("""
                SELECT id, code, designation, unite, facteur_conversion, fournisseur 
                FROM produits 
                WHERE actif = 1 AND (designation LIKE ? OR code LIKE ? OR fournisseur LIKE ?)
                ORDER BY designation
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            produits = conn.execute("""
                SELECT id, code, designation, unite, facteur_conversion, fournisseur 
                FROM produits WHERE actif = 1 ORDER BY designation
            """).fetchall()
        conn.close()
        
        # Créer une checkbox pour chaque produit
        for p in produits:
            var = tk.IntVar(value=1 if p["id"] in self.produits_selectionnes else 0)
            self.prod_checkboxes[p["id"]] = var
            
            # Déterminer la couleur selon le fournisseur
            fournisseur = p["fournisseur"] or ""
            color = CLR_ACCENT
            if fournisseur.upper() == "CASA":
                color = CLR_ORANGE
            elif fournisseur.upper() == "GINI":
                color = CLR_GREEN
            elif fournisseur.upper() == "BEBETO":
                color = CLR_PURPLE
            
            cb = tk.Checkbutton(
                self.prod_inner,
                text=f"{p['designation']} ({p['code']}) - {fournisseur or 'Sans marque'}",
                variable=var,
                bg=CLR_CARD,
                fg=color,
                selectcolor=CLR_INPUT,
                activebackground=CLR_CARD,
                font=("Segoe UI", 9),
                cursor="hand2",
                anchor="w",
                padx=5,
                pady=2
            )
            cb.pack(fill="x", padx=5, pady=1)
            self.prod_labels[p["id"]] = cb
            
            # Mettre à jour le compteur quand on coche/décoche
            var.trace_add("write", self.mettre_a_jour_compteur)
        
        self.mettre_a_jour_compteur()
    
    def mettre_a_jour_compteur(self, *args):
        """Met à jour le compteur des produits sélectionnés"""
        count = sum(1 for var in self.prod_checkboxes.values() if var.get() == 1)
        # Chercher le label "Produits sélectionnés"
        for child in self.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subchild, tk.Label) and "Produits sélectionnés" in subchild.cget("text"):
                    subchild.config(text=f"Produits sélectionnés: {count}")
                    break
    
    def tout_selectionner(self):
        """Sélectionne tous les produits affichés"""
        for var in self.prod_checkboxes.values():
            var.set(1)
    
    def tout_deselectionner(self):
        """Désélectionne tous les produits"""
        for var in self.prod_checkboxes.values():
            var.set(0)
    
    def analyser(self):
        """Analyse les produits sélectionnés"""
        # Récupérer les IDs des produits sélectionnés
        self.produits_selectionnes = [pid for pid, var in self.prod_checkboxes.items() if var.get() == 1]
        
        if not self.produits_selectionnes:
            messagebox.showwarning("Avertissement", "Sélectionnez au moins un produit à analyser")
            return
        
        # Vider le tableau
        self.tree.delete(*self.tree.get_children())
        
        # Construire la requête - MAINTENANT AVEC LES PRIX D'ACHAT
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        placeholders = ",".join("?" * len(self.produits_selectionnes))
        
        # ✅ NOUVELLE REQUÊTE: Récupérer aussi le prix d'achat pour calculer le coût
        query = f"""
            SELECT 
                c.id as client_id,
                c.nom as client_nom,
                COUNT(DISTINCT lv.produit_id) as nb_produits,
                COALESCE(SUM(lv.quantite / NULLIF(p.facteur_conversion, 0)), 0) as total_cartons,
                COALESCE(SUM(lv.total), 0) as total_vente_ht,
                COALESCE(SUM(lv.quantite * COALESCE(NULLIF(p.prix_moyen_pondere, 0), p.prix_achat, 0)), 0) as total_achat_ht,
                COALESCE(SUM(lv.total * (1 + COALESCE(p.tva, 0) / 100)), 0) as total_vente_ttc
            FROM lignes_vente lv
            JOIN bons_vente bv ON lv.bon_id = bv.id
            JOIN clients c ON bv.client_id = c.id
            JOIN produits p ON lv.produit_id = p.id
            WHERE lv.produit_id IN ({placeholders})
            AND bv.statut = 'Validé'
        """
        
        params = list(self.produits_selectionnes)
        
        if date_debut and date_fin:
            query += " AND bv.date_bon BETWEEN ? AND ?"
            params.extend([date_debut, date_fin])
        
        query += " GROUP BY c.id, c.nom ORDER BY total_vente_ht DESC"
        
        conn = get_conn()
        rows = conn.execute(query, params).fetchall()
        
        # Calcul des totaux
        total_global_vente = 0
        total_global_achat = 0
        total_global_cartons = 0
        total_vos = 0
        total_part = 0
        
        # Déterminer les clients du partenaire
        clients_partenaire = ["PARTENAIRE", "CASA PARTENAIRE"]
        
        for r in rows:
            total_global_vente += r["total_vente_ht"]
            total_global_achat += r["total_achat_ht"]
            total_global_cartons += r["total_cartons"]
            
            # Déterminer le type de client
            is_partenaire = any(p in r["client_nom"].upper() for p in clients_partenaire)
            type_client = "Partenaire" if is_partenaire else "Vos clients"
            
            if is_partenaire:
                total_part += r["total_vente_ht"]
            else:
                total_vos += r["total_vente_ht"]
            
            # Calcul de la marge pour ce client
            marge = r["total_vente_ht"] - r["total_achat_ht"]
            taux_marge = (marge / r["total_vente_ht"] * 100) if r["total_vente_ht"] > 0 else 0
            
            # Pourcentage du total
            pct = (r["total_vente_ht"] / total_global_vente * 100) if total_global_vente > 0 else 0
            
            # ✅ AJOUT: Colonnes Total HT Achat et Marge
            self.tree.insert("", "end", values=(
                r["client_nom"],
                type_client,
                f"{r['nb_produits']} produits",
                f"{r['total_cartons']:.2f}",
                f"{r['total_vente_ht']:,.2f} DA",
                f"{r['total_achat_ht']:,.2f} DA",
                f"{marge:,.2f} DA ({taux_marge:.1f}%)",
                f"{pct:.1f}%"
            ))
        
        conn.close()
        
        # Mettre à jour les indicateurs
        self.total_ventes_var.set(f"{total_global_vente:,.2f} DA")
        self.total_cartons_var.set(f"{total_global_cartons:.2f}")
        self.nb_clients_var.set(str(len(rows)))
        self.nb_produits_var.set(str(len(self.produits_selectionnes)))
        
        # Mettre à jour le calcul partenaire
        self.vos_total_var.set(f"{total_vos:,.2f} DA")
        self.part_total_var.set(f"{total_part:,.2f} DA")
        
        # ✅ NOUVEAU: Mettre à jour les indicateurs d'achat et marge
        self.total_achat_global_var.set(f"{total_global_achat:,.2f} DA")
        marge_globale = total_global_vente - total_global_achat
        self.marge_globale_var.set(f"{marge_globale:,.2f} DA")
        taux_marge_global = (marge_globale / total_global_vente * 100) if total_global_vente > 0 else 0
        self.taux_marge_global_var.set(f"{taux_marge_global:.1f}%")
        
        # Mettre à jour les pourcentages dans le titre
        total = total_vos + total_part
        if total > 0:
            vos_pct = (total_vos / total * 100)
            part_pct = (total_part / total * 100)
            # Mettre à jour les labels des cadres
            for child in self.winfo_children():
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.LabelFrame) and "Calcul Partenaire" in subchild.cget("text"):
                        for inner in subchild.winfo_children():
                            if isinstance(inner, tk.Frame):
                                for lbl_widget in inner.winfo_children():
                                    if isinstance(lbl_widget, tk.Label) and "pourcentage" in lbl_widget.cget("text"):
                                        parent_frame = lbl_widget.master
                                        for child_widget in parent_frame.winfo_children():
                                            if isinstance(child_widget, tk.Label) and "DA" not in child_widget.cget("text"):
                                                if "VOS" in parent_frame.winfo_children()[0].cget("text"):
                                                    child_widget.config(text=f"{vos_pct:.1f}%")
                                                else:
                                                    child_widget.config(text=f"{part_pct:.1f}%")
        
        # ✅ Afficher un message avec plus d'informations
        messagebox.showinfo("Succès", f"✅ Analyse terminée !\n\n"
                            f"📊 Produits analysés: {len(self.produits_selectionnes)}\n"
                            f"👥 Clients concernés: {len(rows)}\n"
                            f"💰 Total ventes HT: {total_global_vente:,.2f} DA\n"
                            f"📦 Total achats HT: {total_global_achat:,.2f} DA\n"
                            f"💹 Marge brute: {marge_globale:,.2f} DA ({taux_marge_global:.1f}%)")
    
    def exporter_rapport(self):
        """Exporter le rapport en CSV"""
        if not self.produits_selectionnes:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        # ✅ MODIFICATION: Ajout des colonnes Total HT Achat et Marge
        headers = ["Client", "Type", "Produits", "Qté Cartons", 
                   "Total HT Vente", "Total HT Achat", "Marge", "% du total"]
        
        # Ajouter les totaux
        data.append(["", "", "", "", "", "", "", ""])
        data.append(["TOTAL", "", 
                    self.nb_produits_var.get(), 
                    self.total_cartons_var.get(),
                    self.total_ventes_var.get(),
                    self.total_achat_global_var.get(),
                    self.marge_globale_var.get(),
                    self.taux_marge_global_var.get()])
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"analyse_produits_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        
        if filename:
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    def imprimer_analyse(self):
        """Imprimer l'analyse"""
        if not self.produits_selectionnes:
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        if not data:
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        headers = ["Client", "Type", "Produits", "Qté Cartons", 
                   "Total HT Vente", "Total HT Achat", "Marge", "% du total"]
        
        # Ajouter les totaux
        data.append(["", "", "", "", "", "", "", ""])
        data.append(["TOTAL", "", 
                    self.nb_produits_var.get(), 
                    self.total_cartons_var.get(),
                    self.total_ventes_var.get(),
                    self.total_achat_global_var.get(),
                    self.marge_globale_var.get(),
                    self.taux_marge_global_var.get()])
        
        # Ajouter les informations sur les produits sélectionnés
        conn = get_conn()
        produits = conn.execute(
            f"SELECT designation, fournisseur, prix_achat, prix_moyen_pondere FROM produits WHERE id IN ({','.join('?' * len(self.produits_selectionnes))})",
            self.produits_selectionnes
        ).fetchall()
        conn.close()
        
        footer = "📦 Produits analysés:\n"
        for p in produits:
            prix_achat = p['prix_achat'] or 0
            prix_moyen = p['prix_moyen_pondere'] or 0
            prix_utilise = prix_moyen if prix_moyen > 0 else prix_achat
            footer += f"  - {p['designation']} ({p['fournisseur'] or 'Sans marque'}) - PMP: {prix_utilise:.2f} DA\n"
        
        footer += f"\n📊 Période: {self.date_debut_var.get()} → {self.date_fin_var.get()}"
        
        title = f"ANALYSE DES PRODUITS SÉLECTIONNÉS\n{datetime.now().strftime('%d/%m/%Y')}"
        
        print_preview(data, title, headers, footer_text=footer)
    
    def envoyer_partenaire(self):
        """Simuler l'envoi au partenaire"""
        messagebox.showinfo("Envoi au partenaire", 
                           "📧 Fonctionnalité à implémenter\n\n"
                           "Cette fonction générera un rapport PDF\n"
                           "et l'enverra par email au partenaire.")
if __name__ == "__main__":
    app = App()
    app.mainloop()