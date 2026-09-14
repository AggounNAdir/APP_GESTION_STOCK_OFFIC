from modules.core import *
from modules.dateentry import DateEntry
from modules.tiersdialog import TiersDialog

class BonDialog(tk.Toplevel):
    def __init__(self, parent, bon_type):
        super().__init__(parent)
        self.bon_type = bon_type
        self.title("Bon d'Achat" if bon_type=="achat" else "Bon de Vente")
        self.configure(bg=CLR_BG)
        
        # Maximiser la fenêtre (prend tout l'écran sauf barre des tâches)
        self.state('zoomed')  # Pour Windows
        
        self.geometry("1000x750")
        self.lignes = []
        # ✅ VARIABLES POUR LA REMISE
        self.total_avant_remise = 0
        self.total_apres_remise = 0
        self.remise_appliquee = False
        self.remise_type = "aucune"
        self.remise_valeur = 0
        self.remise_motif = ""
        self.bind("<<ProduitsModifies>>", lambda e: self.refresh_produits())
        self._build()
        center_window(self, 1000, 750)

    def _build(self):
        # Frame principal avec padding
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # ========== SECTION EN-TÊTE ==========
        header_frame = tk.Frame(main_container, bg=CLR_CARD, padx=15, pady=12, relief="groove", bd=1)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Ligne 1: Numéro et Date
        line1 = tk.Frame(header_frame, bg=CLR_CARD)
        line1.pack(fill="x", pady=5)
        
        lbl(line1, "Numéro:", color=CLR_MUTED).pack(side="left", padx=4)
        prefix = "BA" if self.bon_type=="achat" else "BV"
        self.load_tiers_list()

        # Générer le numéro dès le premier tiers disponible
        if self.tiers_map:
            premier_tiers_id = list(self.tiers_map.values())[0]
            num_initial = next_numero_tiers(prefix, premier_tiers_id)
        else:
            num_initial = f"{prefix}-00000-0001"
        self.num_var = tk.StringVar(value=num_initial)  # sera généré à la validation
        entry(line1, width=18, textvariable=self.num_var).pack(side="left", padx=4)
        
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        DateEntry(line1, self.date_var, label_text="Date:", width=12).pack(side="left", padx=4)
        
        # Ligne 2.5: Vendeur (seulement pour la vente)
        if self.bon_type == "vente":
            line2_5 = tk.Frame(header_frame, bg=CLR_CARD)
            line2_5.pack(fill="x", pady=5)
            lbl(line2_5, "Vendeur:", color=CLR_MUTED).pack(side="left", padx=4)
            self.vendeur_var = tk.StringVar()
            # Charger les vendeurs
            conn = sqlite3.connect(DB_PATH)
            vendeurs = [r['nom'] for r in conn.execute("SELECT nom FROM vendeurs WHERE actif=1").fetchall()]
            conn.close()
            self.vendeur_combo = combo(line2_5, vendeurs, width=35, textvariable=self.vendeur_var)
            self.vendeur_combo.pack(side="left", padx=4)

        # Ligne 2: Fournisseur/Client
        line2 = tk.Frame(header_frame, bg=CLR_CARD)
        line2.pack(fill="x", pady=5)
        
        tiers_label = "Fournisseur:" if self.bon_type=="achat" else "Client:"
        lbl(line2, tiers_label, color=CLR_MUTED).pack(side="left", padx=4)
        
        tiers_frame = tk.Frame(line2, bg=CLR_CARD)
        tiers_frame.pack(side="left", padx=4)
        
        self.load_tiers_list()
        self.tiers_var = tk.StringVar()
        self.tiers_combo = combo(tiers_frame, list(self.tiers_map.keys()), width=35, 
                                  textvariable=self.tiers_var)
        self.tiers_combo.pack(side="left")
        self.tiers_combo.bind("<<ComboboxSelected>>", self.on_tiers_change)
        btn_add_tiers = tk.Button(tiers_frame, text="➕", command=self.ajouter_tiers,
                                  bg=CLR_GREEN, fg="white", relief="flat",
                                  font=("Segoe UI", 10, "bold"), width=3,
                                  padx=5, pady=2, cursor="hand2")
        btn_add_tiers.pack(side="left", padx=5)
        
        if self.tiers_map:
            self.tiers_var.set(list(self.tiers_map.keys())[0])
        
        # Lignes spécifiques aux achats
        if self.bon_type == "achat":
            line3 = tk.Frame(header_frame, bg=CLR_CARD)
            line3.pack(fill="x", pady=5)
            lbl(line3, "📅 Date livraison:", color=CLR_MUTED).pack(side="left", padx=4)
            self.date_livraison_var = tk.StringVar(value="")
            entry(line3, width=14, textvariable=self.date_livraison_var).pack(side="left", padx=4)
            
            line4 = tk.Frame(header_frame, bg=CLR_CARD)
            line4.pack(fill="x", pady=5)
            lbl(line4, "📄 N° Facture Fournisseur:", color=CLR_MUTED).pack(side="left", padx=4)
            self.num_facture_fournisseur_var = tk.StringVar(value="")
            entry(line4, width=20, textvariable=self.num_facture_fournisseur_var).pack(side="left", padx=4)
            
            lbl(line4, "🚚 N° BL Fournisseur:", color=CLR_MUTED).pack(side="left", padx=20)
            self.num_bl_fournisseur_var = tk.StringVar(value="")
            entry(line4, width=20, textvariable=self.num_bl_fournisseur_var).pack(side="left", padx=4)
        
        # ========== SECTION SAISIE PRODUITS (COMPRESSÉE) ==========
        saisie_frame = tk.Frame(main_container, bg=CLR_CARD, padx=10, pady=5, relief="groove", bd=1)
        saisie_frame.pack(fill="x", pady=(0, 10))
        
        prod_frame = tk.Frame(saisie_frame, bg=CLR_CARD)
        prod_frame.pack(fill="x")
        
        # Ligne 1: Produit
        lbl(prod_frame, "🛍️ Produit:", color=CLR_MUTED, size=9, bold=True).grid(row=0, column=0, sticky="w", padx=3, pady=2)
        conn = get_conn()
        prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion, 
                            prix_achat, prix_vente, barcode,
                            prix_detail, prix_gros, prix_super_gros, prix_special,
                            tva  -- ✅ AJOUTER LA TVA ICI
                        FROM produits ORDER BY designation""").fetchall()        
        conn.close()
        self.prod_map = {}
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
        
        self.prod_var = tk.StringVar()
        pcb = combo(prod_frame, list(self.prod_map.keys()), width=35, textvariable=self.prod_var)
        pcb.grid(row=0, column=1, padx=3, columnspan=2)
        btn_refresh = tk.Button(prod_frame, text="🔄", command=self.refresh_produits,
                        bg=CLR_ACCENT, fg="white", relief="flat",
                        font=("Segoe UI", 10, "bold"), padx=6, pady=2,
                        cursor="hand2", width=3)
        btn_refresh.grid(row=0, column=3, padx=2, pady=2)

        self.prod_var.trace_add("write", self._on_prod_change)
        
        # Infos produit sur la même ligne
        lbl(prod_frame, "📦", color=CLR_MUTED).grid(row=0, column=3, padx=(10,2))
        self.unite_label = tk.Label(prod_frame, text="", bg=CLR_CARD, fg=CLR_GREEN, 
                                    font=("Segoe UI", 8, "bold"), width=6)
        self.unite_label.grid(row=0, column=4, padx=2)
        
        lbl(prod_frame, "🔄", color=CLR_MUTED).grid(row=0, column=5, padx=2)
        self.facteur_label = tk.Label(prod_frame, text="1", bg=CLR_CARD, fg=CLR_ORANGE,
                                    font=("Segoe UI", 8, "bold"), width=4)
        self.facteur_label.grid(row=0, column=6, padx=2)
        
        # Ligne 2: Code barre et recherche
        lbl(prod_frame, "🔍 Code:", color=CLR_MUTED, size=8).grid(row=1, column=0, sticky="w", padx=3, pady=2)
        self.barcode_var = tk.StringVar()
        self.barcode_entry = entry(prod_frame, width=18, textvariable=self.barcode_var)
        self.barcode_entry.grid(row=1, column=1, padx=3, pady=2)
        self.barcode_entry.bind("<Return>", lambda e: self._search_prod_by_barcode())
        tk.Button(prod_frame, text="Chercher", width=8, command=self._search_prod_by_barcode,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8)).grid(row=1, column=2, padx=3, pady=2)
        
        # Ligne 3: Quantité et Prix
        lbl(prod_frame, "🔢 Qté:", color=CLR_MUTED, size=8).grid(row=2, column=0, sticky="w", padx=3, pady=2)
        self.qty_var = tk.StringVar(value="1")
        entry(prod_frame, width=8, textvariable=self.qty_var, font=("Segoe UI", 9)).grid(row=2, column=1, padx=3, pady=2)

        lbl(prod_frame, "💰 Prix:", color=CLR_MUTED, size=8).grid(row=2, column=2, sticky="w", padx=10, pady=2)
        self.prix_var = tk.StringVar()
        entry(prod_frame, width=12, textvariable=self.prix_var, font=("Segoe UI", 9)).grid(row=2, column=3, padx=3, pady=2)
        # ✅ NOUVEAU : Champ Remise
        lbl(prod_frame, "🏷️ Remise:", color=CLR_MUTED, size=8).grid(row=2, column=4, sticky="w", padx=10, pady=2)
        self.remise_produit_var = tk.StringVar(value="0")
        entry(prod_frame, width=8, textvariable=self.remise_produit_var, font=("Segoe UI", 9)).grid(row=2, column=5, padx=3, pady=2)
        lbl(prod_frame, "%", color=CLR_MUTED, size=8).grid(row=2, column=6, sticky="w", padx=2, pady=2)
        # ✅ Bouton AJOUTER (sans remise) - prend la remise du champ
        btn_ajouter = tk.Button(prod_frame, text="➕ AJOUTER", command=lambda: self.add_ligne(False),
                                bg=CLR_GREEN, fg="white", relief="raised",
                                font=("Segoe UI", 9, "bold"), padx=12, pady=3, cursor="hand2")
        btn_ajouter.grid(row=2, column=7, padx=5, pady=2)

        # ✅ Bouton AJOUTER AVEC REMISE (demande la remise)
        btn_ajouter_remise = tk.Button(prod_frame, text="➕ Remise", command=lambda: self.add_ligne(True),
                                        bg=CLR_ORANGE, fg="white", relief="raised",
                                        font=("Segoe UI", 9, "bold"), padx=12, pady=3, cursor="hand2")
        btn_ajouter_remise.grid(row=2, column=8, padx=5, pady=2)
        # Sélecteur de prix uniquement pour les VENTES - CORRECTION ICI
        if self.bon_type == "vente":
            selector_frame = tk.Frame(prod_frame, bg=CLR_CARD)
            selector_frame.grid(row=3, column=0, columnspan=7, sticky="ew", pady=5)

            # Référence à l'instance pour la méthode on_tiers_change
            self.prix_selector = prix_niveaux.PrixSelectorWidget(
                selector_frame,
                prix_var=self.prix_var,
                client_id_fn=self._get_client_id
            )
            self.prix_selector.pack(fill="x")
        
        # ========== SECTION TABLEAU + BOUTONS ==========
        content_frame = tk.Frame(main_container, bg=CLR_BG)
        content_frame.pack(fill="both", expand=True)
        
        # Tableau à gauche
        tableau_frame = tk.LabelFrame(content_frame, text="📋 Lignes du Bon", bg=CLR_CARD, 
                                      fg=CLR_GREEN, font=("Segoe UI", 10, "bold"),
                                      padx=10, pady=10)
        tableau_frame.pack(side="left", fill="both", expand=True)
        
        cols = ["Produit", "Quantité", "Unité", "Prix Unit.", "Remise %", "Total HT", "TVA", "Total TTC"]
        widths = [250, 70, 50, 80, 70, 90, 70, 110]
        tf, self.tree = make_tree(tableau_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # ========== PANEL DES BOUTONS À DROITE ==========
        panel_droite = tk.Frame(content_frame, bg=CLR_BG, width=320)  # 🟢 LÉGÈREMENT PLUS LARGE
        panel_droite.pack(side="right", fill="y", padx=(5, 0))
        panel_droite.pack_propagate(False)

        # ============================================================
        # 1. SECTION ACTIONS
        # ============================================================
        actions_frame = tk.LabelFrame(panel_droite, text="⚡ ACTIONS", 
                                    bg=CLR_CARD, fg=CLR_ACCENT,
                                    font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=8)
        actions_frame.pack(fill="x", padx=5, pady=5)

        # Boutons actions sur une ligne
        btn_line1 = tk.Frame(actions_frame, bg=CLR_CARD)
        btn_line1.pack(fill="x", pady=2)

        tk.Button(btn_line1, text="🗑 Retirer", command=self.remove_ligne,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        tk.Button(btn_line1, text="💵 Modifier Prix", command=self.modifier_prix_produit,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        tk.Button(btn_line1, text="✏ Modifier Qté", command=self.modifier_quantite,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)

        tk.Button(btn_line1, text="🗑 Vider", command=self.vider_panier,
                bg=CLR_BORDER, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        # Dans la section ACTIONS, après les autres boutons
        tk.Button(btn_line1, text="💰 Remise", command=self.modifier_remise_produit,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI", 8, "bold"), padx=10, pady=4,
                cursor="hand2", width=10).pack(side="left", padx=2)
        # ============================================================
        # 2. SECTION REMISE (seulement pour les ventes)
        # ============================================================
        if self.bon_type == "vente":
            remise_frame = tk.LabelFrame(panel_droite, text="🏷️ REMISE", 
                                        bg=CLR_CARD, fg=CLR_ORANGE,
                                        font=("Segoe UI", 10, "bold"),
                                        padx=10, pady=8)
            remise_frame.pack(fill="x", padx=5, pady=5)
            
            # Type de remise
            type_frame = tk.Frame(remise_frame, bg=CLR_CARD)
            type_frame.pack(fill="x", pady=2)
            
            tk.Label(type_frame, text="Type:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=2)
            
            self.remise_type_var = tk.StringVar(value="aucune")
            
            rb_aucune = tk.Radiobutton(type_frame, text="Aucune", 
                                    variable=self.remise_type_var,
                                    value="aucune", bg=CLR_CARD, fg=CLR_TEXT,
                                    selectcolor=CLR_INPUT, relief="flat",
                                    activebackground=CLR_CARD,
                                    font=("Segoe UI", 8), cursor="hand2")
            rb_aucune.pack(side="left", padx=5)
            rb_aucune.configure(command=self.appliquer_remise)
            
            rb_pourcent = tk.Radiobutton(type_frame, text="%", 
                                        variable=self.remise_type_var,
                                        value="pourcentage", bg=CLR_CARD, fg=CLR_TEXT,
                                        selectcolor=CLR_INPUT, relief="flat",
                                        activebackground=CLR_CARD,
                                        font=("Segoe UI", 8), cursor="hand2")
            rb_pourcent.pack(side="left", padx=5)
            rb_pourcent.configure(command=self.appliquer_remise)
            
            rb_montant = tk.Radiobutton(type_frame, text="Montant", 
                                        variable=self.remise_type_var,
                                        value="montant", bg=CLR_CARD, fg=CLR_TEXT,
                                        selectcolor=CLR_INPUT, relief="flat",
                                        activebackground=CLR_CARD,
                                        font=("Segoe UI", 8), cursor="hand2")
            rb_montant.pack(side="left", padx=5)
            rb_montant.configure(command=self.appliquer_remise)
            
            # Valeur et motif sur la même ligne
            value_frame = tk.Frame(remise_frame, bg=CLR_CARD)
            value_frame.pack(fill="x", pady=2)
            
            tk.Label(value_frame, text="Valeur:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=2)
            
            self.remise_valeur_var = tk.StringVar(value="0")
            entry_remise = entry(value_frame, width=8, textvariable=self.remise_valeur_var,
                                font=("Segoe UI", 9))
            entry_remise.pack(side="left", padx=3)
            entry_remise.bind("<KeyRelease>", lambda e: self.appliquer_remise())
            
            tk.Label(value_frame, text="Motif:", bg=CLR_CARD, fg=CLR_MUTED,
                    font=("Segoe UI", 8)).pack(side="left", padx=(10, 2))
            
            self.remise_motif_var = tk.StringVar(value="")
            entry_motif = entry(value_frame, width=12, textvariable=self.remise_motif_var,
                                font=("Segoe UI", 8))
            entry_motif.pack(side="left", padx=3, fill="x", expand=True)
            entry_motif.bind("<KeyRelease>", lambda e: self.appliquer_remise())
            
            # Bouton appliquer
            btn_remise = tk.Button(remise_frame, text="✅ Appliquer Remise",
                                command=self.appliquer_remise,
                                bg=CLR_ORANGE, fg="white", relief="flat",
                                font=("Segoe UI", 8, "bold"), padx=10, pady=3,
                                cursor="hand2")
            btn_remise.pack(pady=3)

        # ============================================================
        # 3. SECTION RÉCAPITULATIF
        # ============================================================
        recap_frame = tk.LabelFrame(panel_droite, text="📊 RÉCAPITULATIF", 
                                    bg=CLR_CARD, fg=CLR_GREEN,
                                    font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=8)
        recap_frame.pack(fill="x", padx=5, pady=5)

        # Total HT
        row_ht = tk.Frame(recap_frame, bg=CLR_CARD)
        row_ht.pack(fill="x", pady=2)
        tk.Label(row_ht, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        self.total_ht_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_ht, textvariable=self.total_ht_var, bg=CLR_CARD, 
                fg=CLR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right")

        # TVA
        row_tva = tk.Frame(recap_frame, bg=CLR_CARD)
        row_tva.pack(fill="x", pady=2)
        tk.Label(row_tva, text="TVA:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        self.tva_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_tva, textvariable=self.tva_var, bg=CLR_CARD, 
                fg=CLR_ORANGE, font=("Segoe UI", 9, "bold")).pack(side="right")

        # Remise (seulement si appliquée)
        self.remise_affichage_var = tk.StringVar(value="")
        row_remise = tk.Frame(recap_frame, bg=CLR_CARD)
        row_remise.pack(fill="x", pady=2)
        tk.Label(row_remise, text="Remise:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row_remise, textvariable=self.remise_affichage_var, bg=CLR_CARD, 
                fg=CLR_RED, font=("Segoe UI", 9, "bold")).pack(side="right")

        # Séparateur
        sep_recap = tk.Frame(recap_frame, bg=CLR_BORDER, height=1)
        sep_recap.pack(fill="x", pady=4)

        # Total TTC (en gras)
        row_ttc = tk.Frame(recap_frame, bg=CLR_CARD)
        row_ttc.pack(fill="x", pady=2)
        tk.Label(row_ttc, text="⭐ TOTAL TTC:", bg=CLR_CARD, fg=CLR_MUTED,
                font=("Segoe UI", 10, "bold")).pack(side="left")
        self.total_ttc_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_ttc, textvariable=self.total_ttc_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 13, "bold")).pack(side="right")

        # ============================================================
        # 4. SECTION BOUTONS FINAUX
        # ============================================================
        btn_final_frame = tk.Frame(panel_droite, bg=CLR_BG)
        btn_final_frame.pack(fill="x", padx=5, pady=5)

        # Ligne 1: Valider et Annuler
        btn_line2 = tk.Frame(btn_final_frame, bg=CLR_BG)
        btn_line2.pack(fill="x", pady=2)

        tk.Button(btn_line2, text="✅ Valider", command=self.save,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"), padx=15, pady=8,
                cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        tk.Button(btn_line2, text="❌ Annuler", command=self.destroy,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"), padx=15, pady=8,
                cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        # Ligne 2: Ticket (seulement pour les ventes)
        if self.bon_type == "vente":
            btn_line3 = tk.Frame(btn_final_frame, bg=CLR_BG)
            btn_line3.pack(fill="x", pady=2)
            
            tk.Button(btn_line3, text="🖨 Ticket", command=self.imprimer_ticket_rapide,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                    cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")
            
            tk.Button(btn_line3, text="📄 Facture", command=self.creer_facture_rapide,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 9, "bold"), padx=15, pady=6,
                    cursor="hand2", width=12).pack(side="left", padx=3, expand=True, fill="x")

        # Raccourcis clavier
        shortcuts_frame = tk.Frame(panel_droite, bg=CLR_BG)
        shortcuts_frame.pack(fill="x", pady=5)
        shortcuts_label = tk.Label(shortcuts_frame, 
                                text="Entrée (Ajouter) | Suppr (Retirer) | F11 (Plein écran)", 
                                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 7))
        shortcuts_label.pack()

        # Bindings des raccourcis clavier
        self.bind('<Return>', lambda e: self.add_ligne())
        self.bind('<Delete>', lambda e: self.remove_ligne())
        if self.prod_map:
            self.prod_var.set(list(self.prod_map.keys())[0])
    def refresh_produits(self):
        """✅ Rafraîchit la liste des produits dans le combobox"""
        print(f"🔄 BonDialog.refresh_produits() appelé !")  # DEBUG
        
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion, 
                                prix_achat, prix_vente, barcode,
                                prix_detail, prix_gros, prix_super_gros, prix_special,
                                tva
                            FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        # Sauvegarder l'ancienne sélection
        old_selection = self.prod_var.get() if hasattr(self, 'prod_var') else ""
        
        # Mettre à jour le dictionnaire des produits
        self.prod_map = {}
        new_prod_list = []
        
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
            new_prod_list.append(key)
        
        print(f"📦 Nouveaux produits: {len(new_prod_list)}")  # DEBUG
        
        # ✅ MÉTHODE SIMPLIFIÉE : Mettre à jour directement la combobox
        self._update_combobox_produits(new_prod_list, old_selection)
        
        # Mettre à jour les informations du produit sélectionné
        if old_selection in self.prod_map:
            p = self.prod_map[old_selection]
            unite = p["unite"] if p["unite"] else "Pcs"
            if hasattr(self, 'unite_label'):
                self.unite_label.config(text=unite)
            facteur = p["facteur_conversion"] if p["facteur_conversion"] else 1
            if hasattr(self, 'facteur_label'):
                self.facteur_label.config(text=f"{facteur:.0f}")
            
            if hasattr(self, 'prix_selector'):
                self.prix_selector.set_produit(p)
            else:
                if self.bon_type == "achat":
                    px = p.get("prix_achat", 0)
                else:
                    px = p.get("prix_detail") or p.get("prix_vente", 0)
                self.prix_var.set(str(px))
        elif new_prod_list:
            self.prod_var.set(new_prod_list[0])
        
        # ✅ Si un nouveau produit a été ajouté, afficher un message discret
        if old_selection != self.prod_var.get() and new_prod_list:
            self._afficher_notification("✅ Nouveau produit disponible !")
    
    def _update_combobox_produits(self, new_prod_list, old_selection):
        """✅ Met à jour la combobox des produits - VERSION SIMPLIFIÉE"""
        # Méthode 1: Chercher dans la structure de la fenêtre
        # On parcourt tous les widgets pour trouver le combobox
        def find_and_update(widget):
            if isinstance(widget, ttk.Combobox):
                # Vérifier si c'est la combobox des produits
                # On vérifie si les valeurs ressemblent à des produits
                if widget['values'] and len(widget['values']) > 0:
                    # Vérifier si le premier élément contient " - " (format produit)
                    if " - " in str(widget['values'][0]):
                        widget['values'] = new_prod_list
                        if old_selection in new_prod_list:
                            self.prod_var.set(old_selection)
                        elif new_prod_list:
                            self.prod_var.set(new_prod_list[0])
                        return True
            return False
        
        # Parcourir récursivement tous les widgets
        def traverse(widget):
            if find_and_update(widget):
                return True
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if traverse(child):
                        return True
            return False
        
        traverse(self)
        
        # ✅ MÉTHODE 2: Si la première méthode échoue, forcer la mise à jour
        # Chercher le combobox dans le frame 'prod_frame'
        for child in self.winfo_children():
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_children'):
                        for grandchild in subchild.winfo_children():
                            if isinstance(grandchild, ttk.Combobox):
                                if grandchild['values'] and len(grandchild['values']) > 0:
                                    # Si les valeurs contiennent " - ", c'est probablement la bonne
                                    if " - " in str(grandchild['values'][0]):
                                        grandchild['values'] = new_prod_list
                                        if old_selection in new_prod_list:
                                            self.prod_var.set(old_selection)
                                        elif new_prod_list:
                                            self.prod_var.set(new_prod_list[0])
                                        return
    
    def _afficher_notification(self, message):
        """Affiche une notification temporaire dans la fenêtre"""
        # Créer un label de notification qui disparaît après 3 secondes
        notification = tk.Label(self, text=message, bg=CLR_GREEN, fg="white",
                               font=("Segoe UI", 10, "bold"), padx=20, pady=10)
        notification.place(relx=0.5, rely=0.02, anchor="n")
        self.after(3000, notification.destroy)  
    def _get_client_id(self):
        """Retourne l'ID du client sélectionné pour les prix spéciaux"""
        if not hasattr(self, 'tiers_var') or not self.tiers_var.get():
            return None
        if self.bon_type != "vente":
            return None
        tiers_nom = self.tiers_var.get()
        if hasattr(self, 'tiers_map') and tiers_nom in self.tiers_map:
            return self.tiers_map[tiers_nom]
        return None
    def modifier_quantite(self):
        """Modifier la quantité d'une ligne sélectionnée"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne à modifier")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]
        
        # ✅ Fenêtre de dialogue dédiée
        dlg = tk.Toplevel(self)
        dlg.title("Modifier la quantité")
        dlg.configure(bg=CLR_BG)
        dlg.geometry("400x300")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        center_window(dlg, 400, 300)
        
        main_frame = tk.Frame(dlg, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏️ Modifier la quantité", 12, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # Informations du produit
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=5)
        
        facteur = ligne.get("facteur", 1)
        qte_affichee = ligne["quantite"] 
        # facteur if facteur else ligne["quantite"]
        
        lbl(info_frame, f"Produit: {ligne['designation']}", 10, True, CLR_TEXT).pack(anchor="w")
        lbl(info_frame, f"Quantité actuelle: {qte_affichee:.2f} {ligne.get('unite', 'Pcs')}", 9, False, CLR_MUTED).pack(anchor="w")
        lbl(info_frame, f"Prix unitaire: {ligne['prix']:.2f} DA", 9, False, CLR_MUTED).pack(anchor="w")
        
        # Champ de saisie
        input_frame = tk.Frame(main_frame, bg=CLR_BG)
        input_frame.pack(fill="x", pady=10)
        
        lbl(input_frame, "Nouvelle quantité:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        new_qty_var = tk.StringVar(value=str(qte_affichee))
        entry_qty = entry(input_frame, width=12, textvariable=new_qty_var, font=("Segoe UI", 11, "bold"))
        entry_qty.pack(side="left", padx=10)
        entry_qty.focus_set()
        entry_qty.select_range(0, tk.END)
        
        # ✅ Message de statut (au lieu de messagebox)
        status_var = tk.StringVar(value="")
        status_label = tk.Label(main_frame, textvariable=status_var, bg=CLR_BG, 
                            fg=CLR_GREEN, font=("Segoe UI", 9, "bold"))
        status_label.pack(pady=5)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        def valider_modification():
            try:
                nouvelle_qty = parse_decimal(new_qty_var.get())
                if nouvelle_qty <= 0:
                    status_var.set("❌ La quantité doit être > 0")
                    status_label.config(fg=CLR_RED)
                    return
            except ValueError:
                status_var.set("❌ Quantité invalide")
                status_label.config(fg=CLR_RED)
                return
            
            # Mettre à jour la ligne
            facteur_ligne = ligne.get("facteur", 1)
            nouvelle_qty_base = nouvelle_qty * facteur_ligne
            ligne["quantite"] = nouvelle_qty
            ligne["quantite_base"] = nouvelle_qty_base
            ligne["total"] = nouvelle_qty_base * ligne["prix"]
            
            # ✅ Rafraîchir la treeview principale AVANT de fermer
            self._refresh_tree()
            
            # ✅ Afficher le succès dans le label avant de fermer
            status_var.set(f"✅ Quantité mise à jour: {nouvelle_qty:.2f}")
            status_label.config(fg=CLR_GREEN)
            
            # ✅ Fermer après un court délai pour que l'utilisateur voie le message
            self.after(500, dlg.destroy)
        
        def annuler_modification():
            dlg.destroy()
        
        # Bind Entrée pour valider
        entry_qty.bind('<Return>', lambda e: valider_modification())
        entry_qty.bind('<Escape>', lambda e: annuler_modification())
        
        tk.Button(btn_frame, text="✅ Valider (Entrée)", command=valider_modification,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ Annuler (Echap)", command=annuler_modification,
                bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
    
    def modifier_prix_produit(self):
        """Modifier le prix unitaire d'une ligne et recalculer total/TVA/TTC"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne")
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]

        nouveau_prix = simpledialog.askfloat(
            "💵 Modifier le prix",
            f"Produit: {ligne['designation']}\n"
            f"Prix actuel: {ligne['prix']:.2f} DA\n\n"
            f"Nouveau prix unitaire (DA):",
            initialvalue=ligne['prix'],
            minvalue=0.01,
            parent=self
        )
        if nouveau_prix is None:
            return
        if nouveau_prix <= 0:
            messagebox.showerror("Erreur", "Le prix doit être > 0")
            return

        # Mettre à jour le prix de base
        ligne["prix"] = nouveau_prix

        # Recalculer en tenant compte d'une éventuelle remise
        remise = ligne.get("remise_produit", 0)
        if remise > 0:
            prix_remise = nouveau_prix * (1 - remise / 100)
        else:
            prix_remise = nouveau_prix

        qte_base = ligne.get("quantite_base", ligne["quantite"])
        total_ht_brut = qte_base * nouveau_prix
        total_ht = qte_base * prix_remise

        ligne["prix_remise"] = prix_remise
        ligne["total_ht_brut"] = total_ht_brut
        ligne["remise_montant"] = total_ht_brut - total_ht
        ligne["total_ht"] = total_ht
        ligne["total"] = total_ht

        tva_taux = ligne.get("tva", 0)
        ligne["total_tva"] = total_ht * tva_taux / 100
        ligne["total_ttc"] = total_ht + ligne["total_tva"]

        # ✅ Recalcule immédiatement le total du bon (HT/TVA/TTC)
        self._refresh_tree()

        messagebox.showinfo("Succès",
            f"✅ Prix mis à jour: {nouveau_prix:.2f} DA\n"
            f"Nouveau total ligne: {total_ht:,.2f} DA")
    def load_tiers_list(self):
        conn = get_conn()
        try:
            if self.bon_type == "achat":
                tiers = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            else:
                tiers = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
        finally:
            conn.close()
        self.tiers_map = {r["nom"]: r["id"] for r in tiers}
        self.tiers_list = list(self.tiers_map.keys())

    def ajouter_tiers(self):
        if self.bon_type == "achat":
            dialog = TiersDialog(self, "fournisseur", data=None)
        else:
            dialog = TiersDialog(self, "client", data=None)
        self.wait_window(dialog)
        self.load_tiers_list()
        self.tiers_combo['values'] = self.tiers_list
        if self.tiers_list:
            self.tiers_var.set(self.tiers_list[-1])
            messagebox.showinfo("Succès", f"{'Fournisseur' if self.bon_type=='achat' else 'Client'} ajouté avec succès !")

    def _search_prod_by_barcode(self):
        raw = self.barcode_var.get().strip()
        if not raw:
            return
        normalized = normalize_barcode_input(raw)
        if not normalized:
            return
        conn = get_conn()
        try:
            produit = conn.execute("SELECT * FROM produits WHERE barcode = ? OR code = ?", (normalized, normalized)).fetchone()
            if not produit:
                produit = conn.execute("SELECT * FROM produits WHERE barcode LIKE ? OR code LIKE ? LIMIT 1", (f"%{normalized}%", f"%{normalized}%")).fetchone()
        finally:
            conn.close()
        if produit:
            display_key = f"{produit['code']} - {produit['designation']}"
            if display_key in self.prod_map:
                self.prod_var.set(display_key)
            else:
                self.prod_map[display_key] = dict(produit)
                self.prod_var.set(display_key)
            
            # Gestion prix vente (si pas de prix, mettre 0 ou gérer le comportement)
            # On convertit le sqlite3.Row en dict pour utiliser .get()
            prod_dict = dict(produit)
            px = prod_dict.get('prix_achat') if self.bon_type == 'achat' else prod_dict.get('prix_vente')
            if px is None: px = 0
            
            self.prix_var.set(str(px))
            self.qty_var.set('1')
            self._afficher_notification(f"✅ {produit['designation']} ajouté")
        else:
            self._afficher_notification(f"❌ Produit non trouvé: {normalized}")

    def _on_prod_change(self, *a):
        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            unite = p["unite"] if p["unite"] else "Pcs"
            self.unite_label.config(text=unite)
            facteur = p["facteur_conversion"] if p["facteur_conversion"] else 1
            self.facteur_label.config(text=f"{facteur:.0f}")

            if hasattr(self, 'prix_selector'):
                self.prix_selector.set_produit(p)
            else:
                if self.bon_type == "achat":
                    px = p.get("prix_achat", 0)
                else:
                    px = p.get("prix_detail") or p.get("prix_vente", 0)
                self.prix_var.set(str(px))
            
            # ✅ Réinitialiser la remise quand on change de produit
            if hasattr(self, 'remise_produit_var'):
                self.remise_produit_var.set("0")

    def on_tiers_change(self, event=None):
        """Met à jour le numéro de bon ET le niveau de prix quand le client change"""
        tiers_nom = self.tiers_var.get()
        if tiers_nom in self.tiers_map:
            tiers_id = self.tiers_map[tiers_nom]
            prefix = "BA" if self.bon_type == "achat" else "BV"
            self.num_var.set(next_numero_tiers(prefix, tiers_id))
        
        # Mise à jour des prix (logique existante)
        if self.bon_type != "vente":
            return
        if not hasattr(self, 'prix_selector'):
            return
        
        key = self.prod_var.get()
        if key and key in self.prod_map:
            self.prix_selector.client_id_fn = self._get_client_id
            self.prix_selector.set_produit(self.prod_map[key])

    def add_ligne(self, demander_remise=False):
        """
        Ajoute une ligne au panier
        demander_remise: True = demande la remise, False = utilise la valeur du champ
        """
        key = self.prod_var.get()
        if key not in self.prod_map:
            messagebox.showerror("Erreur", "Produit invalide")
            return
        try:
            qty = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide")
            return
        
        if qty <= 0:
            messagebox.showerror("Erreur", "Quantité doit être > 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix doit être > 0")
            return
        
        prod = self.prod_map[key]
        facteur = prod["facteur_conversion"] if prod["facteur_conversion"] else 1
        unite = prod["unite"] if prod["unite"] else "Pcs"
        
        # ✅ Quantité en unité de base (pour le stock)
        quantite_en_unite_base = qty * facteur
        
        # ✅ Calcul du total HT brut (sans remise) en unité de base
        total_ht_brut = quantite_en_unite_base * prix
        
        # ✅ TVA RÉELLE du produit
        tva_taux = float(prod.get("tva") or 0)
        
        # ✅ Gestion de la remise
        remise_produit = 0
        
        if demander_remise:
            # ✅ BOUTON "Ajouter avec remise" → demande la remise
            remise_input = simpledialog.askfloat(
                "💰 Remise sur ce produit",
                f"Entrez le pourcentage de remise pour '{key}':\n\n"
                f"Prix unitaire: {prix:.2f} DA\n"
                f"Quantité: {qty:.2f}\n"
                f"Facteur de conversion: {facteur}\n"
                f"Quantité en unité de base: {quantite_en_unite_base:.2f}\n"
                f"Total HT brut: {total_ht_brut:,.2f} DA\n\n"
                f"Remise (%):",
                minvalue=0,
                maxvalue=100,
                parent=self
            )
            if remise_input is None:
                return
            if remise_input > 0:
                remise_produit = remise_input
        else:
            # ✅ BOUTON "AJOUTER" normal → utilise la valeur du champ
            try:
                remise_produit = parse_decimal(self.remise_produit_var.get() or "0")
                if remise_produit < 0 or remise_produit > 100:
                    messagebox.showerror("Erreur", "La remise doit être entre 0 et 100%")
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Remise invalide")
                return
        
        # ✅ Calcul avec remise
        if remise_produit > 0:
            prix_remise = prix * (1 - remise_produit / 100)
            total_ht = quantite_en_unite_base * prix_remise
            remise_montant = total_ht_brut - total_ht
        else:
            prix_remise = prix
            total_ht = total_ht_brut
            remise_montant = 0
        
        total_tva = total_ht * tva_taux / 100
        total_ttc = total_ht + total_tva

        # ✅ VÉRIFIER SI LE PRODUIT EXISTE DÉJÀ
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                # ✅ Calculer la quantité actuelle en unité d'affichage
                qty_actuelle = ligne["quantite"] / ligne["facteur"] if ligne["facteur"] else ligne["quantite"]
                
                reponse = messagebox.askyesno(
                    "Produit déjà ajouté",
                    f"Le produit '{key}' est déjà dans le bon.\n"
                    f"Quantité actuelle: {qty_actuelle:.2f}\n"
                    f"Nouvelle quantité: {qty:.2f}\n\n"
                    f"Voulez-vous CUMULER les quantités ?"
                )
                if reponse:
                    # ✅ CUMULER CORRECTEMENT avec le facteur de conversion
                    # Mettre à jour la quantité affichée (en cartons/kg)
                    ligne["quantite"] += qty
                    # Mettre à jour la quantité en unité de base
                    ligne["quantite_base"] += quantite_en_unite_base
                    
                    # ✅ Recalculer les totaux avec la nouvelle quantité totale
                    quantite_base_totale = ligne["quantite_base"]
                    
                    # ✅ Calculer le nouveau total HT avec remise
                    if ligne.get("remise_produit", 0) > 0:
                        # Si le produit a une remise, l'appliquer sur le total
                        prix_remise_cumule = ligne["prix"] * (1 - ligne["remise_produit"] / 100)
                        ligne["total_ht"] = quantite_base_totale * prix_remise_cumule
                        ligne["prix_remise"] = prix_remise_cumule
                        ligne["remise_montant"] = (quantite_base_totale * ligne["prix"]) - ligne["total_ht"]
                    else:
                        # Sans remise
                        ligne["total_ht"] = quantite_base_totale * ligne["prix"]
                    
                    # ✅ Recalculer TVA et TTC
                    tva_taux_ligne = ligne.get("tva", 0)
                    ligne["total_tva"] = ligne["total_ht"] * tva_taux_ligne / 100
                    ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]
                    ligne["total"] = ligne["total_ht"]
                    
                    # ✅ Mettre à jour le prix_remise si la remise est active
                    if ligne.get("remise_produit", 0) > 0:
                        if ligne["quantite_base"] > 0:
                            ligne["prix_remise"] = ligne["total_ht"] / ligne["quantite_base"]
                    
                    messagebox.showinfo("Succès", 
                        f"✅ Quantité mise à jour\n"
                        f"Nouvelle quantité: {ligne['quantite']:.2f}\n"
                        f"Nouveau total: {ligne['total_ht']:,.2f} DA")
                else:
                    messagebox.showinfo("Info", "Ajout annulé")
                self._refresh_tree()
                self.qty_var.set("1")
                self.prix_var.set("")
                self.remise_produit_var.set("0")
                return

        # ✅ NOUVEAU PRODUIT
        self.lignes.append({
            "produit_id":    prod["id"],
            "designation":   key,
            "barcode":       prod.get("barcode", ""),
            "quantite":      qty,  # ✅ Quantité en unité d'affichage (cartons)
            "unite":         unite,
            "facteur":       facteur,
            "quantite_base": quantite_en_unite_base,  # ✅ Quantité en unité de stock
            "prix":          prix,
            "prix_remise":   prix_remise,
            "remise_produit": remise_produit,
            "remise_montant": remise_montant,
            "total_ht_brut": total_ht_brut,
            "total_ht":      total_ht,
            "tva":           tva_taux,
            "total_tva":     total_tva,
            "total_ttc":     total_ttc,
            "total":         total_ht,
        })
        self._refresh_tree()
        
        # ✅ Réinitialiser les champs
        self.qty_var.set("1")
        self.prix_var.set("")
        self.remise_produit_var.set("0")
        
        if demander_remise and remise_produit > 0:
            messagebox.showinfo("Succès", 
                            f"✅ Produit ajouté avec remise de {remise_produit:.0f}%\n"
                            f"Nouveau prix: {prix_remise:.2f} DA")

    def remove_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez une ligne à supprimer")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_tree()
    def vider_panier(self):
        """Vider toutes les lignes du panier"""
        if not self.lignes:
            messagebox.showinfo("Information", "Le panier est déjà vide")
            return
        
        if messagebox.askyesno("Confirmation", 
                            "⚠️ Vider tout le panier ?\n\n"
                            "Toutes les lignes seront supprimées."):
            self.lignes = []
            self._refresh_tree()
            
            # Réinitialiser la remise
            if hasattr(self, 'remise_type_var'):
                self.remise_type_var.set("aucune")
            if hasattr(self, 'remise_valeur_var'):
                self.remise_valeur_var.set("0")
            if hasattr(self, 'remise_motif_var'):
                self.remise_motif_var.set("")
            
            # Réappliquer la remise (pour remettre à zéro)
            if hasattr(self, 'appliquer_remise'):
                self.appliquer_remise()
            
            messagebox.showinfo("Succès", "🗑 Panier vidé avec succès")
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        total_ht = 0
        total_tva = 0
        total_ttc = 0
        total_remise = 0
        
        for i, l in enumerate(self.lignes):
            facteur = l.get("facteur", 1) or 1
            # Utiliser la quantité en unité de base pour les calculs
            qte_base = l.get("quantite_base", l["quantite"])
            qte_carton = l["quantite"]
            
            # Quantité affichée (avec cartons)
            qty_display = l["quantite"] 
            qty_text = f"{qty_display:.2f}" if facteur > 1 else f"{qty_display:.2f}"
            
            tva_taux = l.get("tva", 0)
            # ✅ PRIX ORIGINAL (avant remise) pour l'affichage
            prix_original = l["prix"]  # Le prix original sans remise
            
            # ✅ PRIX AVEC REMISE pour le calcul du total
            prix_remise = l.get("prix_remise", l["prix"])
            
            # Calculer le HT en utilisant la quantité de base
            ht_ligne = qte_base * prix_remise
            remise = l.get("remise_produit", 0)
            remise_montant = l.get("remise_montant", 0)
            
            remise_affichage = f"{remise:.0f}%" if remise > 0 else "-"
            
            tva_ligne = ht_ligne * tva_taux / 100
            ttc_ligne = ht_ligne + tva_ligne
            
            self.tree.insert("", "end", iid=str(i),
                values=(
                    l["designation"], 
                    qty_text,
                    l.get("unite", "Pcs"),
                    f"{prix_original:.2f}",
                    remise_affichage,
                    f"{ht_ligne:.2f}",
                    f"{tva_taux:.0f}%",
                    f"{ttc_ligne:.2f}"
                ))
            
            total_ht += ht_ligne
            total_tva += tva_ligne
            total_ttc += ttc_ligne
            total_remise += remise_montant
            
            # Mettre à jour les valeurs dans la ligne
            l["total_ht"] = ht_ligne
            l["total_tva"] = tva_ligne
            l["total_ttc"] = ttc_ligne
        
        # Mise à jour des totaux
        if self.bon_type == "achat":
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            self.tva_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
        else:
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            if total_remise > 0:
                self.tva_var.set(f"Remises: {total_remise:,.2f} DA")
            else:
                self.tva_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
    def appliquer_remise(self, event=None):
        """Appliquer une remise sur le total en tenant compte du facteur de conversion"""
        if self.bon_type != "vente":
            return
        
        # Calculer le total HT en tenant compte du facteur de conversion
        total_ht = 0
        for l in self.lignes:
            # Utiliser la quantité en unité de base (facteur * quantité)
            qte_base = l.get("quantite_base", l["quantite"])
            prix = l.get("prix_remise", l["prix"])
            ht_ligne = qte_base * prix
            total_ht += ht_ligne
        
        self.total_avant_remise = total_ht
        
        if not self.lignes:
            self.total_ht_var.set("0.00 DA")
            self.tva_var.set("0.00 DA")
            self.total_ttc_var.set("0.00 DA")
            return
        
        remise_type = self.remise_type_var.get()
        try:
            remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
        except ValueError:
            remise_valeur = 0
        
        self.remise_type = remise_type
        self.remise_valeur = remise_valeur
        
        # Calculer le total après remise
        if remise_type == "aucune" or remise_valeur <= 0:
            total_apres = total_ht
            remise_montant = 0
            self.remise_appliquee = False
        elif remise_type == "pourcentage":
            remise_montant = total_ht * remise_valeur / 100
            total_apres = total_ht - remise_montant
            self.remise_appliquee = True
        else:  # montant fixe
            remise_montant = min(remise_valeur, total_ht)
            total_apres = total_ht - remise_montant
            self.remise_appliquee = True
        
        self.total_apres_remise = total_apres
        
        # Mettre à jour l'affichage avec le TTC (si TVA)
        total_ttc = total_apres
        
        self.total_ht_var.set(f"{total_apres:,.2f} DA")
        
        if self.remise_appliquee:
            remise_text = f"{remise_montant:,.2f} DA"
            if remise_type == "pourcentage":
                remise_text = f"{remise_valeur:.1f}% ({remise_montant:,.2f} DA)"
            self.tva_var.set(f"Remise: {remise_text}")
            self.total_ttc_var.set(f"{total_apres:,.2f} DA")
            
            self.remise_motif = self.remise_motif_var.get().strip()
        else:
            self.tva_var.set("0.00 DA")
            self.total_ttc_var.set(f"{total_apres:,.2f} DA")
    def modifier_remise_produit(self):
        """Modifier la remise d'un produit sélectionné"""
        if self.bon_type != "vente":
            messagebox.showinfo("Information", "La remise est uniquement disponible pour les ventes")
            return
        
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        
        idx = int(sel[0])
        ligne = self.lignes[idx]
        
        remise_actuelle = ligne.get('remise_produit', 0)
        
        nouvelle_remise = simpledialog.askfloat(
            "💰 Modifier la remise",
            f"Produit: {ligne['designation']}\n"
            f"Prix unitaire original: {ligne['prix']:.2f} DA\n"
            f"Prix actuel: {ligne.get('prix_remise', ligne['prix']):.2f} DA\n"
            f"Remise actuelle: {remise_actuelle:.1f}%\n\n"
            f"Nouvelle remise (%):",
            initialvalue=remise_actuelle,
            minvalue=0,
            maxvalue=100,
            parent=self
        )
        
        if nouvelle_remise is None:
            return
        
        if nouvelle_remise < 0 or nouvelle_remise > 100:
            messagebox.showerror("Erreur", "La remise doit être entre 0 et 100%")
            return
        
        # ✅ Recalculer avec la nouvelle remise
        prix_original = ligne['prix']
        prix_remise = prix_original * (1 - nouvelle_remise / 100)
        total_ht_brut = ligne['quantite_base'] * prix_original
        total_ht = ligne['quantite_base'] * prix_remise
        remise_montant = total_ht_brut - total_ht
        
        # ✅ Mettre à jour la ligne
        ligne['remise_produit'] = nouvelle_remise
        ligne['prix_remise'] = prix_remise
        ligne['total_ht'] = total_ht
        ligne['remise_montant'] = remise_montant
        ligne['total_ht_brut'] = total_ht_brut
        
        # ✅ Recalculer TVA et TTC
        tva_taux = ligne.get('tva', 0)
        ligne['total_tva'] = total_ht * tva_taux / 100
        ligne['total_ttc'] = total_ht + ligne['total_tva']
        
        self._refresh_tree()
        messagebox.showinfo("Succès", 
                        f"✅ Remise mise à jour: {nouvelle_remise:.1f}%\n"
                        f"Nouveau prix: {prix_remise:.2f} DA\n"
                        f"Nouveau total: {total_ht:,.2f} DA")  
    def imprimer_ticket_rapide(self):
        """Afficher un aperçu du ticket de caisse"""
        if not self.lignes:
            messagebox.showwarning("Avertissement", "Le panier est vide")
            return
        
        # Calculer le total
        total = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        total_tva = sum(l.get("total_tva", 0) for l in self.lignes)
        
        # Vérifier s'il y a une remise globale
        remise_globale = 0
        remise_type = ""
        remise_valeur = 0
        
        if hasattr(self, 'remise_appliquee') and self.remise_appliquee:
            remise_type = self.remise_type_var.get()
            remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
            
            if remise_type == "pourcentage":
                remise_globale = total * remise_valeur / 100
            elif remise_type == "montant":
                remise_globale = min(remise_valeur, total)
        
        total_apres = total - remise_globale
        client_nom = self.tiers_var.get() if hasattr(self, 'tiers_var') else "COMPTOIR"
        
        # Créer la fenêtre d'aperçu
        preview = tk.Toplevel(self)
        preview.title("🧾 Aperçu Ticket")
        preview.configure(bg="white")
        preview.geometry("400x650")
        preview.transient(self)
        preview.grab_set()
        center_window(preview, 400, 650)
        
        # Contenu du ticket
        ticket_frame = tk.Frame(preview, bg="white", padx=20, pady=20)
        ticket_frame.pack(fill="both", expand=True)
        
        # En-tête
        tk.Label(ticket_frame, text="VOTRE MAGASIN", 
                font=("Courier", 14, "bold"), bg="white").pack()
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Infos
        tk.Label(ticket_frame, text=f"Client: {client_nom}", 
                font=("Courier", 9), bg="white", anchor="w").pack(fill="x")
        tk.Label(ticket_frame, text=f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                font=("Courier", 8), bg="white", anchor="w").pack(fill="x")
        tk.Label(ticket_frame, text="-"*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Lignes de produits
        for l in self.lignes:
            designation = l.get("designation", "Produit")
            if len(designation) > 25:
                designation = designation[:22] + "..."
            
            qty = l.get("quantite", 0)
            prix = l.get("prix_remise", l.get("prix", 0))
            total_ligne = l.get("total_ht", l["total"])
            remise_produit = l.get("remise_produit", 0)
            
            # Ligne produit
            line_text = f"{qty:.0f} x {designation}"
            tk.Label(ticket_frame, text=line_text, font=("Courier", 8), 
                    bg="white", anchor="w").pack(fill="x")
            
            # Prix avec remise si applicable
            if remise_produit > 0:
                prix_text = f"  {prix:.2f} DA (-{remise_produit:.0f}%)"
            else:
                prix_text = f"  {prix:.2f} DA"
            tk.Label(ticket_frame, text=prix_text, font=("Courier", 8), 
                    bg="white", anchor="w").pack(fill="x")
        
        tk.Label(ticket_frame, text="-"*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        # Totaux
        tk.Label(ticket_frame, text=f"TOTAL HT: {total:,.2f} DA", 
                font=("Courier", 9), bg="white", anchor="e").pack(fill="x")
        
        if total_tva > 0:
            tk.Label(ticket_frame, text=f"TVA: {total_tva:,.2f} DA", 
                    font=("Courier", 9), bg="white", anchor="e").pack(fill="x")
        
        if remise_globale > 0:
            tk.Label(ticket_frame, text=f"Remise: -{remise_globale:,.2f} DA", 
                    font=("Courier", 9), bg="white", fg="red", anchor="e").pack(fill="x")
            if remise_type == "pourcentage":
                tk.Label(ticket_frame, text=f"  ({remise_valeur:.0f}%)", 
                        font=("Courier", 7), bg="white", fg="red", anchor="e").pack(fill="x")
        
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=3)
        tk.Label(ticket_frame, text=f"⭐ TOTAL TTC: {total_apres + total_tva:,.2f} DA", 
                font=("Courier", 12, "bold"), bg="white", fg="green", anchor="e").pack(fill="x")
        tk.Label(ticket_frame, text="="*35, font=("Courier", 8), bg="white").pack(pady=5)
        
        tk.Label(ticket_frame, text="MERCI DE VOTRE VISITE !", 
                font=("Courier", 10, "bold"), bg="white").pack()
        tk.Label(ticket_frame, text=f"Généré le {datetime.now().strftime('%H:%M:%S')}", 
                font=("Courier", 7), bg="white").pack()
        
        # Boutons
        btn_frame = tk.Frame(preview, bg="white", pady=10)
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="❌ Fermer", command=preview.destroy, 
                bg=CLR_RED, fg="white", font=("Segoe UI", 9, "bold"),
                padx=15, pady=5, cursor="hand2").pack(side="left", padx=5, expand=True)
        
        tk.Button(btn_frame, text="🖨 Imprimer", 
                command=lambda: self._imprimer_ticket_html(preview),
                bg=CLR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                padx=15, pady=5, cursor="hand2").pack(side="left", padx=5, expand=True)

    def _imprimer_ticket_html(self, preview_window):
        """Imprimer le ticket via HTML"""
        try:
            # Récupérer tout le texte du ticket
            content = ""
            for child in preview_window.winfo_children():
                if isinstance(child, tk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            text = subchild.cget("text")
                            if text:
                                content += text + "\n"
            
            # Créer un fichier HTML pour impression
            html_content = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Ticket de caisse</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        font-size: 10pt;
                        padding: 20px;
                        margin: 0;
                        white-space: pre-wrap;
                        max-width: 380px;
                        margin: 0 auto;
                    }}
                    @media print {{
                        body {{ padding: 10px; }}
                    }}
                </style>
            </head>
            <body>
                <pre>{content}</pre>
                <script>
                    window.onload = function() {{
                        window.print();
                        setTimeout(function() {{ window.close(); }}, 1000);
                    }}
                </script>
            </body>
            </html>
            """
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                                    delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            webbrowser.open(temp_file.name)
            
            messagebox.showinfo("Impression", 
                            "Ticket ouvert dans le navigateur.\n"
                            "Utilisez Ctrl+P pour imprimer.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'impression: {str(e)}")

    def creer_facture_rapide(self):
        """Créer une facture à partir du bon en cours"""
        if not self.lignes:
            messagebox.showwarning("Avertissement", "Le panier est vide")
            return
        
        # Vérifier si un client est sélectionné
        tiers_nom = self.tiers_var.get() if hasattr(self, 'tiers_var') else ""
        if not tiers_nom or tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", 
                                "Sélectionnez un client pour créer une facture.\n"
                                "Le client COMPTOIR n'est pas éligible pour une facture.")
            return
        
        # Vérifier que ce n'est pas le client COMPTOIR
        if tiers_nom == "COMPTOIR":
            messagebox.showerror("Erreur", 
                                "Impossible de créer une facture pour le client COMPTOIR.\n"
                                "Veuillez sélectionner un client avec des informations fiscales.")
            return
        
        # Calculer le total
        total = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        
        # Demander confirmation
        if messagebox.askyesno("Confirmation", 
                            f"Créer une facture pour le client {tiers_nom} ?\n\n"
                            f"Total HT: {total:,.2f} DA\n"
                            f"Total TTC: {self.total_ttc_var.get() if hasattr(self, 'total_ttc_var') else 'N/A'}"):
            # Sauvegarder d'abord le bon
            self.save()
            messagebox.showinfo("Info", 
                            "✅ Le bon a été sauvegardé.\n\n"
                            "Vous pouvez maintenant créer la facture depuis la page Factures,\n"
                            "ou utiliser le bouton '🧾 Créer Facture' dans la liste des bons.")             
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins une ligne")
            return
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", "Sélectionnez un tiers")
            return
        tiers_id = self.tiers_map[tiers_nom]
        
        # Calculer les totaux HT et TTC
        total_ht_brut = sum(l.get("total_ht", l["total"]) for l in self.lignes)
        
        # ✅ CORRECTION : Vérifier si les attributs de remise existent
        remise_montant = 0
        remise_type = "aucune"
        remise_valeur = 0
        motif_remise = ""
        
        if self.bon_type == "vente" and hasattr(self, 'remise_type_var'):
            remise_type = self.remise_type_var.get()
            try:
                remise_valeur = parse_decimal(self.remise_valeur_var.get() or "0")
            except ValueError:
                remise_valeur = 0
            
            if remise_type != "aucune" and remise_valeur > 0:
                if remise_type == "pourcentage":
                    remise_montant = total_ht_brut * remise_valeur / 100
                else:  # montant fixe
                    remise_montant = min(remise_valeur, total_ht_brut)
                
                total_ht = total_ht_brut - remise_montant
                motif_remise = self.remise_motif_var.get().strip() or "Remise accordée"
            else:
                total_ht = total_ht_brut
        else:
            total_ht = total_ht_brut
        
        # Calculer la TVA et le TTC
        total_tva = 0
        total_ttc = 0
        
        for l in self.lignes:
            tva_taux = l.get("tva", 0)
            ht_ligne = l.get("total_ht", l["total"])
            
            if self.bon_type == "vente" and remise_montant > 0 and total_ht_brut > 0:
                # ✅ Répartir la remise proportionnellement sur chaque ligne
                proportion = ht_ligne / total_ht_brut
                ht_avec_remise = ht_ligne - (remise_montant * proportion)
            else:
                ht_avec_remise = ht_ligne
            
            tva_ligne = ht_avec_remise * tva_taux / 100
            ttc_ligne = ht_avec_remise + tva_ligne
            
            total_tva += tva_ligne
            total_ttc += ttc_ligne
            
            # ✅ STOCKER LE HT AVEC REMISE POUR L'ENREGISTREMENT
            l["total_ht_avec_remise"] = ht_avec_remise
            l["total_ttc_avec_remise"] = ttc_ligne
            l["tva_ligne"] = tva_ligne
        
        # Régénérer le numéro avec l'ID du tiers au moment de valider
        tiers_id_local = self.tiers_map[tiers_nom]
        prefix = "BA" if self.bon_type == "achat" else "BV"
        num = next_numero_tiers(prefix, tiers_id_local)
        self.num_var.set(num)      
        dt = self.date_var.get()

        if not valider_date(self.date_var.get()):
            messagebox.showerror("Erreur", "Format de date invalide.\nUtilisez le format YYYY-MM-DD\nExemple: 2026-06-04")
            return

        # Vérification du stock pour les ventes
        if self.bon_type == "vente":
            conn_verif = get_conn()
            alertes = []
            for l in self.lignes:
                quantite_a_verifier = l.get("quantite_base", l["quantite"])
                produit = conn_verif.execute(
                    "SELECT designation, stock_actuel FROM produits WHERE id=?", 
                    (l["produit_id"],)
                ).fetchone()
                
                if produit and produit["stock_actuel"] < quantite_a_verifier:
                    alertes.append(
                        f"⚠️ {produit['designation']}: Stock actuel={produit['stock_actuel']:.2f}, "
                        f"Vente={quantite_a_verifier:.2f} → Nouveau stock={produit['stock_actuel'] - quantite_a_verifier:.2f}"
                    )
            conn_verif.close()
            
            if alertes:
                messagebox.showwarning(
                    "⚠️ ALERTE STOCK INSUFFISANT",
                    "Les produits suivants ont un stock insuffisant :\n\n" + 
                    "\n".join(alertes) +
                    "\n\n➡ Le bon sera quand même enregistré avec un stock négatif."
                )

        # ✅ Confirmation avec affichage de la remise
        if self.bon_type == "achat":
            if not messagebox.askyesno("Confirmation", 
                f"Valider ce bon d'achat ?\n"
                f"Numéro: {num}\n"
                f"Total HT: {total_ht:,.2f} DA\n"
                f"Total TTC: {total_ttc:,.2f} DA"):
                return
        else:
            msg_confirmation = f"Valider ce bon de vente ?\n\n"
            msg_confirmation += f"Numéro: {num}\n"
            msg_confirmation += f"Client: {tiers_nom}\n"
            msg_confirmation += f"Total HT brut: {total_ht_brut:,.2f} DA\n"
            
            if remise_montant > 0:
                msg_confirmation += f"Remise: {remise_montant:,.2f} DA ({remise_type} {remise_valeur}%)\n"
                msg_confirmation += f"Motif: {motif_remise}\n"
            
            msg_confirmation += f"Total HT après remise: {total_ht:,.2f} DA\n"
            msg_confirmation += f"TVA: {total_tva:,.2f} DA\n"
            msg_confirmation += f"Total TTC: {total_ttc:,.2f} DA"
            
            if not messagebox.askyesno("Confirmation", msg_confirmation):
                return

        conn = get_conn()
        try:
            if self.bon_type == "achat":
                # ... (votre code achat inchangé)
                date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_livraison = self.date_livraison_var.get() if hasattr(self, 'date_livraison_var') else None
                num_facture = self.num_facture_fournisseur_var.get() if hasattr(self, 'num_facture_fournisseur_var') else None
                num_bl = self.num_bl_fournisseur_var.get() if hasattr(self, 'num_bl_fournisseur_var') else None
                
                fournisseur = conn.execute("SELECT solde FROM fournisseurs WHERE id=?", (tiers_id,)).fetchone()
                ancien_solde = fournisseur["solde"] if fournisseur else 0
                
                nouveau_solde = ancien_solde + total_ttc
                
                conn.execute(
                    """INSERT INTO bons_achat(numero, date_bon, date_creation, date_livraison, 
                    fournisseur_id, total, statut, num_facture_fournisseur, num_bl_fournisseur,
                    ancien_solde, nouveau_solde) 
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (num, dt, date_creation, date_livraison, tiers_id, total_ttc, "Validé", 
                    num_facture, num_bl, ancien_solde, nouveau_solde)
                )
                bon_id = conn.execute(
                    "SELECT id FROM bons_achat WHERE numero=?", (num,)
                ).fetchone()["id"]

                for l in self.lignes:
                    quantite_achat = l.get("quantite_base", l["quantite"])
                    ht_l = l.get("total_ht", l["total"])
                    taux = float(l.get("tva", 0))
                    tva_l = l.get("total_tva", ht_l * taux / 100)
                    ttc_l = l.get("total_ttc", ht_l + tva_l)

                    conn.execute(
                        """INSERT INTO lignes_achat
                        (bon_id, produit_id, quantite, prix_unitaire,
                            total_ht, tva_taux, total_ttc, total)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (bon_id, l["produit_id"], quantite_achat, l["prix"],
                        ht_l, taux, ttc_l, ht_l)
                    )
                    nouveau_pmp, nouveau_cout = calculer_pmp(
                        conn, l["produit_id"], quantite_achat, l["prix"]
                    )
                    conn.execute(
                        """UPDATE produits
                        SET stock_actuel = stock_actuel + ?,
                            prix_moyen_pondere = ?,
                            cout_total_stock = ?,
                            prix_achat = ?
                        WHERE id = ?""",
                        (quantite_achat, nouveau_pmp, nouveau_cout, l["prix"], l["produit_id"])
                    )
                    conn.execute(
                        """INSERT INTO historique_prix
                        (produit_id, date_achat, quantite, prix_unitaire, prix_moyen_apres)
                        VALUES(?,?,?,?,?)""",
                        (l["produit_id"], dt, quantite_achat, l["prix"], nouveau_pmp)
                    )
                conn.execute("UPDATE fournisseurs SET solde = solde + ? WHERE id=?", (total_ttc, tiers_id))
                
            else:
                # ✅ VENTE : Enregistrement du bon (TTC dans total, HT et TVA ajoutés)
                vendeur_id = None
                if self.vendeur_var.get():
                    vendeur = conn.execute("SELECT id FROM vendeurs WHERE nom=?", (self.vendeur_var.get(),)).fetchone()
                    if vendeur: vendeur_id = vendeur['id']
                
                conn.execute("""INSERT INTO bons_vente(numero, date_bon, client_id, total, total_ht, tva_total, total_ttc, statut, vendeur_id) 
                                VALUES(?,?,?,?,?,?,?,?,?)""",
                            (num, dt, tiers_id, total_ttc, total_ht, total_tva, total_ttc, "Validé", vendeur_id))
                
                bon_id = conn.execute("SELECT id FROM bons_vente WHERE numero=?", (num,)).fetchone()["id"]
                
                # ✅ ENREGISTRER LES REMISES PAR PRODUIT
                for l in self.lignes:
                    remise_produit = l.get("remise_produit", 0)
                    if remise_produit > 0:
                        conn.execute("""
                            INSERT INTO remises(vente_id, achat_id, produit_id, type, valeur, motif, total_avant, total_apres, reference)
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            bon_id,
                            None,
                            l["produit_id"],
                            "produit",
                            remise_produit, 
                            f"Remise sur {l['designation']}",
                            l.get("total_ht_brut", l.get("total_ht", 0)),
                            l["total_ht"],
                            f"Ligne {l['designation']}"
                        ))
                
                # ✅ Enregistrer les lignes de vente AVEC TVA et REMISES
                for l in self.lignes:
                    quantite_vente = l.get("quantite_base", l.get("quantite", 1))
                    
                    conn.execute("""
                        INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total, total_ht, tva_taux, total_tva, total_ttc)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (bon_id, l["produit_id"], quantite_vente, l.get("prix", 0), l["total_ttc_avec_remise"], 
                          l["total_ht_avec_remise"], l.get("tva", 0), l["tva_ligne"], l["total_ttc_avec_remise"]))
                    
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], quantite_vente)
                    
                
                # ✅ Mise à jour du solde client en TTC
                conn.execute("UPDATE clients SET solde = solde + ? WHERE id=?", (total_ttc, tiers_id))
            
            conn.commit()
            conn.close()
            
            # ✅ Message de succès avec détails
            msg_succes = f"✅ Bon {num} enregistré avec succès !\n\n"
            msg_succes += f"Client: {tiers_nom}\n"
            msg_succes += f"Total HT: {total_ht:,.2f} DA\n"
            if remise_montant > 0:
                msg_succes += f"Remise: {remise_montant:,.2f} DA\n"
            msg_succes += f"TTC: {total_ttc:,.2f} DA"
            
            messagebox.showinfo("Succès", msg_succes)
            self.destroy()
            
        except sqlite3.IntegrityError:
            prefix = "BA" if self.bon_type == "achat" else "BV"
            nouveau_num = next_numero_tiers(prefix, tiers_id)
            self.num_var.set(nouveau_num)
            messagebox.showwarning(
                "Numéro dupliqué",
                f"Le numéro {num} existait déjà.\n"
                f"Nouveau numéro généré : {nouveau_num}\n"
                "Veuillez valider à nouveau."
            )
            if conn:
                conn.rollback()
                conn.close()
        except Exception as ex:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {str(ex)}")
            if conn:
                conn.rollback()
                conn.close()

# ========== DIALOGUE MODIFICATION BON ==========

