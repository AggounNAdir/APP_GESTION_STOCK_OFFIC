"""
Point d'entrée principal de l'application modulaire Gestion de Stock.
"""

import tkinter as tk
from tkinter import messagebox
from config import CLR_BG, CLR_TEXT, CLR_ACCENT, CLR_SIDEBAR, CLR_CARD
from database import init_db, get_conn
from utils import center_window

class ApplicationGestionStock(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application de Gestion de Stock (Modulaire)")
        self.geometry("1200x750")
        self.configure(bg=CLR_BG)
        center_window(self, 1200, 750)
        
        # Initialiser la base de données
        init_db()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Barre latérale (Sidebar)
        sidebar = tk.Frame(self, bg=CLR_SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        tk.Label(
            sidebar, text="📦 GESTION STOCK", bg=CLR_SIDEBAR, fg="white",
            font=("Segoe UI", 13, "bold")
        ).pack(pady=20)
        
        # Contenu principal
        self.main_content = tk.Frame(self, bg=CLR_BG)
        self.main_content.pack(side="right", fill="both", expand=True)
        
        # Accueil / Tableau de bord par défaut
        welcome_frame = tk.Frame(self.main_content, bg=CLR_CARD)
        welcome_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        tk.Label(
            welcome_frame, text="Bienvenue dans votre Gestion de Stock Modulaire",
            bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 18, "bold")
        ).pack(pady=20)
        
        tk.Label(
            welcome_frame, text="Architecture modulaire activée avec succès.\n"
                                "Base de données SQLite connectée et opérationnelle.",
            bg=CLR_CARD, fg="#94a3b8", font=("Segoe UI", 11)
        ).pack(pady=10)
        
        tk.Button(
            welcome_frame, text="🔄 Actualiser les statistiques", command=self.refresh_stats,
            bg=CLR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=15, pady=8, cursor="hand2"
        ).pack(pady=20)
        
        self.stats_label = tk.Label(
            welcome_frame, text="", bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 11)
        )
        self.stats_label.pack(pady=10)
        self.refresh_stats()

    def refresh_stats(self):
        try:
            conn = get_conn()
            nb_produits = conn.execute("SELECT COUNT(*) FROM produits WHERE actif=1").fetchone()[0]
            nb_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            nb_ventes = conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0]
            conn.close()
            
            self.stats_label.config(
                text=f"📊 Produits enregistrés : {nb_produits} | "
                     f"👥 Clients : {nb_clients} | "
                     f"🛒 Ventes validées : {nb_ventes}"
            )
        except Exception as e:
            self.stats_label.config(text=f"Erreur de lecture stats : {str(e)}")

if __name__ == "__main__":
    app = ApplicationGestionStock()
    app.mainloop()
