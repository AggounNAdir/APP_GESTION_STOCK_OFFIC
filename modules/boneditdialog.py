from modules.core import *
from modules.dateentry import DateEntry

class BonEditDialog(tk.Toplevel):
    def __init__(self, parent, bon_type, bon_id, bon_data, lignes):
        super().__init__(parent)
        self.bon_type = bon_type
        self.bon_id = bon_id
        self.bon_data = bon_data
        self.lignes_originales = list(lignes)
        self.lignes = []
        self.title(f"✏ Modification Bon d'{bon_type.capitalize()}")
        self.bind("<<ProduitsModifies>>", lambda e: self.refresh_produits())
        self.configure(bg=CLR_BG)
        self.state('zoomed')  # Pour Windows

        self.geometry("900x750")

        # Charger le solde actuel du tiers
        conn = get_conn()
        if self.bon_type == "achat":
            tiers_row = conn.execute("SELECT solde FROM fournisseurs WHERE id=?", (self.bon_data["fournisseur_id"],)).fetchone()
        else:
            tiers_row = conn.execute("SELECT solde FROM clients WHERE id=?", (self.bon_data["client_id"],)).fetchone()
        conn.close()
        self.solde_tiers_actuel = tiers_row["solde"] if tiers_row else 0

        self._build()
        self._charger_lignes()
        center_window(self, 900, 750)
    def refresh_produits(self):
        """✅ Rafraîchit la liste des produits dans le combobox pour BonEditDialog"""
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                               prix_achat, prix_vente, barcode,
                               prix_detail, prix_gros, prix_super_gros, prix_special,
                               tva
                        FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        old_selection = self.prod_var.get() if hasattr(self, 'prod_var') else ""
        self.prod_map = {}
        new_prod_list = []
        
        for r in prods:
            key = f"{r['code']} - {r['designation']}"
            self.prod_map[key] = dict(r)
            new_prod_list.append(key)
        
        # Mettre à jour la combobox des produits
        self._update_combobox_produits(new_prod_list, old_selection)
        
        if old_selection in self.prod_map:
            p = self.prod_map[old_selection]
            px = p["prix_achat"] if self.bon_type == "achat" else p["prix_vente"]
            self.prix_var.set(str(px))
        elif new_prod_list:
            self.prod_var.set(new_prod_list[0])
    
    def _update_combobox_produits(self, new_prod_list, old_selection):
        """Met à jour la combobox des produits"""
        for child in self.winfo_children():
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_children'):
                        for grandchild in subchild.winfo_children():
                            if isinstance(grandchild, ttk.Combobox):
                                if grandchild['values'] and len(grandchild['values']) > 0:
                                    if hasattr(self, 'prod_var') and grandchild.cget('textvariable') == str(self.prod_var):
                                        grandchild['values'] = new_prod_list
                                        if old_selection in new_prod_list:
                                            self.prod_var.set(old_selection)
                                        elif new_prod_list:
                                            self.prod_var.set(new_prod_list[0])
                                        return
    def _build(self):
        # ========== EN-TÊTE PRINCIPAL ==========
        top = tk.Frame(self, bg=CLR_CARD, padx=15, pady=12)
        top.pack(fill="x", padx=15, pady=(15,5))

        # Ligne 1: Numéro, Date, Statut, Total actuel
        lbl(top, "Numéro:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4, pady=3)

        self.num_var = tk.StringVar(value=self.bon_data["numero"])
        entry(top, width=18, textvariable=self.num_var).grid(row=0, column=1, padx=8, pady=3)

        lbl(top, "Date:", color=CLR_MUTED).grid(row=0, column=2, sticky="w", padx=4)
        self.date_var = tk.StringVar(value=self.bon_data["date_bon"])
        DateEntry(top, self.date_var, width=12).grid(row=0, column=3, padx=8)

        lbl(top, "Statut:", color=CLR_MUTED).grid(row=0, column=4, sticky="w", padx=4)
        statut_color = CLR_GREEN if self.bon_data["statut"] == "Validé" else CLR_RED
        tk.Label(top, text=self.bon_data["statut"], bg=CLR_CARD, fg=statut_color,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=5, sticky="w", padx=8)

        lbl(top, "Total actuel:", color=CLR_MUTED).grid(row=0, column=6, sticky="w", padx=(20,4))
        tk.Label(top, text=f"{self.bon_data['total']:,.2f} DA", bg=CLR_CARD, fg=CLR_GREEN,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=7, sticky="w", padx=8)

        # Ligne 2: Fournisseur/Client + Solde actuel
        tiers_label = "Fournisseur:" if self.bon_type == "achat" else "Client:"
        lbl(top, tiers_label, color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=3)
        
        conn = get_conn()
        if self.bon_type == "achat":
            tiers = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            tiers_id = self.bon_data["fournisseur_id"]
        else:
            tiers = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
            tiers_id = self.bon_data["client_id"]
        conn.close()
        
        self.tiers_map = {r["nom"]: r["id"] for r in tiers}
        self.tiers_reverse = {r["id"]: r["nom"] for r in tiers}
        self.tiers_var = tk.StringVar(value=self.tiers_reverse.get(tiers_id, ""))
        cb = combo(top, list(self.tiers_map.keys()), width=22, textvariable=self.tiers_var)
        cb.grid(row=1, column=1, padx=8, pady=3)

        lbl(top, "Solde actuel:", color=CLR_MUTED).grid(row=1, column=2, sticky="w", padx=(20,4))
        solde_color = CLR_RED if self.solde_tiers_actuel < 0 else CLR_TEXT
        tk.Label(top, text=f"{self.solde_tiers_actuel:,.2f} DA", bg=CLR_CARD, fg=solde_color,
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=3, sticky="w", padx=8)

        # ========== INFOS SPÉCIFIQUES ACHAT ==========
        if self.bon_type == "achat":
            line3 = tk.Frame(self, bg=CLR_CARD, padx=15, pady=8)
            line3.pack(fill="x", padx=15, pady=(0,5))

            lbl(line3, "📅 Date livraison:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4)
            self.date_livraison_var = tk.StringVar(value=self.bon_data.get("date_livraison") or "")
            entry(line3, width=14, textvariable=self.date_livraison_var).grid(row=0, column=1, padx=8)

            lbl(line3, "📄 N° Facture Fourn.:", color=CLR_MUTED).grid(row=0, column=2, sticky="w", padx=(20,4))
            self.num_facture_fournisseur_var = tk.StringVar(value=self.bon_data.get("num_facture_fournisseur") or "")
            entry(line3, width=18, textvariable=self.num_facture_fournisseur_var).grid(row=0, column=3, padx=8)

            lbl(line3, "🚚 N° BL Fournisseur:", color=CLR_MUTED).grid(row=0, column=4, sticky="w", padx=(20,4))
            self.num_bl_fournisseur_var = tk.StringVar(value=self.bon_data.get("num_bl_fournisseur") or "")
            entry(line3, width=18, textvariable=self.num_bl_fournisseur_var).grid(row=0, column=5, padx=8)

            lbl(line3, "Ancien solde:", color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=(6,0))
            tk.Label(line3, text=f"{self.bon_data.get('ancien_solde', 0):,.2f} DA", bg=CLR_CARD, fg=CLR_ORANGE,
                     font=("Segoe UI", 9, "bold")).grid(row=1, column=1, sticky="w", padx=8, pady=(6,0))

            lbl(line3, "Nouveau solde (au moment du bon):", color=CLR_MUTED).grid(row=1, column=2, sticky="w", padx=(20,4), pady=(6,0))
            tk.Label(line3, text=f"{self.bon_data.get('nouveau_solde', 0):,.2f} DA", bg=CLR_CARD, fg=CLR_GREEN,
                     font=("Segoe UI", 9, "bold")).grid(row=1, column=3, sticky="w", padx=8, pady=(6,0))

        mid = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        mid.pack(fill="x")
        
        lbl(mid, "Produit:", color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=4)
        
        conn = get_conn()
        prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                               prix_achat, prix_vente, barcode,
                               prix_detail, prix_gros, prix_super_gros, prix_special,
                               tva  -- ✅ AJOUTER LA TVA ICI
                        FROM produits ORDER BY designation""").fetchall()
        conn.close()
        self.prod_map = {f"{r['code']} - {r['designation']}": r for r in prods}
        self.prod_var = tk.StringVar()
        pcb = combo(mid, list(self.prod_map.keys()), width=30, textvariable=self.prod_var)
        pcb.grid(row=0, column=1, padx=8)
        # ✅ AJOUT DU BOUTON RAFRAÎCHIR
        btn_refresh = tk.Button(mid, text="🔄", command=self.refresh_produits,
                                bg=CLR_ACCENT, fg="white", relief="flat",
                                font=("Segoe UI", 10, "bold"), padx=6, pady=2,
                                cursor="hand2", width=3)
        btn_refresh.grid(row=0, column=2, padx=2, pady=2)

        self.prod_var.trace_add("write", self._on_prod_change)


        lbl(mid, "Code Barre:", color=CLR_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.barcode_var = tk.StringVar()
        self.barcode_entry = entry(mid, width=18, textvariable=self.barcode_var)
        self.barcode_entry.grid(row=1, column=1, padx=8, pady=4)
        self.barcode_entry.bind("<Return>", lambda e: self._search_prod_by_barcode())
        tk.Button(mid, text="🔎 Chercher", width=10, command=self._search_prod_by_barcode,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2").grid(row=1, column=2, padx=8, pady=4)

        lbl(mid, "Qté:", color=CLR_MUTED).grid(row=0, column=2, padx=4)
        self.qty_var = tk.StringVar(value="1")
        entry(mid, width=8, textvariable=self.qty_var).grid(row=0, column=3, padx=4)

        lbl(mid, "Prix:", color=CLR_MUTED).grid(row=0, column=4, padx=4)
        self.prix_var = tk.StringVar()
        entry(mid, width=10, textvariable=self.prix_var).grid(row=0, column=5, padx=4)

        tk.Button(mid, text="➕ Ajouter ligne", command=self.add_ligne, 
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=5, 
                  cursor="hand2").grid(row=0, column=6, padx=10)

        if self.prod_map:
            self.prod_var.set(list(self.prod_map.keys())[0])

        cols = ["Code", "Produit", "Qté", "Qté Carton", "Unité", "Prix Unit.", "TVA", "Total HT", "Total TTC"]
        widths = [80, 180, 60, 70, 60, 80, 60, 90, 110]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=15, pady=10)

        total_frame = tk.Frame(self, bg=CLR_BG, padx=15, pady=5)
        total_frame.pack(fill="x")
        self.total_var = tk.StringVar(value="Total: 0.00 DA")
        tk.Label(total_frame, textvariable=self.total_var, bg=CLR_BG, fg=CLR_GREEN, font=("Segoe UI", 14, "bold")).pack(side="right", padx=10)

        action_frame = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        action_frame.pack(fill="x", side="bottom")
        
        tk.Button(action_frame, text="✏ Modifier ligne", command=self.edit_ligne,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(action_frame, text="💵 Modifier Prix", command=self.modifier_prix_ligne,
                bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(action_frame, text="🗑 Supprimer ligne", command=self.remove_ligne,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)

        tk.Button(action_frame, text="✅ VALIDER LES MODIFICATIONS", command=self.save,
                  bg=CLR_GREEN, fg="white", relief="flat", 
                  font=("Segoe UI", 10, "bold"),
                  padx=20, pady=6, cursor="hand2").pack(side="left", padx=20)
        
        tk.Button(action_frame, text="❌ ANNULER", command=self.destroy,
                  bg=CLR_RED, fg="white", relief="flat", 
                  font=("Segoe UI", 10, "bold"),
                  padx=14, pady=6, cursor="hand2").pack(side="left", padx=4)
    def modifier_prix_ligne(self):
        """Modifier le prix unitaire d'une ligne existante"""
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

        ligne["prix"] = nouveau_prix
        ligne["total_ht"] = ligne["quantite"] * nouveau_prix   # quantite = quantité en unité de base ici
        ligne["total"] = ligne["total_ht"]

        tva_taux = ligne.get("tva", 0)
        ligne["total_tva"] = ligne["total_ht"] * tva_taux / 100
        ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]

        self._refresh_tree()
        messagebox.showinfo("Succès", f"✅ Prix mis à jour: {nouveau_prix:.2f} DA")
    def _charger_lignes(self):
        for ligne in self.lignes_originales:
            prod_info = None
            designation_key = None
            for key, val in self.prod_map.items():
                if val["id"] == ligne["produit_id"]:
                    prod_info = val
                    designation_key = key
                    break
            if not prod_info:
                continue
            try:
                facteur = float(prod_info["facteur_conversion"]) if prod_info["facteur_conversion"] else 1
            except (KeyError, IndexError, TypeError):
                facteur = 1

            # ✅ Récupérer le taux TVA réel de la ligne (ou du produit à défaut)
            tva_ligne = ligne["tva_taux"] if "tva_taux" in ligne.keys() and ligne["tva_taux"] is not None else float(prod_info["tva"] or 0)

            self.lignes.append({
                "produit_id": ligne["produit_id"],
                "designation": designation_key,
                "code": prod_info["code"] if prod_info["code"] else "",
                "unite": prod_info["unite"] if prod_info["unite"] else "Pcs",
                "barcode": prod_info["barcode"] if prod_info["barcode"] else "",
                "quantite": ligne["quantite"],
                "facteur": facteur,
                "prix": ligne["prix_unitaire"],
                "total": ligne["total"],
                "tva": tva_ligne,   # ✅ ajouté
            })
        self._refresh_tree()
    
    def _on_prod_change(self, *a):
        key = self.prod_var.get()
        if key in self.prod_map:
            p = self.prod_map[key]
            px = p["prix_achat"] if self.bon_type == "achat" else p["prix_vente"]
            self.prix_var.set(str(px))

    def _search_prod_by_barcode(self):
        raw = self.barcode_var.get().strip()
        if not raw:
            messagebox.showwarning("Recherche code-barre", "Entrez un code-barre à rechercher")
            return
        normalized = normalize_barcode_input(raw)
        if not normalized:
            messagebox.showwarning("Recherche code-barre", "Code-barre invalide après normalisation")
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
            px = produit['prix_achat'] if self.bon_type == 'achat' else produit['prix_vente']
            self.prix_var.set(str(px))
            self.qty_var.set('1')
            self.remise_produit_var.set("0")  # ✅ Réinitialiser la remise
            self.barcode_var.set('')
            messagebox.showinfo("Produit trouvé", f"Produit trouvé: {produit['designation']}")
        else:
            messagebox.showinfo("Non trouvé", f"Aucun produit trouvé pour: {normalized}")

    def edit_ligne(self):
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
        dlg.resizable(False, True)
        center_window(dlg, 400, 300)
        
        main_frame = tk.Frame(dlg, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏️ Modifier la quantité", 12, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # Informations du produit
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=5)
        
        facteur = ligne.get("facteur", 1)
        qte_affichee = ligne["quantite"] / facteur if facteur else ligne["quantite"]
        
        lbl(info_frame, f"Produit: {ligne['designation']}", 10, True, CLR_TEXT).pack(anchor="w")
        lbl(info_frame, f"Quantité actuelle: {qte_affichee:.2f} {ligne.get('unite', 'Pcs')}", 9, False, CLR_MUTED).pack(anchor="w")
        lbl(info_frame, f"Prix unitaire: {ligne['prix']:.2f} DA", 9, False, CLR_MUTED).pack(anchor="w")
        if ligne.get("remise_produit", 0) > 0:
            lbl(info_frame, f"Remise: {ligne['remise_produit']:.0f}%", 9, False, CLR_ORANGE).pack(anchor="w")
        
        # Champ de saisie
        input_frame = tk.Frame(main_frame, bg=CLR_BG)
        input_frame.pack(fill="x", pady=10)
        
        lbl(input_frame, "Nouvelle quantité:", 9, False, CLR_MUTED).pack(side="left", padx=5)
        new_qty_var = tk.StringVar(value=str(qte_affichee))
        entry_qty = entry(input_frame, width=12, textvariable=new_qty_var, font=("Segoe UI", 11, "bold"))
        entry_qty.pack(side="left", padx=10)
        entry_qty.focus_set()
        entry_qty.select_range(0, tk.END)
        
        # ✅ Message de statut
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
            ligne["quantite"] = nouvelle_qty_base
            ligne["total_ht"] = nouvelle_qty_base * ligne["prix"]
            ligne["total"] = ligne["total_ht"]
            
            tva_taux = ligne.get("tva", 0)
            ligne["total_tva"] = ligne["total_ht"] * tva_taux / 100
            ligne["total_ttc"] = ligne["total_ht"] + ligne["total_tva"]
            
            if ligne.get("remise_produit", 0) > 0:
                ligne["prix_remise"] = ligne["prix"] * (1 - ligne["remise_produit"] / 100)
                ligne["total_ht"] = nouvelle_qty_base * ligne["prix_remise"]
            
            # ✅ Rafraîchir AVANT de fermer
            self._refresh_tree()
            
            # ✅ Message de succès
            status_var.set(f"✅ Quantité mise à jour: {nouvelle_qty:.2f}")
            status_label.config(fg=CLR_GREEN)
            
            # ✅ Fermer après un délai
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
    
    def add_ligne(self):
        key = self.prod_var.get()
        if key not in self.prod_map:
            messagebox.showerror("Erreur", "Veuillez sélectionner un produit")
            return
        try:
            qty = float(self.qty_var.get())
            prix = float(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité et prix doivent être des nombres")
            return
        if qty <= 0:
            messagebox.showerror("Erreur", "La quantité doit être supérieure à 0")
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Le prix doit être supérieur à 0")
            return

        prod = self.prod_map[key]
        facteur = float(prod["facteur_conversion"]) if prod["facteur_conversion"] else 1.0
        
        # ✅ CORRECTION : Utiliser l'indexation directe pour sqlite3.Row
        tva_taux = float(prod["tva"] or 0)
        barcode = prod["barcode"] if prod["barcode"] else ""
        
        quantite_base = qty * facteur
        total_ht = quantite_base * prix
        total_tva = total_ht * tva_taux / 100
        total_ttc = total_ht + total_tva

        # ✅ VÉRIFIER SI LE PRODUIT EXISTE DÉJÀ
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                reponse = messagebox.askyesno(
                    "Produit existant",
                    f"Le produit '{key}' existe déjà dans le bon.\n"
                    f"Quantité actuelle: {ligne['quantite'] / ligne['facteur']:.2f}\n"
                    f"Nouvelle quantité: {qty:.2f}\n\n"
                    f"Voulez-vous cumuler les quantités ?"
                )
                if reponse:
                    ligne["quantite"] += quantite_base
                    ligne["total_ht"] += total_ht
                    ligne["total_tva"] += total_tva
                    ligne["total_ttc"] += total_ttc
                    ligne["total"] = ligne["total_ht"]
                    ligne["tva"] = tva_taux
                    messagebox.showinfo("Succès", 
                        f"Quantité mise à jour: {ligne['quantite'] / ligne['facteur']:.2f}")
                else:
                    messagebox.showinfo("Info", "Ligne non ajoutée")
                self._refresh_tree()
                self.qty_var.set("1")
                self.prix_var.set("")
                return

        # ✅ NOUVEAU PRODUIT - Utiliser l'indexation directe partout
        self.lignes.append({
            "produit_id": prod["id"],
            "designation": key,
            "code": prod["code"],
            "unite": prod["unite"] or "Pcs",
            "barcode": barcode,  # ✅ Déjà récupéré avec l'indexation directe
            "quantite": quantite_base,
            "facteur": facteur,
            "prix": prix,
            "total_ht": total_ht,
            "tva": tva_taux,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
            "total": total_ht,
        })
        self._refresh_tree()
        self.qty_var.set("1")
        self.prix_var.set("")
        messagebox.showinfo("Succès", "Ligne ajoutée avec succès")
    
    def remove_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne à supprimer")
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_tree()
        messagebox.showinfo("Succès", "Ligne supprimée")
    
    # Dans _refresh_tree() de BonDialog et BonEditDialog (vers ligne 2760)
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        total_ht = 0
        total_tva = 0
        total_ttc = 0

        for i, l in enumerate(self.lignes):
            facteur = l.get("facteur", 1) or 1
            qte_carton = l["quantite"] / facteur if facteur else l["quantite"]
            
            # ✅ Afficher la quantité avec les cartons
            qty_text = f"{l['quantite']:.2f} ({qte_carton:.2f} cartons)" if facteur > 1 else f"{l['quantite']:.2f}"
            
            tva_taux = l.get("tva", 19)
            ht_ligne = l["total"]
            tva_ligne = ht_ligne * tva_taux / 100
            ttc_ligne = ht_ligne + tva_ligne
            
            self.tree.insert("", "end", iid=str(i),
                values=(
                    l.get("code", ""),
                    l["designation"],
                    qty_text,  # ✅ Quantité avec cartons
                    f"{qte_carton:.2f}",  # ✅ Garder la colonne Qté Carton séparée
                    l.get("unite", "Pcs"),
                    f"{l['prix']:.2f}",
                    f"{tva_taux:.0f}%",
                    f"{ht_ligne:.2f}",
                    f"{ttc_ligne:.2f}"
                ))
            
            total_ht += ht_ligne
            total_tva += tva_ligne
            total_ttc += ttc_ligne

        self.total_var.set(f"Total HT: {total_ht:,.2f} DA  |  TVA: {total_tva:,.2f} DA  |  TTC: {total_ttc:,.2f} DA")
    
    def save(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez au moins une ligne")
            return
        tiers_nom = self.tiers_var.get()
        if tiers_nom not in self.tiers_map:
            messagebox.showerror("Erreur", "Sélectionnez un fournisseur/client")
            return
        tiers_id = self.tiers_map[tiers_nom]
        total = sum(l["total"] for l in self.lignes)
        dt = self.date_var.get()
        
        # ✅ Récupérer le nouveau numéro
        nouveau_numero = self.num_var.get().strip()
        if not nouveau_numero:
            messagebox.showerror("Erreur", "Le numéro ne peut pas être vide")
            return
        
        # ✅ Vérifier que le numéro n'est pas déjà utilisé (sauf par ce bon)
        conn_check = get_conn()
        table = "bons_achat" if self.bon_type == "achat" else "bons_vente"
        existing = conn_check.execute(
            f"SELECT id FROM {table} WHERE numero = ? AND id != ?",
            (nouveau_numero, self.bon_id)
        ).fetchone()
        conn_check.close()
        
        if existing:
            messagebox.showerror(
                "Numéro déjà utilisé",
                f"Le numéro '{nouveau_numero}' est déjà utilisé par un autre bon.\n"
                "Veuillez choisir un autre numéro."
            )
            return
        
        conn = get_conn()
        try:
            if self.bon_type == "achat":
                if self.bon_data["statut"] != "Annulé":
                    anciennes_lignes = conn.execute(
                        "SELECT * FROM lignes_achat WHERE bon_id=?", (self.bon_id,)
                    ).fetchall()
                    # ✅ CORRECTION : on annule l'ancien bon avec la même fonction
                    # que la suppression/annulation (inverser_stock_achat), qui retire
                    # le coût EXACT du lot acheté, au lieu de la formule "sortie de
                    # vente" (PMP inchangé) suivie d'un recalcul manuel du PMP qui la
                    # contredisait. Les 3 écrans (édition, suppression, annulation)
                    # produisent maintenant le même résultat.
                    inverser_stock_achat(
                        conn, anciennes_lignes,
                        document_type="bon_achat", document_id=self.bon_id,
                        motif="Modification du bon : reprise de l'ancien contenu",
                    )
                    conn.execute(
                        "UPDATE fournisseurs SET solde = solde - ? WHERE id=?",
                        (self.bon_data["total"], self.bon_data["fournisseur_id"])
                    )
                conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (self.bon_id,))
                
                # ✅ AJOUTER numero=? DANS L'UPDATE
                conn.execute(
                    """UPDATE bons_achat 
                    SET numero=?, date_bon=?, fournisseur_id=?, total=?, 
                        date_livraison=?, num_facture_fournisseur=?, num_bl_fournisseur=?
                    WHERE id=?""",
                    (nouveau_numero, dt, tiers_id, total,
                    self.date_livraison_var.get() or None,
                    self.num_facture_fournisseur_var.get() or None,
                    self.num_bl_fournisseur_var.get() or None,
                    self.bon_id)
                )
                for l in self.lignes:
                    tva_taux = float(l.get("tva", 0))
                    ht_l = l["total"]
                    tva_l = ht_l * tva_taux / 100
                    ttc_l = ht_l + tva_l

                    conn.execute(
                        """INSERT INTO lignes_achat
                        (bon_id, produit_id, quantite, prix_unitaire, total, total_ht, tva_taux, total_ttc)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (self.bon_id, l["produit_id"], l["quantite"], l["prix"], l["total"], ht_l, tva_taux, ttc_l)
                    )
                    # PMP + stock + prix d'achat + journal des mouvements (core.py)
                    nouveau_pmp, nouveau_cout = entree_stock_achat(
                        conn, l["produit_id"], l["quantite"], l["prix"],
                        document_type="bon_achat", document_id=self.bon_id,
                        date_document=dt,
                        motif="Modification du bon : nouveau contenu",
                    )
                    conn.execute(
                        """INSERT INTO historique_prix
                        (produit_id, date_achat, quantite, prix_unitaire, prix_moyen_apres)
                        VALUES(?,?,?,?,?)""",
                        (l["produit_id"], dt, l["quantite"], l["prix"], nouveau_pmp)
                    )
                conn.execute(
                    "UPDATE fournisseurs SET solde = solde + ? WHERE id=?", (total, tiers_id)
                )
            else:
                # Vérification du stock : on alerte mais on ne bloque plus la modification
                alertes = []
                for l in self.lignes:
                    stk = conn.execute(
                        "SELECT stock_actuel FROM produits WHERE id=?", (l["produit_id"],)
                    ).fetchone()
                    ancienne_qty = sum(
                        lq["quantite"] for lq in self.lignes_originales
                        if lq["produit_id"] == l["produit_id"]
                    )
                    stock_reel = (stk["stock_actuel"] if stk else 0) + ancienne_qty
                    if stock_reel < l["quantite"]:
                        alertes.append(
                            f"⚠️ {l['designation']}: Disponible={stock_reel:.2f}, "
                            f"Demandé={l['quantite']:.2f} → Nouveau stock={stock_reel - l['quantite']:.2f}"
                        )
                if alertes:
                    messagebox.showwarning(
                        "⚠️ ALERTE STOCK INSUFFISANT",
                        "Les produits suivants ont un stock insuffisant :\n\n" +
                        "\n".join(alertes) +
                        "\n\n➡ Le bon sera quand même modifié (le stock peut devenir négatif)."
                    )
                if self.bon_data["statut"] != "Annulé":
                    anciennes_lignes = conn.execute(
                        "SELECT * FROM lignes_vente WHERE bon_id=?", (self.bon_id,)
                    ).fetchall()
                    for l in anciennes_lignes:
                        # ✅ CORRECTION : réintégrer le stock au PMP courant (pas au prix de vente)
                        # et ajuster cout_total_stock en conséquence
                        entree_stock_annulation_vente(
                            conn, l["produit_id"], l["quantite"],
                            document_type="bon_vente", document_id=self.bon_id,
                            motif="Modification du bon : reprise de l'ancien contenu",
                        )
                    conn.execute(
                        "UPDATE clients SET solde = solde - ? WHERE id=?",
                        (self.bon_data["total"], self.bon_data["client_id"])
                    )
                conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (self.bon_id,))
                
                # ✅ AJOUTER numero=? DANS L'UPDATE
                conn.execute(
                    "UPDATE bons_vente SET numero=?, date_bon=?, client_id=?, total=? WHERE id=?",
                    (nouveau_numero, dt, tiers_id, total, self.bon_id)
                )
                for l in self.lignes:
                    conn.execute(
                        """INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total)
                        VALUES(?,?,?,?,?)""",
                        (self.bon_id, l["produit_id"], l["quantite"], l["prix"], l["total"])
                    )
                    # ✅ CORRECTION : sortie de stock avec ajustement du cout_total_stock
                    # AVANT de décrémenter stock_actuel (sinon cout_total_stock ne bouge jamais)
                    recalculer_cout_stock_apres_sortie(
                        conn, l["produit_id"], l["quantite"],
                        type_mouvement="VENTE", document_type="bon_vente",
                        document_id=self.bon_id, date_document=dt,
                        motif="Modification du bon : nouveau contenu",
                    )
                   
                conn.execute(
                    "UPDATE clients SET solde = solde + ? WHERE id=?", (total, tiers_id)
                )
            conn.commit()
            messagebox.showinfo("Succès", "Bon modifié avec succès !")
            self.destroy()
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "numero" in str(e):
                messagebox.showerror(
                    "Erreur",
                    f"Le numéro '{nouveau_numero}' existe déjà.\n"
                    "Veuillez choisir un autre numéro."
                )
            else:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            conn.rollback()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {str(ex)}")
        finally:
            conn.close()


# ========== DIALOGUE DÉTAIL BON ==========