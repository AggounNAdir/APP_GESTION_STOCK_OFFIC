from modules.core import *

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

