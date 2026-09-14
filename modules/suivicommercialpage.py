import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import date
from config import DB_PATH

class SuiviCommercialPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Filtre Date
        filter_frame = tk.Frame(self)
        filter_frame.pack(fill="x", pady=10)
        
        tk.Label(filter_frame, text="Date :").pack(side="left")
        self.date_entry = tk.Entry(filter_frame)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(side="left", padx=5)
        
        tk.Button(filter_frame, text="Rechercher", command=self.refresh_stats).pack(side="left", padx=5)
        
        # Tableau Stats
        self.tree = ttk.Treeview(self, columns=("nom", "nb_ventes", "ca", "encaisse", "reste"), show="headings")
        self.tree.heading("nom", text="Vendeur")
        self.tree.heading("nb_ventes", text="Nbr Ventes")
        self.tree.heading("ca", text="Chiffre d'Affaires")
        self.tree.heading("encaisse", text="Espèces Encaissées")
        self.tree.heading("reste", text="Crédit Restant")
        self.tree.pack(fill="both", expand=True)
        
        self.refresh_stats()

    def refresh_stats(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        date_jour = self.date_entry.get()
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT v.nom, 
                   COUNT(b.id) as nb_ventes, 
                   SUM(b.total) as ca, 
                   SUM(b.montant_verse) as encaisse,
                   SUM(b.reste_payer) as reste
            FROM vendeurs v
            LEFT JOIN bons_vente b ON v.id = b.vendeur_id AND b.date_bon = ?
            GROUP BY v.id
        """
        for row in conn.execute(query, (date_jour,)).fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

"" 
