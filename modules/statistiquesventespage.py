from modules.core import *
from modules.detailventeclientdialog import DetailVenteClientDialog

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

