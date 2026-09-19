#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE PRIX MULTI-NIVEAUX
==========================
Ajoute 4 niveaux de prix par produit :
  - Prix Super Gros  (vente en très grande quantité)
  - Prix Gros        (vente en grande quantité)
  - Prix Détail      (vente au détail / standard)
  - Prix Spécial     (prix négocié / promotionnel)

INTÉGRATION DANS VOTRE CODE PRINCIPAL :
=========================================

ÉTAPE 1 — Migration base de données
-------------------------------------
Appelez  migrer_prix_niveaux()  UNE SEULE FOIS après init_db() dans App.__init__ :

    init_db()
    migrer_prix_niveaux()          # ← ajouter cette ligne
    self._pages = {}
    self._build()


ÉTAPE 2 — Remplacer les stubs
-------------------------------
Supprimez les 4 classes stub à la fin de votre fichier principal
et collez ce fichier entier à leur place (ou importez-le).


ÉTAPE 3 — Modifier ProduitDialog
----------------------------------
Dans ProduitDialog._build(), remplacez les champs prix_vente
par l'appel à  PrixNiveauxFrame(f, self.vars, self.data)
(voir commentaire dans le code ci-dessous).


ÉTAPE 4 — Modifier BonDialog / VenteComptoirDialog
----------------------------------------------------
Remplacez le combo produit et la saisie du prix par
PrixSelectorWidget (voir bas de fichier).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# ========== DÉFINITIONS DES COULEURS ==========
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

# ========== FONCTIONS NÉCESSAIRES ==========
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

def parse_decimal(value):
    """Convertit une chaîne en décimal"""
    if not value:
        return 0.0
    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0

from api.db import get_conn  # noqa: E402,F401  (connexion unique)

def make_tree(parent, columns, col_widths=None):
    """Crée un arbre avec style (version simplifiée)"""
    style = ttk.Style()
    style.configure("Dark.Treeview",
                    background=CLR_CARD, foreground=CLR_TEXT,
                    fieldbackground=CLR_CARD, rowheight=26)
    
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
        tree.column(col, width=w, minwidth=60)
    
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    return frame, tree

def print_preview(data, title, headers):
    """Aperçu avant impression (version simplifiée)"""
    preview = tk.Toplevel()
    preview.title(f"Aperçu - {title}")
    preview.geometry("800x600")
    preview.configure(bg=CLR_BG)
    
    text_widget = tk.Text(preview, wrap="none", font=("Courier", 9))
    scrollbar_y = tk.Scrollbar(preview, orient="vertical", command=text_widget.yview)
    scrollbar_x = tk.Scrollbar(preview, orient="horizontal", command=text_widget.xview)
    text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
    
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar_y.pack(side="right", fill="y")
    scrollbar_x.pack(side="bottom", fill="x")
    
    content = f"\n{'='*80}\n{title:^80}\n{'='*80}\n\n"
    for header in headers:
        content += f"{header:<20}"
    content += "\n" + "-"*80 + "\n"
    
    for row in data:
        for cell in row:
            content += f"{str(cell):<20}"
        content += "\n"
    
    text_widget.insert("1.0", content)
    text_widget.configure(state="disabled")
    
    tk.Button(preview, text="Fermer", command=preview.destroy,
              bg=CLR_ACCENT, fg="white", padx=15, pady=8).pack(pady=10)

def lbl(parent, text, size=9, bold=False, color=CLR_TEXT, **kw):
    """Label stylisé"""
    style = "bold" if bold else "normal"
    if 'bg' not in kw:
        kw['bg'] = parent["bg"] if hasattr(parent, "bg") else CLR_BG
    return tk.Label(parent, text=text, fg=color, font=("Segoe UI", size, style), **kw)
NIVEAUX_PRIX = [
    ("prix_super_gros",  "Super Gros"),
    ("prix_gros",        "Gros"),
    ("prix_detail",      "Détail"),
    ("prix_special",     "Spécial"),
]

def migrer_prix_niveaux():
    """
    Conservée pour compatibilité. Les colonnes de prix multi-niveaux et la table
    clients_niveau_prix sont désormais créées par le schéma unique (api/schema.py) :
    on délègue simplement à init_db() (idempotent).
    """
    try:
        from api.db import init_db
        init_db()
    except Exception as e:
        print(f"[migrer_prix_niveaux] Erreur : {e}")


def get_prix_produit(produit_id, niveau="detail"):
    """
    Retourne le prix du produit pour le niveau demandé.
    Fallback sur prix_vente si la colonne est 0 ou absente.
    """
    col_map = {
        "super_gros": "prix_super_gros",
        "gros":       "prix_gros",
        "detail":     "prix_detail",
        "special":    "prix_special",
    }
    col = col_map.get(niveau, "prix_detail")
    conn = get_conn()
    row = conn.execute(
        f"SELECT {col}, prix_vente FROM produits WHERE id=?", (produit_id,)
    ).fetchone()
    conn.close()
    if not row:
        return 0.0
    val = row[col] or 0.0
    return val if val > 0 else (row["prix_vente"] or 0.0)


