from modules.core import *

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

