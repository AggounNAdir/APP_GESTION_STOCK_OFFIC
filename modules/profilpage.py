"""
Page Profil Utilisateur — Paramètres de l'application et sélection du thème.
Permet de changer le thème et redémarre l'application pour appliquer les changements.
"""
import tkinter as tk
from tkinter import messagebox
import sys
import os
import subprocess

from modules.core import *
from modules.theme import THEMES, THEME_KEYS, save_theme, get_current_theme_name


class ProfilPage(tk.Frame):
    """Page de profil utilisateur avec paramètres d'application et sélection de thème"""

    def __init__(self, parent, app=None):
        self.app = app
        super().__init__(parent, bg=CLR_BG)
        self._build()

    def _build(self):
        # ── En-tête ──
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=30, pady=(25, 10))
        lbl(hdr, "👤 Mon Profil & Paramètres", 18, True).pack(side="left")

        # ── Contenu scrollable ──
        canvas = tk.Canvas(self, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=CLR_BG)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)