def get_niveau_client(client_id):
    """Retourne le niveau de prix par défaut d'un client."""
    conn = get_conn()
    row = conn.execute(
        "SELECT niveau FROM clients_niveau_prix WHERE client_id=?",
        (client_id,)
    ).fetchone()
    conn.close()
    return row["niveau"] if row else "detail"


def set_niveau_client(client_id, niveau):
    """Définit le niveau de prix par défaut d'un client."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO clients_niveau_prix(client_id, niveau)
        VALUES(?,?)
        ON CONFLICT(client_id) DO UPDATE SET niveau=excluded.niveau
    """, (client_id, niveau))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET : FRAME DES 4 PRIX (à intégrer dans ProduitDialog)
# ══════════════════════════════════════════════════════════════════════════════

class PrixNiveauxFrame(tk.LabelFrame):
    """
    Widget autonome affichant les 4 champs de prix + prix d'achat.
    Usage dans ProduitDialog._build() :

        # Remplacer le champ unique "Prix Vente" par :
        pnf = PrixNiveauxFrame(f, self.vars, self.data)
        pnf.grid(row=ROW, column=0, columnspan=3, sticky="ew", pady=8)
    """

    def __init__(self, parent, vars_dict, data=None, **kw):
        super().__init__(
            parent,
            text="💰  Grille de Prix",
            bg=CLR_CARD if hasattr(parent, "winfo_class") else CLR_BG,
            fg=CLR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            padx=12, pady=8,
            **kw
        )
        self._bg = self["bg"]
        self.vars_dict = vars_dict
        self.data       = data or {}
        self._build()

    def _build(self):
        LABELS = [
            ("Prix Achat",     "prix_achat",     CLR_MUTED),
            ("Prix Super Gros","prix_super_gros", CLR_ACCENT),
            ("Prix Gros",      "prix_gros",       CLR_GREEN),
            ("Prix Détail",    "prix_detail",     CLR_ORANGE),
            ("Prix Spécial",   "prix_special",    CLR_RED),
        ]

        for col, (lbl_txt, key, clr) in enumerate(LABELS):
            tk.Label(self, text=lbl_txt, bg=self._bg, fg=clr,
                     font=("Segoe UI", 8, "bold")).grid(
                row=0, column=col, padx=8, pady=(4, 2), sticky="w"
            )

            v = tk.StringVar()
            # Chercher la valeur dans data
            val = self.data.get(key, "") or self.data.get("prix_vente", "")
            if val:
                v.set(str(val))

            e = tk.Entry(
                self, textvariable=v, width=12,
                bg=CLR_INPUT, fg=CLR_TEXT,
                insertbackground=CLR_TEXT, relief="flat",
                highlightthickness=1, highlightbackground=CLR_BORDER,
                highlightcolor=clr, font=("Segoe UI", 9, "bold")
            )
            e.grid(row=1, column=col, padx=8, pady=4)
            self.vars_dict[key] = v

        # Bouton copier depuis prix_achat
        tk.Button(
            self, text="📋 Copier PA → tous",
            command=self._copier_depuis_achat,
            bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
            font=("Segoe UI", 8), padx=8, pady=3, cursor="hand2"
        ).grid(row=2, column=0, columnspan=2, padx=8, pady=(6, 2), sticky="w")

        tk.Button(
            self, text="% Calculer automatiquement",
            command=self._calculer_auto,
            bg=CLR_ACCENT, fg="white", relief="flat",
            font=("Segoe UI", 8, "bold"), padx=8, pady=3, cursor="hand2"
        ).grid(row=2, column=2, columnspan=3, padx=8, pady=(6, 2), sticky="e")

    def _copier_depuis_achat(self):
        """Copie le prix d'achat dans tous les niveaux."""
        try:
            pa = float(self.vars_dict.get("prix_achat", tk.StringVar()).get() or 0)
        except ValueError:
            return
        for col in ("prix_super_gros", "prix_gros", "prix_detail", "prix_special"):
            if col in self.vars_dict:
                self.vars_dict[col].set(f"{pa:.2f}")

    def _calculer_auto(self):
        """Ouvre un mini-dialogue pour calculer les prix par marge."""
        d = tk.Toplevel(self)
        d.title("Calcul automatique des prix")
        d.configure(bg=CLR_BG)
        d.geometry("420x300")
        d.grab_set()
        center_window(d, 420, 300)

        f = tk.Frame(d, bg=CLR_BG, padx=20, pady=15)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Calcul par % de marge sur le Prix d'Achat",
                 bg=CLR_BG, fg=CLR_ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 12))

        try:
            pa = float(self.vars_dict.get("prix_achat", tk.StringVar()).get() or 0)
        except ValueError:
            pa = 0.0

        tk.Label(f, text=f"Prix d'achat : {pa:.2f} DA",
                 bg=CLR_BG, fg=CLR_TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w")

        DEFAULTS = [
            ("Super Gros (%)", "prix_super_gros", "10"),
            ("Gros (%)",       "prix_gros",       "20"),
            ("Détail (%)",     "prix_detail",     "35"),
            ("Spécial (%)",    "prix_special",    "15"),
        ]

        marge_vars = {}
        for lbl_txt, key, default in DEFAULTS:
            row = tk.Frame(f, bg=CLR_BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=lbl_txt, bg=CLR_BG, fg=CLR_MUTED,
                     font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
            v = tk.StringVar(value=default)
            tk.Entry(row, textvariable=v, width=8,
                     bg=CLR_INPUT, fg=CLR_TEXT, relief="flat").pack(side="left", padx=8)
            marge_vars[key] = v

        def appliquer():
            for key, mv in marge_vars.items():
                try:
                    pct  = float(mv.get() or 0)
                    prix = pa * (1 + pct / 100)
                    if key in self.vars_dict:
                        self.vars_dict[key].set(f"{prix:.2f}")
                except ValueError:
                    pass
            d.destroy()

        tk.Button(f, text="✅ Appliquer",
                  command=appliquer,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"),
                  padx=14, pady=7, cursor="hand2").pack(pady=12)


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET : SÉLECTEUR DE PRIX (à intégrer dans BonDialog / VenteComptoir)
# ══════════════════════════════════════════════════════════════════════════════

class PrixSelectorWidget(tk.Frame):
    NIVEAUX = [
        ("super_gros", "SUPER GROS", CLR_ACCENT),
        ("gros",       "GROS",       CLR_GREEN),
        ("detail",     "DÉTAIL",     CLR_ORANGE),
        ("special",    "SPÉCIAL",    CLR_RED),
    ]

    def __init__(self, parent, prix_var, client_id_fn=None, **kw):
        super().__init__(parent, bg=CLR_CARD, **kw)
        self.prix_var     = prix_var
        self.client_id_fn = client_id_fn
        self.produit      = None
        self.niveau_actif = "detail"
        self._btns        = {}
        self._build()

    def _build(self):
        tk.Label(self, text="Niveau de prix :",
                 bg=CLR_CARD, fg=CLR_MUTED,
                 font=("Segoe UI", 8)).pack(side="left", padx=(8, 4))

        for niveau, label, couleur in self.NIVEAUX:
            btn = tk.Button(
                self, text=label,
                bg=CLR_BORDER, fg=CLR_TEXT,
                relief="flat", font=("Segoe UI", 8, "bold"),
                padx=10, pady=4, cursor="hand2",
                command=lambda n=niveau: self.choisir_niveau(n)
            )
            btn.pack(side="left", padx=3)
            self._btns[niveau] = (btn, couleur)

        self.prix_label = tk.Label(
            self, text="0.00 DA",
            bg=CLR_CARD, fg=CLR_GREEN,
            font=("Segoe UI", 10, "bold")
        )
        self.prix_label.pack(side="left", padx=12)

    def _selectionner_bouton(self, niveau):
        for n, (btn, clr) in self._btns.items():
            if n == niveau:
                btn.config(bg=clr, fg="white")
            else:
                btn.config(bg=CLR_BORDER, fg=CLR_TEXT)
        self.niveau_actif = niveau

    def _get_prix_special_client(self, produit_id):
        """Retourne le prix spécial client ou None."""
        if not self.client_id_fn or not produit_id:
            return None
        try:
            client_id = self.client_id_fn()
        except Exception:
            return None
        if not client_id:
            return None
        try:
            conn = get_conn()
            row = conn.execute("""
                SELECT prix_special FROM prix_speciaux_clients
                WHERE client_id = ? AND produit_id = ? AND actif = 1
            """, (client_id, produit_id)).fetchone()
            conn.close()
            if row:
                return float(row["prix_special"])
        except Exception:
            pass
        return None

    def _get_niveau_client(self):
        """Retourne le niveau de prix du client sélectionné."""
        if not self.client_id_fn:
            return "detail"
        try:
            client_id = self.client_id_fn()
        except Exception:
            return "detail"
        if not client_id:
            return "detail"
        try:
            conn = get_conn()
            # Essayer d'abord la table clients_niveau_prix
            row = conn.execute(
                "SELECT niveau FROM clients_niveau_prix WHERE client_id=?",
                (client_id,)
            ).fetchone()
            if row and row["niveau"]:
                conn.close()
                return row["niveau"]
            # Fallback sur la colonne niveau_prix dans clients
            cols = [c[1] for c in conn.execute("PRAGMA table_info(clients)").fetchall()]
            if "niveau_prix" in cols:
                client = conn.execute(
                    "SELECT niveau_prix FROM clients WHERE id=?", (client_id,)
                ).fetchone()
                if client and client["niveau_prix"]:
                    conn.close()
                    return client["niveau_prix"]
            conn.close()
        except Exception as e:
            print(f"[PrixSelectorWidget] Erreur niveau client: {e}")
        return "detail"

    def set_produit(self, produit):
        """Appelé quand le produit ou le client change."""
        self.produit = produit
        if not produit:
            return

        # 1. Prix spécial client ?
        prix_special = self._get_prix_special_client(produit.get("id"))
        if prix_special is not None and prix_special > 0:
            if self.prix_var:
                self.prix_var.set(f"{prix_special:.2f}")
            self.prix_label.config(text=f"{prix_special:,.2f} DA ★")
            self._selectionner_bouton("special")
            return

        # 2. Niveau par défaut du client
        niveau = self._get_niveau_client()
        self._selectionner_bouton(niveau)
        self._afficher_prix()

    def choisir_niveau(self, niveau):
        """Changement manuel du niveau."""
        self._selectionner_bouton(niveau)
        self._afficher_prix()

    def _afficher_prix(self):
        """Met à jour la StringVar et le label selon le niveau actif."""
        if not self.produit:
            return
        col_map = {
            "super_gros": "prix_super_gros",
            "gros":       "prix_gros",
            "detail":     "prix_detail",
            "special":    "prix_special",
        }
        col  = col_map.get(self.niveau_actif, "prix_detail")
        prix = float(self.produit.get(col) or 0)
        if prix == 0:
            prix = float(self.produit.get("prix_vente") or 0)

        if self.prix_var:
            self.prix_var.set(f"{prix:.2f}")
        self.prix_label.config(text=f"{prix:,.2f} DA")

    def get_niveau(self):
        return self.niveau_actif


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE COMPLÈTE : GRILLE DES PRIX PRODUITS
# ══════════════════════════════════════════════════════════════════════════════

class GrillePrixPage(tk.Frame):
    """
    Page dédiée à la visualisation et modification en masse
    de la grille de prix de tous les produits.

    Ajouter dans App._build() et show_page() :
        ("💲", "Grille des Prix", "grille_prix"),
        ...
        elif key == "grille_prix":
            self._pages[key] = GrillePrixPage(self.main)
    """

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    def _build(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20, 10))
        lbl(hdr, "💲  Grille des Prix", 16, True).pack(side="left")

        btn_f = tk.Frame(hdr, bg=CLR_BG)
        btn_f.pack(side="right")

        tk.Button(btn_f, text="💾 Enregistrer tout",
                  command=self.sauvegarder_tout,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                  cursor="hand2").pack(side="left", padx=4)

        tk.Button(btn_f, text="📋 Calcul auto par %",
                  command=self.calcul_auto_global,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                  cursor="hand2").pack(side="left", padx=4)

        tk.Button(btn_f, text="🔄 Actualiser",
                  command=self.refresh,
                  bg=CLR_ORANGE, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7,
                  cursor="hand2").pack(side="left", padx=4)

        tk.Button(btn_f, text="🖨 Imprimer",
                  command=self.imprimer,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7,
                  cursor="hand2").pack(side="left", padx=4)

        # ── Recherche ─────────────────────────────────────────────────────────
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche :", color=CLR_MUTED).pack(side="left")
        self.sv = tk.StringVar()
        self.sv.trace_add("write", lambda *a: self.refresh())
        e = tk.Entry(sf, textvariable=self.sv, width=30,
                     bg=CLR_INPUT, fg=CLR_TEXT, relief="flat",
                     highlightthickness=1, highlightbackground=CLR_BORDER,
                     highlightcolor=CLR_ACCENT)
        e.pack(side="left", padx=8)

        # ── Légende couleurs ─────────────────────────────────────────────────
        leg_f = tk.Frame(self, bg=CLR_BG)
        leg_f.pack(fill="x", padx=20, pady=(0, 5))
        for label, clr in [("Super Gros", CLR_ACCENT), ("Gros", CLR_GREEN),
                            ("Détail", CLR_ORANGE), ("Spécial", CLR_RED)]:
            tk.Label(leg_f, text=f"■ {label}", bg=CLR_BG, fg=clr,
                     font=("Segoe UI", 8, "bold")).pack(side="left", padx=8)

        # ── Tableau ───────────────────────────────────────────────────────────
        cols   = ["Code", "Désignation", "Unité",
                  "Prix Achat", "Super Gros", "Gros", "Détail", "Spécial",
                  "Marge SG%", "Marge G%", "Marge D%", "Marge S%"]
        widths = [80, 220, 60, 90, 90, 90, 90, 90, 80, 80, 80, 80]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=5)

        # Colorier les colonnes de prix
        self.tree.tag_configure("sg", foreground=CLR_ACCENT)
        self.tree.tag_configure("normal", foreground=CLR_TEXT)

        # ── Boutons éditeur rapide ─────────────────────────────────────────
        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0, 15))

        tk.Button(bf, text="✏ Modifier prix produit",
                  command=self.modifier_prix,
                  bg=CLR_ORANGE, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="left", padx=4)

        tk.Button(bf, text="👥 Niveaux par client",
                  command=self.gerer_niveaux_clients,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="left", padx=4)

        self.tree.bind("<Double-1>", lambda e: self.modifier_prix())

    # ── Chargement ────────────────────────────────────────────────────────────

    def refresh(self):
        q = self.sv.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        rows = conn.execute("""
            SELECT id, code, designation, unite,
                   prix_achat,
                   COALESCE(prix_super_gros, prix_vente, 0) as prix_super_gros,
                   COALESCE(prix_gros,       prix_vente, 0) as prix_gros,
                   COALESCE(prix_detail,     prix_vente, 0) as prix_detail,
                   COALESCE(prix_special,    prix_vente, 0) as prix_special
            FROM produits
            WHERE actif = 1
            ORDER BY designation
        """).fetchall()
        conn.close()

        for r in rows:
            if q and q not in r["code"].lower() and q not in r["designation"].lower():
                continue

            pa = r["prix_achat"] or 0.0

            def marge(px):
                if pa > 0 and px > 0:
                    return f"{((px - pa) / pa * 100):+.1f}%"
                return "—"

            sg = r["prix_super_gros"] or 0.0
            g  = r["prix_gros"]       or 0.0
            d  = r["prix_detail"]     or 0.0
            s  = r["prix_special"]    or 0.0

            self.tree.insert("", "end", iid=r["id"], values=(
                r["code"], r["designation"], r["unite"] or "",
                f"{pa:.2f}",
                f"{sg:.2f}", f"{g:.2f}", f"{d:.2f}", f"{s:.2f}",
                marge(sg), marge(g), marge(d), marge(s)
            ))

    # ── Modifier un produit ───────────────────────────────────────────────────

    def modifier_prix(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un produit")
            return
        conn = get_conn()
        row = conn.execute("SELECT * FROM produits WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        d = EditPrixDialog(self, dict(row))
        self.wait_window(d)
        self.refresh()

    # ── Calcul auto global ────────────────────────────────────────────────────

    def calcul_auto_global(self):
        """Applique des % de marge uniformes à tous les produits."""
        d = CalcAutoGlobalDialog(self)
        self.wait_window(d)
        self.refresh()

    # ── Enregistrer tout (depuis le tableau éditable) ─────────────────────────

    def sauvegarder_tout(self):
        """
        Enregistre tous les prix visibles dans le tableau.
        Les valeurs sont celles actuellement affichées
        (après modification via EditPrixDialog).
        """
        messagebox.showinfo(
            "Info",
            "Utilisez le bouton '✏ Modifier prix produit' pour\n"
            "éditer chaque produit individuellement.\n\n"
            "Pour modifier en masse, utilisez '📋 Calcul auto par %'."
        )

    # ── Niveaux par client ────────────────────────────────────────────────────

    def gerer_niveaux_clients(self):
        d = NiveauxClientsDialog(self)
        self.wait_window(d)

    # ── Impression ────────────────────────────────────────────────────────────

    def imprimer(self):
        data = [
            list(self.tree.item(iid, "values"))
            for iid in self.tree.get_children()
        ]
        headers = ["Code", "Désignation", "Unité",
                   "Prix Achat", "Super Gros", "Gros", "Détail", "Spécial",
                   "Marge SG%", "Marge G%", "Marge D%", "Marge S%"]
        print_preview(data, "GRILLE DES PRIX", headers)


# ── Dialogue édition des prix d'un produit ────────────────────────────────────

class EditPrixDialog(tk.Toplevel):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.data = data
        self.title(f"Prix — {data['designation']}")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        center_window(self, 560, 380)

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=25, pady=20)
        f.pack(fill="both", expand=True)

        lbl(f, f"💲 PRIX — {self.data['designation']}", 12, True,
            CLR_ACCENT).grid(row=0, columnspan=4, pady=(0, 15))

        CHAMPS = [
            ("Prix Achat",     "prix_achat",     CLR_MUTED),
            ("Prix Super Gros","prix_super_gros", CLR_ACCENT),
            ("Prix Gros",      "prix_gros",       CLR_GREEN),
            ("Prix Détail",    "prix_detail",     CLR_ORANGE),
            ("Prix Spécial",   "prix_special",    CLR_RED),
        ]

        self.vars = {}
        for i, (lt, key, clr) in enumerate(CHAMPS, start=1):
            tk.Label(f, text=lt, bg=CLR_BG, fg=clr,
                     font=("Segoe UI", 9, "bold")).grid(
                row=i, column=0, sticky="w", pady=5
            )
            v = tk.StringVar(value=f"{float(self.data.get(key) or 0):.2f}")
            e = tk.Entry(f, textvariable=v, width=14,
                         bg=CLR_INPUT, fg=CLR_TEXT, relief="flat",
                         highlightthickness=1, highlightbackground=clr,
                         highlightcolor=clr, font=("Segoe UI", 10, "bold"),
                         justify="right")
            e.grid(row=i, column=1, padx=10, pady=5)
            self.vars[key] = v

            # Label marge calculée
            marge_lbl = tk.Label(f, text="", bg=CLR_BG, fg=CLR_MUTED,
                                 font=("Segoe UI", 8))
            marge_lbl.grid(row=i, column=2, padx=5)
            v.trace_add("write", lambda *a, k=key, ml=marge_lbl: self._update_marge(k, ml))
            self._update_marge(key, marge_lbl)

        # Bouton copier depuis achat
        tk.Button(f, text="📋 Copier PA → tous",
                  command=self._copier_achat,
                  bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                  font=("Segoe UI", 8), padx=8, pady=3,
                  cursor="hand2").grid(row=6, column=0, pady=8, sticky="w")

        tk.Button(f, text="% Auto",
                  command=self._auto_pct,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 8, "bold"), padx=8, pady=3,
                  cursor="hand2").grid(row=6, column=1, pady=8)

        bf = tk.Frame(f, bg=CLR_BG)
        bf.grid(row=7, columnspan=4, pady=12)
        tk.Button(bf, text="💾 Enregistrer", command=self.save,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                  cursor="hand2").pack(side="left", padx=6)
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                  font=("Segoe UI", 9), padx=14, pady=7,
                  cursor="hand2").pack(side="left", padx=6)

    def _update_marge(self, key, label):
        try:
            pa = float(self.vars.get("prix_achat", tk.StringVar()).get() or 0)
            px = float(self.vars[key].get() or 0)
            if pa > 0 and px > 0 and key != "prix_achat":
                m = (px - pa) / pa * 100
                label.config(text=f"(marge {m:+.1f}%)",
                             fg=CLR_GREEN if m > 0 else CLR_RED)
            else:
                label.config(text="")
        except (ValueError, KeyError):
            label.config(text="")

    def _copier_achat(self):
        try:
            pa = float(self.vars["prix_achat"].get() or 0)
            for k in ("prix_super_gros", "prix_gros", "prix_detail", "prix_special"):
                self.vars[k].set(f"{pa:.2f}")
        except ValueError:
            pass

    def _auto_pct(self):
        """Fenêtre rapide pour saisir les 4 marges en %."""
        w = tk.Toplevel(self)
        w.title("Marges automatiques")
        w.configure(bg=CLR_BG)
        w.grab_set()
        center_window(w, 360, 280)

        ff = tk.Frame(w, bg=CLR_BG, padx=20, pady=15)
        ff.pack(fill="both", expand=True)

        try:
            pa = float(self.vars["prix_achat"].get() or 0)
        except ValueError:
            pa = 0.0

        tk.Label(ff, text=f"PA = {pa:.2f} DA",
                 bg=CLR_BG, fg=CLR_TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))

        fields = [
            ("Super Gros (%)", "prix_super_gros", "10"),
            ("Gros (%)",       "prix_gros",       "20"),
            ("Détail (%)",     "prix_detail",     "35"),
            ("Spécial (%)",    "prix_special",    "15"),
        ]
        pct_vars = {}
        for lt, key, dflt in fields:
            row = tk.Frame(ff, bg=CLR_BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=lt, bg=CLR_BG, fg=CLR_MUTED,
                     font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
            v = tk.StringVar(value=dflt)
            tk.Entry(row, textvariable=v, width=8,
                     bg=CLR_INPUT, fg=CLR_TEXT, relief="flat").pack(side="left", padx=6)
            pct_vars[key] = v

        def appliquer():
            for key, pv in pct_vars.items():
                try:
                    pct  = float(pv.get() or 0)
                    prix = pa * (1 + pct / 100)
                    self.vars[key].set(f"{prix:.2f}")
                except ValueError:
                    pass
            w.destroy()

        tk.Button(ff, text="✅ Appliquer",
                  command=appliquer,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(pady=10)

    def save(self):
        conn = get_conn()
        try:
            vals = {}
            for key, v in self.vars.items():
                try:
                    vals[key] = parse_decimal(v.get() or "0")
                except ValueError:
                    vals[key] = 0.0

            conn.execute("""
                UPDATE produits
                SET prix_achat      = ?,
                    prix_super_gros = ?,
                    prix_gros       = ?,
                    prix_detail     = ?,
                    prix_special    = ?,
                    prix_vente      = ?
                WHERE id = ?
            """, (
                vals["prix_achat"],
                vals["prix_super_gros"],
                vals["prix_gros"],
                vals["prix_detail"],
                vals["prix_special"],
                vals["prix_detail"],   # prix_vente = prix détail par défaut
                self.data["id"]
            ))
            conn.commit()
            messagebox.showinfo("Succès", "Prix enregistrés ✅")
            self.destroy()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex))
        finally:
            conn.close()


