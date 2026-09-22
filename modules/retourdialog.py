from modules.core import *

class RetourDialog(tk.Toplevel):
    """Dialogue de création de retour"""
    
    def __init__(self, parent, retour_type):
        super().__init__(parent)
        self.retour_type = retour_type
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        self.bons_table = "bons_vente" if retour_type == "vente" else "bons_achat"
        self.tiers_table = "clients" if retour_type == "vente" else "fournisseurs"
        self.prefix = "RV" if retour_type == "vente" else "RA"
        self.tiers_label = "Client" if retour_type == "vente" else "Fournisseur"
        
        self.lignes = []
        self.bon_selected = None
        
        self.title(f"Nouveau Retour - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        
        # MAXIMISER AVEC BARRE DES TÂCHES VISIBLE
        self.state('zoomed')
        
        self._build()
        self.update_idletasks()
    
    def _build(self):
        # CONTENEUR PRINCIPAL
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True)
        
        # CONTENU PRINCIPAL AVEC PADDING
        main_frame = tk.Frame(main_container, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"↩️ NOUVEAU RETOUR {self.tiers_label.upper()}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Section bon associé
        bon_frame = tk.LabelFrame(main_frame, text="1. Bon associé (optionnel)", 
                                  bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                  padx=15, pady=10)
        bon_frame.pack(fill="x", pady=10)
        
        lbl(bon_frame, f"Bon de {self.tiers_label}:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        if self.retour_type == "vente":
            bons = conn.execute(f"""
                SELECT b.id, b.numero, c.nom as tiers_nom, b.total, b.date_bon
                FROM {self.bons_table} b
                JOIN {self.tiers_table} c ON b.client_id = c.id
                WHERE b.statut = 'Validé'
                ORDER BY b.date_bon DESC
            """).fetchall()
        else:
            bons = conn.execute(f"""
                SELECT b.id, b.numero, f.nom as tiers_nom, b.total, b.date_bon
                FROM {self.bons_table} b
                JOIN {self.tiers_table} f ON b.fournisseur_id = f.id
                WHERE b.statut = 'Validé'
                ORDER BY b.date_bon DESC
            """).fetchall()
        conn.close()
        
        self.bons_map = {}
        bon_liste = ["-- Aucun --"]
        for b in bons:
            display = f"{b['numero']} - {b['tiers_nom']} - {b['total']:,.2f} DA"
            self.bons_map[display] = dict(b)
            bon_liste.append(display)
        
        self.bon_var = tk.StringVar(value="-- Aucun --")
        bon_combo = combo(bon_frame, bon_liste, width=40, textvariable=self.bon_var)
        bon_combo.pack(side="left", padx=10, fill="x", expand=True)
        self.bon_var.trace_add("write", self.on_bon_selected)
        
        # Sélecteur de tiers direct
        tiers_direct_frame = tk.Frame(bon_frame, bg=CLR_CARD)
        tiers_direct_frame.pack(fill="x", pady=5)

        lbl(tiers_direct_frame, f"— ou choisir {self.tiers_label} directement:", 
            9, False, CLR_MUTED).pack(side="left", padx=5)

        conn = get_conn()
        tiers_rows = conn.execute(
            f"SELECT id, nom FROM {self.tiers_table} ORDER BY nom"
        ).fetchall()
        conn.close()

        self.tiers_direct_map = {t["nom"]: t["id"] for t in tiers_rows}
        self.tiers_id_sans_bon = None
        self.tiers_direct_var = tk.StringVar()

        tiers_direct_combo = combo(
            tiers_direct_frame,
            list(self.tiers_direct_map.keys()),
            width=25,
            textvariable=self.tiers_direct_var
        )
        tiers_direct_combo.pack(side="left", padx=10)

        def on_tiers_direct(*_):
            nom = self.tiers_direct_var.get()
            self.tiers_id_sans_bon = self.tiers_direct_map.get(nom)

        self.tiers_direct_var.trace_add("write", on_tiers_direct)
        
        # ✅ Section produit à retourner - TOUT SUR UNE SEULE LIGNE
        prod_frame = tk.LabelFrame(main_frame, text="2. Produit à retourner", 
                                   bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                   padx=15, pady=10)
        prod_frame.pack(fill="x", pady=10)
        
        # ✅ LIGNE UNIQUE POUR TOUS LES CHAMPS + BOUTON AJOUTER
        row_saisie = tk.Frame(prod_frame, bg=CLR_CARD)
        row_saisie.pack(fill="x", pady=5)
        
        # Produit
        lbl(row_saisie, "Produit:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        prods = conn.execute("SELECT id, code, designation, prix_vente, prix_achat, unite, facteur_conversion, stock_actuel FROM produits WHERE actif = 1 ORDER BY designation").fetchall()
        conn.close()
        
        self.prod_map = {}
        prod_liste = []
        for p in prods:
            display = f"{p['code']} - {p['designation']}"
            self.prod_map[display] = dict(p)
            prod_liste.append(display)
        
        self.prod_var = tk.StringVar()
        prod_combo = combo(row_saisie, prod_liste, width=25, textvariable=self.prod_var)
        prod_combo.pack(side="left", padx=5)
        
        # Unité / Mode de conditionnement (Carton vs Pièce)
        lbl(row_saisie, "Unité:", 9, False, CLR_MUTED).pack(side="left", padx=(10,5))
        self.unite_var = tk.StringVar(value="Carton")
        unite_combo = combo(row_saisie, ["Carton", "Pièce"], width=8, textvariable=self.unite_var)
        unite_combo.pack(side="left", padx=5)

        # Quantité
        lbl(row_saisie, "Qté:", 9, False, CLR_MUTED).pack(side="left", padx=(10,5))
        self.qty_var = tk.StringVar(value="1")
        entry(row_saisie, width=6, textvariable=self.qty_var).pack(side="left", padx=5)
        
        # Prix unitaire
        lbl(row_saisie, "Prix:", 9, False, CLR_MUTED).pack(side="left", padx=(10,5))
        self.prix_var = tk.StringVar()
        entry(row_saisie, width=10, textvariable=self.prix_var).pack(side="left", padx=5)
        lbl(row_saisie, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        # ✅ BOUTON AJOUTER EN LIGNE (à droite)
        btn_ajouter = tk.Button(row_saisie, text="➕ AJOUTER", command=self.ajouter_ligne,
                               bg=CLR_GREEN, fg="white", relief="flat", 
                               font=("Segoe UI", 9, "bold"),
                               padx=12, pady=4, cursor="hand2")
        btn_ajouter.pack(side="right", padx=5)
        
        # ✅ Motif sur une ligne séparée (en dessous)
        row_motif = tk.Frame(prod_frame, bg=CLR_CARD)
        row_motif.pack(fill="x", pady=5)
        lbl(row_motif, "Motif du retour:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        self.motif_var = tk.StringVar()
        entry(row_motif, width=60, textvariable=self.motif_var).pack(side="left", padx=10, fill="x", expand=True)
        
        # ✅ CONTENEUR TABLEAU + BOUTONS DROITE (Layout horizontal)
        content_frame = tk.Frame(main_frame, bg=CLR_BG)
        content_frame.pack(fill="both", expand=True, pady=10)
        
        # ✅ TABLEAU À GAUCHE
        tableau_frame = tk.Frame(content_frame, bg=CLR_BG)
        tableau_frame.pack(side="left", fill="both", expand=True)
        
        cols = ["Produit", "Quantité", "Prix unitaire", "Total"]
        widths = [400, 100, 120, 150]
        tf, self.tree = make_tree(tableau_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # ✅ PANEL DES BOUTONS À DROITE
        panel_droite = tk.Frame(content_frame, bg=CLR_BG, width=250)
        panel_droite.pack(side="right", fill="y", padx=(10, 0))
        panel_droite.pack_propagate(False)
        
        # ✅ CADRE DES BOUTONS D'ACTION
        actions_frame = tk.LabelFrame(panel_droite, text="⚡ ACTIONS", 
                                     bg=CLR_CARD, fg=CLR_ACCENT,
                                     font=("Segoe UI", 10, "bold"),
                                     padx=10, pady=8)
        actions_frame.pack(fill="x", pady=5)
        
        # Bouton Retirer ligne
        btn_retirer = tk.Button(actions_frame, text="🗑 Retirer ligne", command=self.retirer_ligne,
                               bg=CLR_RED, fg="white", relief="flat", 
                               font=("Segoe UI", 9, "bold"), padx=10, pady=6,
                               cursor="hand2", width=16)
        btn_retirer.pack(pady=3)
        
        # Bouton Vider tout
        btn_vider = tk.Button(actions_frame, text="🗑 Vider tout", command=self.vider_panier,
                             bg=CLR_ORANGE, fg="white", relief="flat", 
                             font=("Segoe UI", 9, "bold"), padx=10, pady=6,
                             cursor="hand2", width=16)
        btn_vider.pack(pady=3)
        
        # ✅ CADRE RÉCAPITULATIF
        recap_frame = tk.LabelFrame(panel_droite, text="📊 RÉCAPITULATIF", 
                                   bg=CLR_CARD, fg=CLR_GREEN,
                                   font=("Segoe UI", 10, "bold"),
                                   padx=10, pady=8)
        recap_frame.pack(fill="x", pady=5)
        
        # Total
        row_total = tk.Frame(recap_frame, bg=CLR_CARD)
        row_total.pack(fill="x", pady=3)
        lbl(row_total, "Total:", 10, True, CLR_MUTED).pack(side="left")
        self.total_var = tk.StringVar(value="0.00 DA")
        tk.Label(row_total, textvariable=self.total_var, bg=CLR_CARD, 
                fg=CLR_GREEN, font=("Segoe UI", 14, "bold")).pack(side="right")
        
        # Nombre de lignes
        row_nb = tk.Frame(recap_frame, bg=CLR_CARD)
        row_nb.pack(fill="x", pady=3)
        lbl(row_nb, "Lignes:", 9, True, CLR_MUTED).pack(side="left")
        self.nb_lignes_var = tk.StringVar(value="0")
        tk.Label(row_nb, textvariable=self.nb_lignes_var, bg=CLR_CARD, 
                fg=CLR_ACCENT, font=("Segoe UI", 11, "bold")).pack(side="right")
        
        # ✅ CADRE BOUTONS DE VALIDATION
        validation_frame = tk.LabelFrame(panel_droite, text="✅ VALIDATION", 
                                        bg=CLR_CARD, fg=CLR_GREEN,
                                        font=("Segoe UI", 10, "bold"),
                                        padx=10, pady=8)
        validation_frame.pack(fill="x", pady=5)
        
        # Bouton VALIDER
        btn_valider = tk.Button(validation_frame, text="✅ VALIDER", 
                               command=self.save,
                               bg=CLR_GREEN, fg="white", relief="flat", 
                               font=("Segoe UI", 10, "bold"),
                               padx=15, pady=10, cursor="hand2", width=16)
        btn_valider.pack(pady=3)
        
        # Bouton ANNULER
        btn_annuler = tk.Button(validation_frame, text="❌ ANNULER", 
                               command=self.destroy,
                               bg=CLR_RED, fg="white", relief="flat", 
                               font=("Segoe UI", 10, "bold"),
                               padx=15, pady=10, cursor="hand2", width=16)
        btn_annuler.pack(pady=3)
        
        # ✅ Raccourcis clavier
        shortcuts_frame = tk.Frame(panel_droite, bg=CLR_BG)
        shortcuts_frame.pack(fill="x", pady=(5, 0))
        tk.Label(shortcuts_frame, 
                text="Entrée (Ajouter) | Suppr (Retirer)", 
                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 8)).pack()
        
        # Bindings des raccourcis clavier
        self.bind('<Return>', lambda e: self.ajouter_ligne())
        self.bind('<Delete>', lambda e: self.retirer_ligne())
        
        # ✅ Initialisation
        self.refresh_panier()
    
    def on_bon_selected(self, *args):
        key = self.bon_var.get()
        if key != "-- Aucun --" and key in self.bons_map:
            self.bon_selected = self.bons_map[key]
    
    def ajouter_ligne(self):
        prod_key = self.prod_var.get()
        if not prod_key or prod_key not in self.prod_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit")
            return
        
        try:
            qty_saisie = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide")
            return
        
        if qty_saisie <= 0:
            messagebox.showerror("Erreur", "Quantité > 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix > 0")
            return
        
        prod = self.prod_map[prod_key]
        facteur = float(prod.get("facteur_conversion") or 1)
        unite = self.unite_var.get()
        
        # ✅ Calcul de la quantité réelle en pièces/unités de stock
        if unite == "Carton" and facteur > 1:
            quantite_base = qty_saisie * facteur
        else:
            quantite_base = qty_saisie
            
        total = qty_saisie * prix
        
        self.lignes.append({
            "produit_id": prod["id"],
            "designation": f"{prod_key} ({qty_saisie} {unite}{'s' if qty_saisie > 1 else ''})",
            "quantite": quantite_base,
            "qty_saisie": qty_saisie,
            "unite_saisie": unite,
            "prix": prix,
            "total": total
        })
        
        self.refresh_panier()
        self.qty_var.set("1")
        self.prix_var.set("")
    
    def retirer_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self.refresh_panier()
    
    def vider_panier(self):
        if not self.lignes:
            messagebox.showinfo("Information", "Le panier est déjà vide")
            return
        if messagebox.askyesno("Confirmation", "Vider tout le panier ?"):
            self.lignes = []
            self.refresh_panier()
    
    def refresh_panier(self):
        self.tree.delete(*self.tree.get_children())
        total = 0
        for i, l in enumerate(self.lignes):
            self.tree.insert("", "end", iid=str(i), values=(
                l["designation"],
                f"{l['quantite']:.2f}",
                f"{l['prix']:.2f}",
                f"{l['total']:.2f}"
            ))
            total += l["total"]
        self.total_var.set(f"{total:,.2f} DA")
        self.nb_lignes_var.set(str(len(self.lignes)))
    
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins un produit")
            return
        
        total = sum(l["total"] for l in self.lignes)
        num = next_numero(self.prefix, self.table)
        dt = date.today().strftime("%Y-%m-%d")
        motif = self.motif_var.get().strip()
        
        # Distinguer ID du bon et ID du tiers
        if self.bon_selected:
            bon_id = self.bon_selected["id"]
            
            conn_tmp = get_conn()
            if self.retour_type == "vente":
                row = conn_tmp.execute(
                    "SELECT client_id FROM bons_vente WHERE id=?", (bon_id,)
                ).fetchone()
                tiers_id = row["client_id"] if row else None
            else:
                row = conn_tmp.execute(
                    "SELECT fournisseur_id FROM bons_achat WHERE id=?", (bon_id,)
                ).fetchone()
                tiers_id = row["fournisseur_id"] if row else None
            conn_tmp.close()
            
            if not tiers_id:
                messagebox.showerror("Erreur", "Impossible de retrouver le tiers du bon")
                return
        else:
            if not hasattr(self, 'tiers_id_sans_bon') or not self.tiers_id_sans_bon:
                messagebox.showerror(
                    "Erreur",
                    f"Sélectionnez un {self.tiers_label} ou un bon associé."
                )
                return
            tiers_id = self.tiers_id_sans_bon
            bon_id = None
        
        conn = get_conn()
        try:
            if self.retour_type == "vente":
                conn.execute(
                    "INSERT INTO retours_vente(numero, date_retour, bon_vente_id, "
                    "client_id, total, motif) VALUES(?,?,?,?,?,?)",
                    (num, dt, bon_id, tiers_id, total, motif)
                )
            else:
                conn.execute(
                    "INSERT INTO retours_achat(numero, date_retour, bon_achat_id, "
                    "fournisseur_id, total, motif) VALUES(?,?,?,?,?,?)",
                    (num, dt, bon_id, tiers_id, total, motif)
                )
            
            retour_id = conn.execute(
                f"SELECT id FROM {self.table} WHERE numero=?", (num,)
            ).fetchone()["id"]
            
            for l in self.lignes:
                conn.execute(
                    f"INSERT INTO {self.lignes_table}"
                    "(retour_id, produit_id, quantite, prix_unitaire, total) "
                    "VALUES(?,?,?,?,?)",
                    (retour_id, l["produit_id"], l["quantite"], l["prix"], l["total"])
                )
                if self.retour_type == "vente":
                    # ✅ CORRECTION : réintégrer au PMP réel du produit, pas au prix de vente
                    # (le prix de vente inclut la marge, il ne représente pas le coût du stock)
                    entree_stock_annulation_vente(
                        conn, l["produit_id"], l["quantite"],
                        type_mouvement="RETOUR_VENTE", document_type="retour_vente",
                        document_id=retour_id, date_document=dt,
                    )
                    # Diminuer le solde client (retour = moins de dette)
                    conn.execute(
                        "UPDATE clients SET solde = solde - ? WHERE id=?",
                        (l["total"], tiers_id)
                    )
                else:  # Retour achat
                    # Sortie de stock et recalcul du coût (recalculer_cout_stock_apres_sortie gère déjà la décrémentation de stock_actuel)
                    recalculer_cout_stock_apres_sortie(
                        conn, l["produit_id"], l["quantite"],
                        type_mouvement="RETOUR_ACHAT", document_type="retour_achat",
                        document_id=retour_id, date_document=dt,
                    )
                    # Diminuer le solde fournisseur (retour = moins de dette)
                    conn.execute(
                        "UPDATE fournisseurs SET solde = solde - ? WHERE id=?",
                        (l["total"], tiers_id)
                    )

            # ✅ CORRECTION : une seule validation, APRÈS toutes les lignes
            # (avant, le commit était dans la boucle : retour partiellement enregistré)
            conn.commit()
            messagebox.showinfo("Succès", f"Retour {num} enregistré avec succès !")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()

