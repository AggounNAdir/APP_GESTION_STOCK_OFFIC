from modules.core import *

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