# ── Dialogue calcul auto global ───────────────────────────────────────────────

class CalcAutoGlobalDialog(tk.Toplevel):
    """Applique des % de marge à TOUS les produits en un clic."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Calcul automatique — Tous les produits")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        center_window(self, 420, 360)

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=25, pady=20)
        f.pack(fill="both", expand=True)

        lbl(f, "📋 CALCUL AUTO — TOUS LES PRODUITS", 12, True, CLR_ACCENT
            ).pack(pady=(0, 8))

        tk.Label(f,
                 text="Les prix seront calculés à partir du Prix d'Achat\n"
                      "de chaque produit selon les marges saisies ci-dessous.",
                 bg=CLR_BG, fg=CLR_MUTED,
                 font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(0, 12))

        CHAMPS = [
            ("Super Gros (%)", "sg",  "10", CLR_ACCENT),
            ("Gros (%)",       "g",   "20", CLR_GREEN),
            ("Détail (%)",     "d",   "35", CLR_ORANGE),
            ("Spécial (%)",    "sp",  "15", CLR_RED),
        ]
        self.pct_vars = {}
        for lt, key, dflt, clr in CHAMPS:
            row = tk.Frame(f, bg=CLR_BG)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=lt, bg=CLR_BG, fg=clr,
                     font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
            v = tk.StringVar(value=dflt)
            tk.Entry(row, textvariable=v, width=10,
                     bg=CLR_INPUT, fg=CLR_TEXT, relief="flat",
                     font=("Segoe UI", 10, "bold"),
                     justify="right").pack(side="left", padx=8)
            self.pct_vars[key] = v

        # Option : écraser seulement si 0
        self.only_zero = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Écraser uniquement les prix à 0",
                       variable=self.only_zero,
                       bg=CLR_BG, fg=CLR_MUTED,
                       selectcolor=CLR_INPUT,
                       font=("Segoe UI", 8)).pack(anchor="w", pady=8)

        bf = tk.Frame(f, bg=CLR_BG)
        bf.pack(pady=8)
        tk.Button(bf, text="✅ Appliquer à tous",
                  command=self.appliquer,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=20, pady=8,
                  cursor="hand2").pack(side="left", padx=8)
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                  padx=12, pady=8, cursor="hand2").pack(side="left", padx=8)

    def appliquer(self):
        try:
            sg = float(self.pct_vars["sg"].get() or 0)
            g  = float(self.pct_vars["g"].get()  or 0)
            d  = float(self.pct_vars["d"].get()  or 0)
            sp = float(self.pct_vars["sp"].get() or 0)
        except ValueError:
            messagebox.showerror("Erreur", "Saisir des nombres valides")
            return

        only_zero = self.only_zero.get()

        conn = get_conn()
        try:
            produits = conn.execute(
                "SELECT id, prix_achat, prix_super_gros, prix_gros, prix_detail, prix_special "
                "FROM produits WHERE actif=1"
            ).fetchall()

            updated = 0
            for p in produits:
                pa = p["prix_achat"] or 0.0
                if pa <= 0:
                    continue

                new_sg = pa * (1 + sg / 100)
                new_g  = pa * (1 + g  / 100)
                new_d  = pa * (1 + d  / 100)
                new_sp = pa * (1 + sp / 100)

                if only_zero:
                    # N'écraser que si la valeur actuelle est 0 ou None
                    update_sg = new_sg if not (p["prix_super_gros"] or 0) else p["prix_super_gros"]
                    update_g  = new_g  if not (p["prix_gros"]       or 0) else p["prix_gros"]
                    update_d  = new_d  if not (p["prix_detail"]      or 0) else p["prix_detail"]
                    update_sp = new_sp if not (p["prix_special"]     or 0) else p["prix_special"]
                else:
                    update_sg, update_g, update_d, update_sp = new_sg, new_g, new_d, new_sp

                conn.execute("""
                    UPDATE produits
                    SET prix_super_gros = ?,
                        prix_gros       = ?,
                        prix_detail     = ?,
                        prix_special    = ?,
                        prix_vente      = ?
                    WHERE id = ?
                """, (update_sg, update_g, update_d, update_sp, update_d, p["id"]))
                updated += 1

            conn.commit()
            messagebox.showinfo("Succès", f"{updated} produits mis à jour ✅")
            self.destroy()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex))
        finally:
            conn.close()


# ── Dialogue niveaux de prix par client ──────────────────────────────────────

class NiveauxClientsDialog(tk.Toplevel):
    """Assigne un niveau de prix par défaut à chaque client."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Niveaux de prix par client")
        self.configure(bg=CLR_BG)
        self.geometry("700x500")
        self.grab_set()
        self._build()
        self.refresh()
        center_window(self, 700, 500)

    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(15, 8))
        lbl(hdr, "👥  Niveau de prix par défaut — Clients", 13, True).pack(side="left")
        tk.Button(hdr, text="💾 Enregistrer",
                  command=self.sauvegarder,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14, pady=6,
                  cursor="hand2").pack(side="right")

        tk.Label(self,
                 text="Ce niveau sera sélectionné automatiquement lors d'une vente pour ce client.",
                 bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 8)).pack(padx=20, anchor="w")

        cols = ["Client", "Code", "Niveau de prix actuel"]
        widths = [250, 100, 180]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=10)

        lbl(bf, "Changer le niveau sélectionné :", color=CLR_MUTED).pack(side="left")
        self.niveau_var = tk.StringVar(value="detail")
        cb = ttk.Combobox(bf, textvariable=self.niveau_var,
                          values=["super_gros", "gros", "detail", "special"],
                          width=14, state="readonly")
        cb.pack(side="left", padx=8)
        tk.Button(bf, text="✅ Appliquer",
                  command=self.appliquer_niveau,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=6)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        clients = conn.execute("""
            SELECT c.id, c.nom, c.code,
                   COALESCE(cnp.niveau, 'detail') as niveau
            FROM clients c
            LEFT JOIN clients_niveau_prix cnp ON cnp.client_id = c.id
            ORDER BY c.nom
        """).fetchall()
        conn.close()
        for c in clients:
            self.tree.insert("", "end", iid=c["id"], values=(
                c["nom"], c["code"], c["niveau"]
            ))

    def appliquer_niveau(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un ou plusieurs clients")
            return
        niveau = self.niveau_var.get()
        for iid in sel:
            self.tree.set(iid, "Niveau de prix actuel", niveau)

    def sauvegarder(self):
        conn = get_conn()
        try:
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, "values")
                niveau = vals[2]
                conn.execute("""
                    INSERT INTO clients_niveau_prix(client_id, niveau)
                    VALUES(?,?)
                    ON CONFLICT(client_id) DO UPDATE SET niveau=excluded.niveau
                """, (int(iid), niveau))
            conn.commit()
            messagebox.showinfo("Succès", "Niveaux enregistrés ✅")
            self.destroy()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex))
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  PATCH : BonDialog._on_prod_change — injecter le prix selon niveau
# ══════════════════════════════════════════════════════════════════════════════

