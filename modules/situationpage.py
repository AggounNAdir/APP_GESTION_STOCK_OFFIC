from modules.dateentry import DateEntry
from modules.core import *

class SituationPage(tk.Frame):
    """Page de situation des comptes clients/fournisseurs avec filtres"""
    
    def __init__(self, parent, sit_type="client"):
        self.sit_type = sit_type
        self.tiers_table = "clients" if sit_type == "client" else "fournisseurs"
        self.versements_table = "versements_clients" if sit_type == "client" else "versements_fournisseurs"
        self.bons_table = "bons_vente" if sit_type == "client" else "bons_achat"
        self.retours_table = "retours_vente" if sit_type == "client" else "retours_achat"
        self.tiers_label = "Client" if sit_type == "client" else "Fournisseur"
        
        super().__init__(parent, bg=CLR_BG)
        self.current_tiers_id = None
        self.tiers_combo = None
        
        # Variables pour les filtres
        self.date_debut_var = tk.StringVar(value=date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.type_filter_var = tk.StringVar(value="Tous")
        
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(10,2))
        title = f"📊 Situation des {self.tiers_label}s"
        lbl(hdr, title, 16, True).pack(side="left")
        
        # Sélection du tiers
        select_frame = tk.Frame(self, bg=CLR_BG)
        select_frame.pack(fill="x", padx=20, pady=5)
        
        lbl(select_frame, f"Sélectionner un {self.tiers_label}:", 10, True, CLR_MUTED).pack(side="left", padx=5)
        
        self.load_tiers_list()
        self.tiers_var = tk.StringVar()
        self.tiers_combo = combo(select_frame, self.tiers_list, width=30, textvariable=self.tiers_var)
        self.tiers_combo.pack(side="left", padx=10)
        self.tiers_combo.bind("<<ComboboxSelected>>", self.on_tiers_selected)
        
        tk.Button(select_frame, text="Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=10)
        
        # ========== SECTION FILTRES ==========
        filter_frame = tk.LabelFrame(self, text="🔍 Filtres", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=2)
        filter_frame.pack(fill="x", padx=20, pady=2)
        
        # Ligne 1: Période avec calendrier
        row1 = tk.Frame(filter_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        
        # ✅ CORRECTION : Instancier DateEntry correctement
        date_debut_entry = DateEntry(row1, self.date_debut_var, label_text="📅 Du:", width=12)
        date_debut_entry.pack(side="left", padx=5)
        
        lbl(row1, "Au:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        date_fin_entry = DateEntry(row1, self.date_fin_var, width=12)
        date_fin_entry.pack(side="left", padx=5)
        
        # Bouton appliquer les filtres
        tk.Button(row1, text="📊 Appliquer", command=self.apply_filters,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=20)
        
        # Bouton réinitialiser
        tk.Button(row1, text="🔄 Réinitialiser", command=self.reset_filters,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        # Ligne 2: Type de transaction
        row2 = tk.Frame(filter_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=5)
        
        lbl(row2, "📌 Type:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        if self.sit_type == "client":
            types = ["Tous", "VENTE", "RETOUR", "VERSEMENT"]
        else:
            types = ["Tous", "ACHAT", "RETOUR", "VERSEMENT"]
        
        type_combo = combo(row2, types, width=15, textvariable=self.type_filter_var)
        type_combo.pack(side="left", padx=5)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Ligne 3: Boutons d'export
        row3 = tk.Frame(filter_frame, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        
        tk.Button(row3, text="📥 Exporter CSV", command=self.export_filtered_csv,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(row3, text="📄 Exporter HTML", command=self.export_filtered_html,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(row3, text="🖨 Imprimer", command=self.print_filtered,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=4, cursor="hand2").pack(side="left", padx=5)
        
        # Notebook pour les onglets
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=2)
        
        # Onglet Synthèse
        self.synthese_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.synthese_frame, text="📈 Synthèse")
        
        # Onglet Historique
        self.histo_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.histo_frame, text="📜 Historique transactions")
        
        # Onglet Versements
        self.versements_frame = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.versements_frame, text="💳 Versements")
        
        self._build_synthese()
        self._build_historique()
        self._build_versements()
    
    def load_tiers_list(self):
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.tiers_table} ORDER BY nom").fetchall()
        conn.close()
        self.tiers_list = [f"{t['nom']} (Solde: {t['solde']:,.2f} DA)" for t in tiers]
        self.tiers_data = {f"{t['nom']} (Solde: {t['solde']:,.2f} DA)": {"id": t["id"], "nom": t["nom"], "solde": t["solde"]} 
                          for t in tiers}
    
    def on_tiers_selected(self, event=None):
        key = self.tiers_var.get()
        if key and key in self.tiers_data:
            self.current_tiers_id = self.tiers_data[key]["id"]
            self.current_tiers_nom = self.tiers_data[key]["nom"]
            self.refresh_situation()
    def modifier_observation_avoir(self):
        """Modifier l'observation d'un avoir (AVOIR-C ou AVOIR-F)"""
        # Récupérer la sélection dans l'historique
        sel = self.histo_tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne dans l'historique")
            return
        
        # Récupérer les valeurs de la ligne sélectionnée
        values = self.histo_tree.item(sel[0])["values"]
        if len(values) < 3:
            messagebox.showwarning("Avertissement", "Ligne invalide")
            return
        
        type_transaction = values[1]  # Type (AVOIR, SOLDE INITIAL, etc.)
        document = values[2]          # Document (numéro ou observation)
        
        # Vérifier que c'est bien un AVOIR ou SOLDE INITIAL
        if type_transaction not in ["AVOIR", "SOLDE INITIAL"]:
            messagebox.showwarning("Avertissement", 
                "Cette fonction n'est disponible que pour les AVOIR et SOLDE INITIAL")
            return
        
        # Récupérer le numéro du document (si c'est une observation, il faut retrouver le bon)
        conn = get_conn()
        
        # Chercher le bon correspondant
        if self.sit_type == "client":
            # Chercher dans les bons de vente
            bon = conn.execute("""
                SELECT id, numero, observations 
                FROM bons_vente 
                WHERE client_id=? AND (numero LIKE 'AVOIR-C-%' OR numero LIKE 'SI-C-%')
                AND (numero = ? OR observations = ?)
                ORDER BY date_bon DESC
            """, (self.current_tiers_id, document, document)).fetchone()
        else:
            # Chercher dans les bons d'achat
            bon = conn.execute("""
                SELECT id, numero, observations 
                FROM bons_achat 
                WHERE fournisseur_id=? AND (numero LIKE 'AVOIR-F-%' OR numero LIKE 'SI-F-%')
                AND (numero = ? OR observations = ?)
                ORDER BY date_bon DESC
            """, (self.current_tiers_id, document, document)).fetchone()
        
        conn.close()
        
        if not bon:
            messagebox.showwarning("Avertissement", "Document non trouvé")
            return
        
        # Demander la nouvelle observation
        nouvelle_obs = simpledialog.askstring(
            "Modifier l'observation",
            f"Document: {bon['numero']}\n"
            f"Observation actuelle: {bon['observations'] or '(vide)'}\n\n"
            f"Nouvelle observation:",
            initialvalue=bon['observations'] or "",
            parent=self
        )
        
        if nouvelle_obs is None:
            return  # L'utilisateur a annulé
        
        # Mettre à jour dans la base de données
        conn = get_conn()
        try:
            if self.sit_type == "client":
                conn.execute(
                    "UPDATE bons_vente SET observations = ? WHERE id = ?",
                    (nouvelle_obs.strip(), bon["id"])
                )
            else:
                conn.execute(
                    "UPDATE bons_achat SET observations = ? WHERE id = ?",
                    (nouvelle_obs.strip(), bon["id"])
                )
            conn.commit()
            messagebox.showinfo("Succès", "✅ Observation mise à jour avec succès")
            self.refresh_situation()  # Rafraîchir l'affichage
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour: {str(e)}")
        finally:
            conn.close()
    def refresh(self):
        self.load_tiers_list()
        if self.tiers_combo:
            self.tiers_combo['values'] = self.tiers_list

        if self.current_tiers_id is not None:
            nouvelle_cle = next(
                (k for k, v in self.tiers_data.items() if v["id"] == self.current_tiers_id),
                None
            )
            if nouvelle_cle:
                self.tiers_var.set(nouvelle_cle)
                self.refresh_situation()
            elif self.tiers_list:
                self.tiers_var.set(self.tiers_list[0])
                self.on_tiers_selected()
        elif self.tiers_list:
            self.tiers_var.set(self.tiers_list[0])
            self.on_tiers_selected()
    
    def apply_filters(self):
        """Appliquer les filtres et rafraîchir l'affichage"""
        if self.current_tiers_id:
            self.refresh_situation()
    
    def reset_filters(self):
        """Réinitialiser les filtres"""
        self.date_debut_var.set(date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.date_fin_var.set(date.today().strftime("%Y-%m-%d"))
        self.type_filter_var.set("Tous")
        self.apply_filters()
    
    def _build_synthese(self):
        """Construit l'interface de synthèse avec des widgets modernes"""
        main_frame = tk.Frame(self.synthese_frame, bg=CLR_BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=2)
        
        # Carte d'identité du client
        card_info = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
        card_info.pack(fill="x", pady=(0, 15))
        
        header_frame = tk.Frame(card_info, bg=CLR_CARD)
        header_frame.pack(fill="x", pady=(0, 10))
        lbl(header_frame, "INFORMATIONS", 11, True, CLR_ACCENT).pack(side="left")
        
        separator = tk.Frame(header_frame, bg=CLR_BORDER, height=2)
        separator.pack(fill="x", pady=5)
        
        self.info_frame = tk.Frame(card_info, bg=CLR_CARD)
        self.info_frame.pack(fill="x")
        
        # Indicateurs de performance
        kpi_frame = tk.Frame(main_frame, bg=CLR_BG)
        kpi_frame.pack(fill="x", pady=(0, 15))
        
        self.kpi_cards = {}
        if self.sit_type == "client":
            kpi_titles = ["Total Ventes HT", "Total Retours", "Total Versements", "Solde"]
        else:
            kpi_titles = ["Total Achats TTC", "Total Retours", "Total Versements", "Solde"]
        colors = [CLR_ACCENT, CLR_ORANGE, CLR_RED, CLR_GREEN]
        
        for i, (title, color) in enumerate(zip(kpi_titles, colors)):
            card = tk.Frame(kpi_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
            card.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            kpi_frame.grid_columnconfigure(i, weight=1)
            
            lbl(card, title, 9, color=CLR_MUTED).pack(anchor="w")
            
            var_name = f"kpi_var_{i}"
            setattr(self, var_name, tk.StringVar(value="0 DA"))
            label = tk.Label(card, textvariable=getattr(self, var_name), 
                            bg=CLR_CARD, fg=color, font=("Segoe UI", 16, "bold"))
            label.pack(anchor="w", pady=(5, 0))
            self.kpi_cards[f"title_{i}"] = label
        
        # Cadre des soldes
        solde_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15, relief="flat")
        solde_frame.pack(fill="x", pady=(0, 15))

        lbl(solde_frame, "SITUATION FINANCIÈRE", 11, True, CLR_ACCENT).pack(anchor="w")
        tk.Frame(solde_frame, bg=CLR_BORDER, height=2).pack(fill="x", pady=5)

        soldes_grid = tk.Frame(solde_frame, bg=CLR_CARD)
        soldes_grid.pack(fill="x", pady=10)

        # Configurer les colonnes pour qu'elles s'étendent également
        soldes_grid.grid_columnconfigure(0, weight=1)  # 1ère paire
        soldes_grid.grid_columnconfigure(1, weight=1)  # 2ème paire
        soldes_grid.grid_columnconfigure(2, weight=1)  # 3ème paire

        # 1ère paire - Solde calculé
        lbl(soldes_grid, "Solde calculé:", 10, True, CLR_MUTED).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.solde_calcule_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.solde_calcule_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="e", padx=10, pady=5)

        # 2ème paire - Solde enregistré
        lbl(soldes_grid, "Solde enregistré:", 10, True, CLR_MUTED).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self.solde_enregistre_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.solde_enregistre_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="e", padx=10, pady=5)

        # 3ème paire - Écart
        lbl(soldes_grid, "Écart:", 10, True, CLR_MUTED).grid(row=0, column=2, sticky="w", padx=10, pady=5)
        self.ecart_var = tk.StringVar(value="0.00 DA")
        tk.Label(soldes_grid, textvariable=self.ecart_var, bg=CLR_CARD, 
                fg=CLR_RED, font=("Segoe UI", 11, "bold")).grid(row=0, column=2, sticky="e", padx=10, pady=5)
        
        # Indicateur de statut
        self.status_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=0, pady=0, relief="flat")
        self.status_frame.pack(fill="x", pady=(5, 5))
        self.status_label = tk.Label(self.status_frame, text="", font=("Segoe UI", 10, "bold"), 
                                    bg=CLR_CARD, fg=CLR_TEXT, wraplength=800, pady=10)
        self.status_label.pack(fill="x", expand=True)
    
    def _build_historique(self):
        histo_frame = tk.Frame(self.histo_frame, bg=CLR_BG)
        histo_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = ["Date", "Type", "Document", "Montant", "Solde après"]
        widths = [100, 100, 120, 120, 120]
        tf, self.histo_tree = make_tree(histo_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        self.histo_tree.bind("<Double-1>", lambda e: self.modifier_observation_avoir())

    
    def _build_versements(self):
        vers_frame = tk.Frame(self.versements_frame, bg=CLR_BG)
        vers_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = ["Date", "Numéro", "Montant", "Mode", "Référence"]
        widths = [100, 120, 120, 100, 150]
        tf, self.vers_tree = make_tree(vers_frame, cols, widths)
        tf.pack(fill="both", expand=True)
    
    def get_filtered_transactions(self):
        """Récupère les transactions filtrées par date et type"""
        if not self.current_tiers_id:
            return [], 0, 0, 0
        
        conn = get_conn()
        
        # Récupérer les dates
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        type_filter = self.type_filter_var.get()
        
        transactions = []
        
        # Construire la clause WHERE pour les dates
        date_condition = ""
        if date_debut and date_fin:
            date_condition = f"AND date BETWEEN '{date_debut}' AND '{date_fin}'"
        
        # 1. Bons (Ventes ou Achats)
        if self.sit_type == "client":
            # ✅ Clients
            bons = conn.execute(f"""
                SELECT date_bon as date, 
                    CASE 
                        WHEN numero LIKE 'SI-C-%' THEN 'SOLDE INITIAL'
                        WHEN numero LIKE 'AVOIR-%' THEN 'AVOIR'
                        ELSE 'VENTE' 
                    END as type,
                    CASE 
                        WHEN numero LIKE 'SI-C-%' OR numero LIKE 'AVOIR-%' 
                        THEN COALESCE(observations, numero)
                        ELSE numero 
                    END as document,
                    total as montant,
                    observations as motif,
                    '' as mode, '' as reference
                FROM {self.bons_table}
                WHERE client_id=? AND statut='Validé'
                {date_condition}
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        else:
            # ✅ Fournisseurs
            bons = conn.execute(f"""
                SELECT date_bon as date, 
                    CASE 
                        WHEN numero LIKE 'SI-F-%' THEN 'SOLDE INITIAL'
                        WHEN numero LIKE 'AVOIR-%' THEN 'AVOIR'
                        ELSE 'ACHAT' 
                    END as type,
                    CASE 
                        WHEN numero LIKE 'SI-F-%' OR numero LIKE 'AVOIR-%' 
                        THEN COALESCE(observations, numero)  -- ✅ Afficher observations ou le numéro par défaut
                        ELSE numero 
                    END as document,
                    total as montant,
                    observations as motif,
                    '' as mode, '' as reference
                FROM {self.bons_table}
                WHERE fournisseur_id=? AND statut='Validé'
                {date_condition}
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        
        # ✅ Convertir les bons en dictionnaires
        for b in bons:
            transactions.append(dict(b))
        
        # 2. Retours
        if self.sit_type == "client":
            retours = conn.execute(f"""
                SELECT date_retour as date, 'RETOUR' as type, numero as document, -total as montant,
                    motif, '' as mode, '' as reference
                FROM {self.retours_table}
                WHERE client_id=?
                {date_condition}
                ORDER BY date_retour
            """, (self.current_tiers_id,)).fetchall()
        else:
            retours = conn.execute(f"""
                SELECT date_retour as date, 'RETOUR' as type, numero as document, -total as montant,
                    motif, '' as mode, '' as reference
                FROM {self.retours_table}
                WHERE fournisseur_id=?
                {date_condition}
                ORDER BY date_retour
            """, (self.current_tiers_id,)).fetchall()
        
        for r in retours:
            transactions.append(dict(r))
        
        # 3. Versements
        if self.sit_type == "client":
            versements = conn.execute(f"""
                SELECT date_vers as date, 'VERSEMENT' as type, numero as document, -montant as montant,
                    '' as motif, mode, reference
                FROM {self.versements_table}
                WHERE client_id=?
                {date_condition}
                ORDER BY date_vers
            """, (self.current_tiers_id,)).fetchall()
        else:
            versements = conn.execute(f"""
                SELECT date_vers as date, 'VERSEMENT' as type, numero as document, -montant as montant,
                    '' as motif, mode, reference
                FROM {self.versements_table}
                WHERE fournisseur_id=?
                {date_condition}
                ORDER BY date_vers
            """, (self.current_tiers_id,)).fetchall()
        
        for v in versements:
            transactions.append(dict(v))
        
        conn.close()
        
        # Filtrer par type
        if type_filter != "Tous":
            transactions = [t for t in transactions if t["type"] == type_filter]
        
        # Trier par date
        transactions.sort(key=lambda x: x["date"])
        
        # Calculer les totaux
        total_operations = 0
        total_retours = 0
        total_versements = 0
        
        for t in transactions:
            if t["type"] in ("VENTE", "ACHAT", "AVOIR", "REMBOURSEMENT"):
                total_operations += t["montant"]
            elif t["type"] == "RETOUR":
                total_retours += abs(t["montant"])
            elif t["type"] == "VERSEMENT":
                total_versements += abs(t["montant"])
        
        return transactions, total_operations, total_retours, total_versements

    def refresh_situation(self):
        if not self.current_tiers_id:
            return

        conn = get_conn()
        tiers = conn.execute(
            f"SELECT * FROM {self.tiers_table} WHERE id=?",
            (self.current_tiers_id,)
        ).fetchone()

        # ✅ RÉCUPÉRER LES SOLDES INITIAUX POUR LES KPI (TOTAL GLOBAL UNIQUEMENT)
        if self.sit_type == "client":
            total_si_global = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
            """, (self.current_tiers_id,)).fetchone()[0]
            
            total_ventes_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM bons_vente "
                "WHERE client_id=? AND statut='Validé' AND numero NOT LIKE 'SI-C-%'",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_retours_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM retours_vente "
                "WHERE client_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_versements_global = conn.execute(
                "SELECT COALESCE(SUM(montant),0) FROM versements_clients "
                "WHERE client_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
        else:
            total_si_global = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
            """, (self.current_tiers_id,)).fetchone()[0]
            
            total_ventes_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM bons_achat "
                "WHERE fournisseur_id=? AND statut='Validé' AND numero NOT LIKE 'SI-F-%'",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_retours_global = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM retours_achat "
                "WHERE fournisseur_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]
            
            total_versements_global = conn.execute(
                "SELECT COALESCE(SUM(montant),0) FROM versements_fournisseurs "
                "WHERE fournisseur_id=?",
                (self.current_tiers_id,)
            ).fetchone()[0]

        # ✅ Solde calculé GLOBAL (tout l'historique)
        solde_calcule_global = (
            total_ventes_global 
            + total_si_global
            - total_retours_global 
            - total_versements_global
        )

        # ✅ Mettre à jour les labels de solde
        self.solde_calcule_var.set(f"{solde_calcule_global:,.2f} DA")
        self.solde_enregistre_var.set(f"{tiers['solde']:,.2f} DA")

        ecart = abs(solde_calcule_global - tiers["solde"])
        if ecart > 0.01:
            self.ecart_var.set(f"⚠️ {ecart:,.2f} DA")
            self.status_label.config(
                text="⚠️ ATTENTION : Écart détecté entre le solde calculé et enregistré !",
                fg="#FFFFFF",
                bg=CLR_RED
            )
            self.status_frame.config(bg=CLR_RED)
        else:
            self.ecart_var.set(f"✅ {ecart:,.2f} DA")
            self.status_label.config(
                text="✅ Compte équilibré - Tout est en ordre",
                fg="#FFFFFF",
                bg=CLR_GREEN
            )
            self.status_frame.config(bg=CLR_GREEN)

        # ✅ RÉCUPÉRER LES TRANSACTIONS FILTRÉES (ELLES INCLUENT DÉJÀ LES SOLDES INITIAUX)
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ RÉCUPÉRER LE TOTAL DES SOLDES INITIAUX DANS LA PÉRIODE (pour les KPI uniquement)
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        conn2 = get_conn()
        if self.sit_type == "client":
            total_si_periode = conn2.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        else:
            total_si_periode = conn2.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        conn2.close()

        # ✅ Mettre à jour les KPI
        if hasattr(self, 'kpi_var_0'):
            self.kpi_var_0.set(f"{total_ops:,.2f} DA")
            self.kpi_var_1.set(f"{total_ret:,.2f} DA")
        if hasattr(self, 'kpi_var_2'):
            self.kpi_var_2.set(f"{total_vers:,.2f} DA")
        if hasattr(self, 'kpi_var_3'):
            solde_periode = total_si_periode + total_ops - total_ret - total_vers
            self.kpi_var_3.set(f"{solde_periode:,.2f} DA")

        # ========== HISTORIQUE (UNIQUEMENT AVEC transactions) ==========
        self.histo_tree.delete(*self.histo_tree.get_children())

        # ✅ Utiliser directement les transactions (elles contiennent déjà TOUS les soldes initiaux)
        all_transactions = transactions.copy()

        # Trier par date
        all_transactions.sort(key=lambda x: x["date"])

        # ✅ Calculer le solde cumulé
        solde_cumule = 0

        # ✅ Ajouter l'en-tête de période
        period_text = f"Période: {date_debut} → {date_fin}"
        if self.type_filter_var.get() != "Tous":
            period_text += f" | Type: {self.type_filter_var.get()}"

        self.histo_tree.insert("", "end", values=(
            f"📅 {period_text}", "", "", "", ""
        ), tags=("header",))

        # ✅ Afficher les transactions (sans duplication)
        for t in all_transactions:
            solde_cumule += t["montant"]
            
            # ✅ Déterminer le type d'affichage
            if t["type"] == "SOLDE INITIAL":
                type_affichage = "SOLDE INITIAL"
                tag = "solde_initial"
            elif t["type"] == "AVOIR":
                type_affichage = "AVOIR"
                tag = "avoir"
            elif t["type"] == "REMBOURSEMENT":
                type_affichage = "REMBOURSEMENT"
                tag = "remboursement"
            else:
                type_affichage = t["type"]
                if t["type"] in ("VENTE", "ACHAT"):
                    tag = "operation"
                elif t["type"] == "RETOUR":
                    tag = "retour"
                else:  # VERSEMENT
                    tag = "versement"
            
            self.histo_tree.insert("", "end", values=(
                t["date"],
                type_affichage,
                t["document"],
                f"{t['montant']:+,.2f} DA",
                f"{solde_cumule:,.2f} DA"
            ), tags=(tag,))

        # ✅ CONFIGURER LES COULEURS
        self.histo_tree.tag_configure(
            "header", foreground=CLR_ACCENT, font=("Segoe UI", 10, "bold"))
        self.histo_tree.tag_configure(
            "operation", foreground=CLR_ACCENT)
        self.histo_tree.tag_configure(
            "retour", foreground=CLR_ORANGE)
        self.histo_tree.tag_configure(
            "versement", foreground=CLR_GREEN)
        self.histo_tree.tag_configure(
            "solde_initial", foreground=CLR_PURPLE, font=("Segoe UI", 9, "bold"))
        self.histo_tree.tag_configure(
            "avoir", foreground=CLR_ORANGE, font=("Segoe UI", 9, "bold"))
        self.histo_tree.tag_configure(
            "remboursement", foreground=CLR_GREEN, font=("Segoe UI", 9, "bold"))

        # ========== VERSEMENTS (filtrés par date) ==========
        self.vers_tree.delete(*self.vers_tree.get_children())
        conn3 = get_conn()

        if self.sit_type == "client":
            if date_debut and date_fin:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_clients "
                    "WHERE client_id=? AND date_vers BETWEEN ? AND ? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id, date_debut, date_fin)
                ).fetchall()
            else:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_clients WHERE client_id=? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id,)
                ).fetchall()
        else:
            if date_debut and date_fin:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_fournisseurs "
                    "WHERE fournisseur_id=? AND date_vers BETWEEN ? AND ? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id, date_debut, date_fin)
                ).fetchall()
            else:
                vers = conn3.execute(
                    "SELECT date_vers, numero, montant, mode, reference "
                    "FROM versements_fournisseurs WHERE fournisseur_id=? "
                    "ORDER BY date_vers DESC",
                    (self.current_tiers_id,)
                ).fetchall()

        conn3.close()

        for v in vers:
            self.vers_tree.insert("", "end", values=(
                v["date_vers"], v["numero"],
                f"{v['montant']:,.2f} DA",
                v["mode"], v["reference"] or "-"
            ))
            
    def export_filtered_csv(self):
        """Exporter les données filtrées en CSV"""
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ Récupérer les soldes initiaux
        conn = get_conn()
        if self.sit_type == "client":
            soldes_initiaux = conn.execute("""
                SELECT date_bon as date, 'SOLDE INITIAL' as type, 
                    numero as document, total as montant
                FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        else:
            soldes_initiaux = conn.execute("""
                SELECT date_bon as date, 'SOLDE INITIAL' as type, 
                    numero as document, total as montant
                FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                ORDER BY date_bon
            """, (self.current_tiers_id,)).fetchall()
        conn.close()
        
        if not transactions and not soldes_initiaux:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"situation_{self.tiers_label}_{self.current_tiers_nom}.csv"
        )
        
        if filename:
            headers = ["Date", "Type", "Document", "Montant", "Solde Cumulé"]
            data = []
            solde_cumule = 0
            total_si = 0
            
            # ✅ Ajouter les soldes initiaux en premier
            for si in soldes_initiaux:
                solde_cumule += si["montant"]
                total_si += si["montant"]
                data.append([
                    si["date"], 
                    si["type"], 
                    si["document"],
                    f"{si['montant']:+,.2f}",
                    f"{solde_cumule:,.2f}"
                ])
            
            # Ajouter les transactions normales
            for t in transactions:
                solde_cumule += t["montant"]
                data.append([
                    t["date"], 
                    t["type"], 
                    t["document"],
                    f"{t['montant']:+,.2f}",
                    f"{solde_cumule:,.2f}"
                ])
            
            # Ajouter les totaux
            data.append(["", "", "", "", ""])
            if soldes_initiaux:
                data.append(["SOLDE INITIAL", "", "", f"{total_si:+,.2f}", ""])
            data.append(["TOTAL OPERATIONS", "", "", f"{total_ops:+,.2f}", ""])
            data.append(["TOTAL RETOURS", "", "", f"{total_ret:+,.2f}", ""])
            data.append(["TOTAL VERSEMENTS", "", "", f"{total_vers:+,.2f}", ""])
            data.append(["", "", "", "", ""])
            data.append(["SOLDE FINAL", "", "", f"{solde_cumule:,.2f}", ""])
            
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    
    
    def print_filtered(self):
        from modules.core import get_profil_by_type
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        
        # ✅ Récupérer UNIQUEMENT le TOTAL des soldes initiaux pour les KPI
        date_debut = self.date_debut_var.get()
        date_fin = self.date_fin_var.get()
        
        conn = get_conn()
        if self.sit_type == "client":
            total_si = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_vente 
                WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        else:
            total_si = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM bons_achat 
                WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                AND date_bon BETWEEN ? AND ?
            """, (self.current_tiers_id, date_debut, date_fin)).fetchone()[0]
        conn.close()
        
        # ✅ Convertir transactions en dictionnaires (ils contiennent déjà les soldes initiaux)
        transactions_dicts = []
        for t in transactions:
            if hasattr(t, 'keys'):
                transactions_dicts.append(dict(t))
            else:
                transactions_dicts.append(t)
        
        # Trier par date
        transactions_dicts.sort(key=lambda x: x["date"])
        
        if not transactions_dicts:
            from tkinter import messagebox
            messagebox.showwarning("Avertissement", "Aucune donnée à imprimer")
            return
        
        profil = get_profil_by_type("situation")
        
        html = hr.build_situation_html(
            profil      = profil,
            tiers_nom   = self.current_tiers_nom,
            tiers_label = self.tiers_label,
            transactions= transactions_dicts,
            total_ops   = total_ops,
            total_ret   = total_ret,
            total_vers  = total_vers,
            date_debut  = date_debut,
            date_fin    = date_fin,
            total_si    = total_si,
        )
        
        # ✅ AJOUT DES STYLES D'IMPRESSION
        print_styles = """
        <style>
            @media print {
                * {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    box-shadow: none !important;
                    text-shadow: none !important;
                    background-image: none !important;
                    filter: none !important;
                    -webkit-filter: none !important;
                    opacity: 1 !important;
                }
                
                body {
                    background-color: #ffffff !important;
                    margin: 15px !important;
                    font-size: 11pt !important;
                    color: #000000 !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                }
                
                th {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    font-weight: 700 !important;
                    font-size: 11pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    border: 2px solid #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                    text-align: center !important;
                    padding: 8px 12px !important;
                    vertical-align: middle !important;
                    page-break-inside: avoid !important;
                }
                
                td {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border: 1px solid #888888 !important;
                    padding: 6px 10px !important;
                    font-size: 10pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    text-align: center !important;
                }
                
                tr:nth-child(even) td {
                    background-color: #f5f5f5 !important;
                }
                
                .header-section, .header, .bg-primary, .bg-dark {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                }
                
                .header-section h1, .header-section h2, .header-section h3 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                h1, h2, h3, h4, h5 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                table {
                    border-collapse: collapse !important;
                    width: 100% !important;
                    page-break-inside: auto !important;
                }
                
                thead {
                    display: table-header-group !important;
                }
                
                tr {
                    page-break-inside: avoid !important;
                    page-break-after: auto !important;
                }
                
                .total-row td, .grand-total td {
                    font-weight: 700 !important;
                    border-top: 3px solid #000000 !important;
                }
                
                .footer, .footer p, .footer div {
                    color: #000000 !important;
                    border-top: 2px solid #000000 !important;
                    padding-top: 10px !important;
                    margin-top: 15px !important;
                }
            }
        </style>
        """
        
        if '</head>' in html:
            html = html.replace('</head>', print_styles + '</head>')
        else:
            html = html.replace('<body>', print_styles + '<body>')
        
        viewer = hr.DocumentViewer(self)
        viewer.show(html, f"Situation {self.current_tiers_nom}")
 
    def export_filtered_html(self):
        from modules.core import get_profil_by_type
        transactions, total_ops, total_ret, total_vers = self.get_filtered_transactions()
        if not transactions:
            from tkinter import messagebox
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        profil = get_profil_by_type("situation")
        html = hr.build_situation_html(
            profil      = profil,
            tiers_nom   = self.current_tiers_nom,
            tiers_label = self.tiers_label,
            transactions= [dict(t) for t in transactions],
            total_ops   = total_ops,
            total_ret   = total_ret,
            total_vers  = total_vers,
            date_debut  = self.date_debut_var.get(),
            date_fin    = self.date_fin_var.get(),
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_html(html, f"situation_{self.current_tiers_nom}.html")
