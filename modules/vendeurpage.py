import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from config import DB_PATH

class VendeurPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titre
        tk.Label(self, text="Gestion des Vendeurs", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Formulaire
        form_frame = tk.LabelFrame(self, text="Nouveau / Modification")
        form_frame.pack(fill="x", pady=5)
        
        tk.Label(form_frame, text="Code:").grid(row=0, column=0, padx=5, pady=5)
        self.ent_code = tk.Entry(form_frame)
        self.ent_code.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Nom:").grid(row=0, column=2, padx=5, pady=5)
        self.ent_nom = tk.Entry(form_frame)
        self.ent_nom.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(form_frame, text="Téléphone:").grid(row=0, column=4, padx=5, pady=5)
        self.ent_tel = tk.Entry(form_frame)
        self.ent_tel.grid(row=0, column=5, padx=5, pady=5)
        
        tk.Button(form_frame, text="Enregistrer", command=self.save_vendeur).grid(row=0, column=6, padx=10)

        # Liste
        self.tree = ttk.Treeview(self, columns=("id", "code", "nom", "tel", "actif"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Code")
        self.tree.heading("nom", text="Nom")
        self.tree.heading("tel", text="Téléphone")
        self.tree.heading("actif", text="Actif")
        self.tree.column("id", width=50)
        self.tree.pack(fill="both", expand=True, pady=10)
        
        self.refresh_list()

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = sqlite3.connect(DB_PATH)
        for row in conn.execute("SELECT * FROM vendeurs").fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def save_vendeur(self):
        code = self.ent_code.get()
        nom = self.ent_nom.get()
        tel = self.ent_tel.get()
        
        if not code or not nom:
            messagebox.showwarning("Erreur", "Code et Nom obligatoires")
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO vendeurs (code, nom, tel) VALUES (?, ?, ?)", (code, nom, tel))
            conn.commit()
            conn.close()
            self.refresh_list()
            self.ent_code.delete(0, tk.END)
            self.ent_nom.delete(0, tk.END)
            self.ent_tel.delete(0, tk.END)
            messagebox.showinfo("Succès", "Vendeur ajouté")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Le code vendeur existe déjà")