def patch_bon_dialog_prod_change(bon_dialog_instance, niveau="detail"):
    """
    À appeler dans BonDialog.__init__ pour activer les prix multi-niveaux.

    Dans BonDialog._build(), après la création du combo produit, ajouter :

        if hasattr(self, 'prix_selector'):
            self.prix_selector.set_produit(prod)

    Et dans _on_prod_change :

        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            ...
            # REMPLACER la ligne px = p["prix_achat"] if ... else p["prix_vente"]
            # PAR :
            if hasattr(self, 'prix_selector'):
                self.prix_selector.set_produit(p)
            else:
                px = p.get("prix_detail") or p.get("prix_vente", 0)
                self.prix_var.set(str(px))
    """
    pass  # Documentation uniquement


# ══════════════════════════════════════════════════════════════════════════════
#  RÉSUMÉ DES MODIFICATIONS À FAIRE DANS LE FICHIER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
"""
1. Dans App.__init__(), après init_db() :
   ─────────────────────────────────────
   from prix_niveaux import migrer_prix_niveaux, GrillePrixPage
   migrer_prix_niveaux()

2. Dans App._build(), nav_items, ajouter :
   ─────────────────────────────────────────
   ("💲", "Grille des Prix", "grille_prix"),

3. Dans App.show_page(), ajouter :
   ──────────────────────────────────
   elif key == "grille_prix":
       self._pages[key] = GrillePrixPage(self.main)

4. Dans ProduitDialog._build(), remplacer le champ "Prix Vente" :
   ──────────────────────────────────────────────────────────────
   # Supprimer la ligne :
   #   ("Prix Vente", "prix_vente", False),
   # Et après la boucle des fields, ajouter :
   from prix_niveaux import PrixNiveauxFrame
   pnf = PrixNiveauxFrame(f, self.vars, self.data)
   pnf.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=8)

5. Dans ProduitDialog.save(), ajouter les nouvelles colonnes :
   ──────────────────────────────────────────────────────────
   prix_sg = parse_decimal(v.get("prix_super_gros", "0") or "0")
   prix_g  = parse_decimal(v.get("prix_gros",       "0") or "0")
   prix_d  = parse_decimal(v.get("prix_detail",     "0") or "0")
   prix_sp = parse_decimal(v.get("prix_special",    "0") or "0")
   # Utiliser prix_d comme prix_vente par défaut
   # Ajouter dans le UPDATE/INSERT : prix_super_gros=?, prix_gros=?,
   #   prix_detail=?, prix_special=?, prix_vente=prix_d

6. Dans BonDialog._on_prod_change, remplacer :
   ─────────────────────────────────────────────
   # px = p["prix_achat"] if self.bon_type == "achat" else p["prix_vente"]
   # PAR :
   if self.bon_type == "achat":
       px = p.get("prix_achat", 0)
   else:
       px = p.get("prix_detail") or p.get("prix_vente", 0)
   self.prix_var.set(str(px))

7. Dans VenteComptoirDialog._build(), après le combo produit,
   ajouter le PrixSelectorWidget :
   ──────────────────────────────────────────────────────────
   from prix_niveaux import PrixSelectorWidget
   self.prix_selector = PrixSelectorWidget(
       left_panel,
       prix_var     = self.prix_var,
       client_id_fn = lambda: self.clients_map.get(self.client_nom.get())
   )
   self.prix_selector.pack(fill="x", pady=5)

   Et dans on_produit_selectionne() :
   self.prix_selector.set_produit(self.prod_map[key])
"""
