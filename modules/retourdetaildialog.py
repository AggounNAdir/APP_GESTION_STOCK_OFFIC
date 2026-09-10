from modules.core import *

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


