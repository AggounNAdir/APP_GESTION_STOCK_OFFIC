from modules.core import *
from api import princing

class VenteComptoirDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🛒 CAISSE ENREGISTREUSE - Vente Comptoir")
        self.configure(bg=CLR_BG)
        self.geometry("1400x700")
        self.minsize(1200, 700)
        center_window(self, 1400, 700)
        
        # ✅ Initialiser toutes les variables AVANT _build()
        self.lignes = []
        self.montant_recu = 0
        self.monnaie = 0
        self.total_avant_remise = 0
        
        # ✅ Variables tkinter
        self.prix_var = tk.StringVar()
        self.prod_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        self.prix_info_var = tk.StringVar(value="")   # origine du prix affiché
        self._dernier_prix_propose = ""               # pour détecter une saisie manuelle
        self.qty_var.trace_add("write", self._on_qty_change)
        self.client_nom = tk.StringVar(value="COMPTOIR")
        self.code_barre = tk.StringVar()
        self.total_var = tk.StringVar(value="0.00 DA")
        self.montant_recu_var = tk.StringVar(value="0")
        self.monnaie_var = tk.StringVar(value="0.00 DA")
        
        # ✅ Maps et listes
        self.prod_map = {}
        self.prod_list = []
        self.clients_map = {}
        
        self._build()
        self.after(100, lambda: self.code_barre_entry.focus())
    
    def _build(self):
        # ============================================================
        # 1. HEADER
        # ============================================================
        header = tk.Frame(self, bg=CLR_CARD, height=80)
        header.pack(fill="x", padx=10, pady=(10,5))
        header.pack_propagate(False)
        
        # Titre à gauche
        title_frame = tk.Frame(header, bg=CLR_CARD)
        title_frame.pack(side="left", fill="y", padx=15)
        lbl(title_frame, "🏪 CAISSE ENREGISTREUSE", 18, True, color=CLR_GREEN).pack(anchor="w")
        lbl(title_frame, "Mode Vente Comptoir", 9, color=CLR_MUTED).pack(anchor="w")
        
        # Date/Heure à droite
        datetime_frame = tk.Frame(header, bg=CLR_CARD)
        datetime_frame.pack(side="right", padx=15)
        self.date_label = tk.Label(datetime_frame, font=("Segoe UI", 10), bg=CLR_CARD, fg=CLR_TEXT)
        self.date_label.pack()
        self.time_label = tk.Label(datetime_frame, font=("Segoe UI", 16, "bold"), bg=CLR_CARD, fg=CLR_ACCENT)
        self.time_label.pack()
        self.update_datetime()
        
        # Client (à droite avant la date)
        client_frame = tk.Frame(header, bg=CLR_CARD)
        client_frame.pack(side="right", padx=15)
        lbl(client_frame, "Client:", color=CLR_MUTED, size=10).pack(side="left")
        
        self.client_combo = combo(client_frame, ["COMPTOIR"], width=18, textvariable=self.client_nom)
        self.client_combo.pack(side="left", padx=5)
        self.client_combo.bind("<<ComboboxSelected>>", self._on_client_change)
        
        tk.Button(client_frame, text="+ Client", command=self.creer_client_rapide,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=8, pady=2, cursor="hand2").pack(side="left", padx=5)
        
        self.charger_clients()
        
        # ============================================================
        # 2. CONTENEUR PRINCIPAL (3 colonnes)
        # ============================================================
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configuration des colonnes avec des poids corrects
        main_container.grid_columnconfigure(0, weight=1)   # Panneau gauche
        main_container.grid_columnconfigure(1, weight=2)   # Panneau central
        main_container.grid_columnconfigure(2, weight=1)   # Panneau droit
        main_container.grid_rowconfigure(0, weight=1)
        
        # ============================================================
        # 3. PANEL GAUCHE - Recherche et saisie
        # ============================================================
        left_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        
        # --- Titre ---
        lbl(left_panel, "🔍 RECHERCHE", 12, True, color=CLR_ACCENT).pack(anchor="w", pady=(0,10))
        
        # --- Code barre ---
        scan_frame = tk.Frame(left_panel, bg=CLR_CARD)
        scan_frame.pack(fill="x", pady=5)
        lbl(scan_frame, "Code barre:", color=CLR_MUTED, size=9).pack(side="left")
        
        self.code_barre_entry = tk.Entry(scan_frame, width=20, textvariable=self.code_barre,
                                         bg=CLR_INPUT, fg=CLR_TEXT, font=("Segoe UI", 11),
                                         relief="flat", highlightthickness=1)
        self.code_barre_entry.pack(side="left", padx=8)
        self.code_barre_entry.bind("<Return>", lambda e: self.recherche_par_code())
        
        tk.Button(scan_frame, text="Chercher", command=self.recherche_par_code,
                  bg=CLR_ACCENT, fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=10).pack(side="left")
        
        # --- Sélection produit ---
        lbl(left_panel, "Sélection produit:", color=CLR_MUTED, size=9).pack(anchor="w", pady=(15,5))
        
        self.charger_produits()
        
        self.prod_combo = combo(left_panel, self.prod_list, width=30, textvariable=self.prod_var)
        self.prod_combo.pack(fill="x", pady=5)
        self.prod_combo.bind("<<ComboboxSelected>>", self.on_produit_selectionne)
        
        # --- Quantité et Prix sur une ligne ---
        qty_frame = tk.Frame(left_panel, bg=CLR_CARD)
        qty_frame.pack(fill="x", pady=8)
        
        lbl(qty_frame, "Qté:", color=CLR_MUTED, size=9).pack(side="left", padx=2)
        entry(qty_frame, width=8, textvariable=self.qty_var, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        lbl(qty_frame, "Prix:", color=CLR_MUTED, size=9).pack(side="left", padx=(15,2))
        entry(qty_frame, width=10, textvariable=self.prix_var, font=("Segoe UI", 11)).pack(side="left", padx=5)

        tk.Label(left_panel, textvariable=self.prix_info_var, bg=CLR_CARD, fg=CLR_MUTED,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=4)
        
        # --- Boutons ---
        btn_frame = tk.Frame(left_panel, bg=CLR_CARD)
        btn_frame.pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="➕ AJOUTER", command=self.ajouter_ligne,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)
        
        tk.Button(btn_frame, text="🔄 Rafraîchir", command=self.charger_produits,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)
        
        # ============================================================
        # 4. PANEL CENTRAL - Panier
        # ============================================================
        center_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=5)
                
        # Tableau du panier
        cols = ["Code", "Produit", "Qté", "Prix", "Total"]
        widths = [80, 280, 60, 80, 100]
        tf, self.tree = make_tree(center_panel, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)
        
        # Boutons du panier
        panier_btn_frame = tk.Frame(center_panel, bg=CLR_CARD)
        panier_btn_frame.pack(fill="x", pady=8)
        
        tk.Button(panier_btn_frame, text="🗑 Supprimer", command=self.supprimer_ligne,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        tk.Button(panier_btn_frame, text="🔄 Modifier Qté", command=self.modifier_quantite,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        tk.Button(panier_btn_frame, text="🗑 Vider", command=self.vider_panier,
                  bg=CLR_BORDER, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=3)
        
        # ============================================================
        # 5. PANEL DROIT - Encaissement
        # ============================================================
        right_panel = tk.Frame(main_container, bg=CLR_CARD, padx=12, pady=12)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5,0))
        
        # Total
        total_frame = tk.Frame(right_panel, bg=CLR_CARD)
        total_frame.pack(fill="x", pady=5)
        lbl(total_frame, "TOTAL À PAYER", 10, True, color=CLR_TEXT).pack(side="left")
        tk.Label(total_frame, textvariable=self.total_var, bg=CLR_CARD, 
                 fg=CLR_GREEN, font=("Segoe UI", 20, "bold")).pack(side="right")
        
        # Montant reçu
        recu_frame = tk.Frame(right_panel, bg=CLR_CARD)
        recu_frame.pack(fill="x", pady=8)
        lbl(recu_frame, "Montant reçu:", 9, True).pack(side="left")
        
        self.montant_recu_entry = entry(recu_frame, width=12, textvariable=self.montant_recu_var, 
                                        font=("Segoe UI", 12), justify="right")
        self.montant_recu_entry.pack(side="right", padx=5)
        self.montant_recu_entry.bind("<KeyRelease>", self.calculer_monnaie)
        
        # Monnaie à rendre
        monnaie_frame = tk.Frame(right_panel, bg=CLR_CARD)
        monnaie_frame.pack(fill="x", pady=8)
        lbl(monnaie_frame, "Monnaie à rendre:", 9, True).pack(side="left")
        tk.Label(monnaie_frame, textvariable=self.monnaie_var, bg=CLR_CARD, 
                 fg=CLR_ORANGE, font=("Segoe UI", 14, "bold")).pack(side="right")
        
        # Séparateur
        tk.Frame(right_panel, bg=CLR_BORDER, height=2).pack(fill="x", pady=8)
        
        # Boutons d'action
        tk.Button(right_panel, text="✅ VALIDER", command=self.valider_vente,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=15, pady=10, cursor="hand2").pack(fill="x", pady=5)
        
        tk.Button(right_panel, text="🖨 TICKET", command=self.imprimer_ticket_rapide,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(fill="x", pady=5)
        
        tk.Button(right_panel, text="❌ ANNULER", command=self.destroy,
                  bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=15, pady=8, cursor="hand2").pack(fill="x", pady=5)
    
    def charger_produits(self):
        """Charge/recharge la liste des produits"""
        conn = get_conn()
        try:
            prods = conn.execute("""SELECT id, code, designation, unite, facteur_conversion,
                                   prix_achat, prix_vente, barcode, stock_actuel,
                                   prix_detail, prix_gros, prix_super_gros, prix_special
                            FROM produits WHERE actif = 1 ORDER BY designation""").fetchall()
        finally:
            conn.close()
        
        self.prod_map = {}
        self.prod_list = []
        for r in prods:
            display = f"{r['code']} - {r['designation']} ({r['prix_vente']:.2f} DA)"
            self.prod_map[display] = dict(r)
            self.prod_list.append(display)
        
        if hasattr(self, 'prod_combo'):
            self.prod_combo['values'] = self.prod_list
        
        # Garder la sélection actuelle si possible
        current = self.prod_var.get()
        if current not in self.prod_map and self.prod_list:
            self.prod_var.set(self.prod_list[0])
    
    def update_datetime(self):
        now = datetime.now()
        self.date_label.config(text=now.strftime("%A %d %B %Y").upper())
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.after(1000, self.update_datetime)
    
    def charger_clients(self):
        conn = get_conn()
        try:
            clients = conn.execute(
                "SELECT id, nom FROM clients ORDER BY nom"
            ).fetchall()
        finally:
            conn.close()
        
        self.clients_map = {}
        client_liste = []
        for c in clients:
            self.clients_map[c["nom"]] = c["id"]
            client_liste.append(c["nom"])
        if "COMPTOIR" in self.clients_map:
            client_liste.remove("COMPTOIR")
            client_liste.insert(0, "COMPTOIR")
        self.client_combo['values'] = client_liste
        if client_liste:
            self.client_nom.set(client_liste[0])
    
    def creer_client_rapide(self):
        nom = simpledialog.askstring("Nouveau Client", "Nom du client:", parent=self)
        if nom and nom.strip():
            code_auto = generer_code_unique("CLT", "clients", mode="sequentiel")
            conn = get_conn()
            try:
                conn.execute("""INSERT INTO clients(code, nom, adresse, tel, email, solde) 
                            VALUES(?, ?, ?, ?, ?, ?)""", 
                        (code_auto, nom.strip(), "", "", "", 0))
                conn.commit()
                messagebox.showinfo("Succès", f"Client '{nom}' créé avec le code {code_auto}")
                self.charger_clients()
                self.client_nom.set(nom.strip())
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))
            finally:
                conn.close()
    
    def recherche_par_code(self):
        code = self.code_barre.get().strip()
        if not code:
            return
        normalized = normalize_barcode_input(code)
        conn = get_conn()
        produit = conn.execute(
            "SELECT * FROM produits WHERE (barcode = ? OR code = ?) AND actif = 1",
            (normalized, normalized)
        ).fetchone()
        conn.close()
        if produit:
            for display, p in self.prod_map.items():
                if p["id"] == produit["id"]:
                    self.prod_var.set(display)
                    self.qty_var.set("1")
                    self._proposer_prix()
                    self.code_barre.set("")
                    self.ajouter_ligne()
                    break
        else:
            messagebox.showwarning("Non trouvé", f"Produit non trouvé: {code}")
    
    def on_produit_selectionne(self, event):
        key = self.prod_var.get()
        if key in self.prod_map:
            self._proposer_prix()
    
    # ── PRIX : toute la règle vient de api/princing.py ──────────────────────

    def _client_id(self):
        return getattr(self, "clients_map", {}).get(self.client_nom.get())

    def _qty_panier_base(self, produit_id):
        """Quantité déjà au panier pour ce produit (unités de base)."""
        return sum(l.get("qty_base", 0) for l in self.lignes if l["produit_id"] == produit_id)

    def _resoudre_prix(self, produit_id, qty_base):
        conn = get_conn()
        try:
            return princing.resoudre_prix(
                conn, produit_id, client_id=self._client_id(), quantite=qty_base)
        finally:
            conn.close()

    def _proposer_prix(self):
        """Affiche le prix applicable (prix spécial > palier > niveau du client)."""
        key = self.prod_var.get()
        if key not in self.prod_map:
            return
        prod = self.prod_map[key]
        try:
            qty = parse_decimal(self.qty_var.get())
        except (ValueError, TypeError):
            return          # champ vide / saisie en cours : on garde le prix affiché
        if qty <= 0:
            return
        facteur = float(prod.get("facteur_conversion") or 1)
        qty_base = qty * facteur + self._qty_panier_base(prod["id"])
        res = self._resoudre_prix(prod["id"], qty_base)
        self._dernier_prix_propose = f"{res.prix:.2f}"
        self.prix_var.set(self._dernier_prix_propose)
        self.prix_info_var.set(res.libelle)

    def _on_qty_change(self, *_):
        # Ne réécrit le prix que si le caissier ne l'a pas modifié à la main
        if self.prix_var.get() == self._dernier_prix_propose:
            self._proposer_prix()

    def _on_client_change(self, event=None):
        self._recalculer_panier()
        self._proposer_prix()

    def _recalculer_panier(self):
        """Recalcule les lignes au prix automatique (client, palier). Les prix saisis à la main sont conservés."""
        if not self.lignes:
            return
        conn = get_conn()
        try:
            for l in self.lignes:
                if l.get("prix_auto", True):
                    res = princing.resoudre_prix(
                        conn, l["produit_id"], client_id=self._client_id(),
                        quantite=l.get("qty_base", l["quantite"]))
                    l["prix"] = res.prix
                    l["total"] = l["qty_base"] * l["prix"]
        finally:
            conn.close()
        self._refresh_panier()

    def _confirmer_marge(self, produit_id, prix):
        """Alerte (sans bloquer) si le prix est sous le coût / la marge minimale."""
        conn = get_conn()
        try:
            m = princing.verifier_marge(conn, produit_id, prix)
        finally:
            conn.close()
        if m.ok:
            return True
        return messagebox.askyesno(
            "⚠️ Prix trop bas", f"{m.message}\n\nAjouter quand même cette ligne ?", parent=self)

    def ajouter_ligne(self):
        key = self.prod_var.get()
        if not key or key not in self.prod_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit", parent=self)
            return
        try:
            qty = parse_decimal(self.qty_var.get())
            prix = parse_decimal(self.prix_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Quantité/Prix invalide", parent=self)
            return
        if qty <= 0:
            messagebox.showerror("Erreur", "Quantité > 0", parent=self)
            return
        if prix <= 0:
            messagebox.showerror("Erreur", "Prix > 0", parent=self)
            return
        
        prod = self.prod_map[key]
        
        # Convertir la saisie en unités de stock pour comparaison
        facteur = float(prod.get("facteur_conversion") or 1)
        qty_en_unites = qty * facteur
        stock_en_cartons = prod["stock_actuel"] / facteur if facteur else prod["stock_actuel"]
        
        if qty_en_unites > prod["stock_actuel"]:
            messagebox.showerror(
                "Stock insuffisant",
                f"Stock disponible : {stock_en_cartons:.2f} cartons "
                f"({prod['stock_actuel']:.2f} unités)\n"
                f"Quantité demandée : {qty:.2f} cartons ({qty_en_unites:.2f} unités)",
                parent=self
            )
            return
        
        # Prix saisi à la main ? (différent de celui proposé par le service de prix)
        prix_auto = (f"{prix:.2f}" == self._dernier_prix_propose)

        # Vérifier si le produit est déjà dans le panier
        for ligne in self.lignes:
            if ligne["produit_id"] == prod["id"]:
                if not prix_auto and not self._confirmer_marge(prod["id"], prix):
                    return
                ligne["quantite"] += qty
                ligne["qty_base"] = ligne.get("qty_base", ligne["quantite"]) + qty_en_unites
                if not prix_auto:
                    ligne["prix"] = prix          # nouveau prix saisi à la main
                    ligne["prix_auto"] = False
                elif ligne.get("prix_auto", True):
                    # la quantité totale a changé : le palier peut avoir changé
                    ligne["prix"] = self._resoudre_prix(prod["id"], ligne["qty_base"]).prix
                ligne["total"] = ligne["qty_base"] * ligne["prix"]
                self._refresh_panier()
                self.qty_var.set("1")
                return

        if not self._confirmer_marge(prod["id"], prix):
            return
        total = qty_en_unites * prix
        self.lignes.append({
            "produit_id": prod["id"],
            "code": prod["code"],
            "designation": prod["designation"],
            "quantite": qty,          # quantité affichée (cartons)
            "qty_base": qty_en_unites,  # quantité réelle pour le stock
            "facteur": facteur,
            "prix": prix,
            "prix_auto": prix_auto,
            "total": total
        })
        self._refresh_panier()
        self.qty_var.set("1")
    
    def supprimer_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne", parent=self)
            return
        idx = int(sel[0])
        del self.lignes[idx]
        self._refresh_panier()
    
    def modifier_quantite(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne", parent=self)
            return
        idx = int(sel[0])
        ligne = self.lignes[idx]
        nouvelle_qty = simpledialog.askfloat("Modifier quantité",
                                            f"Quantité: {ligne['quantite']}\nNouvelle valeur:",
                                            initialvalue=ligne['quantite'], parent=self)
        if nouvelle_qty and nouvelle_qty > 0:
            # ✅ Mettre à jour la quantité en unité d'affichage
            facteur = ligne.get("facteur", 1)
            ligne["quantite"] = nouvelle_qty
            ligne["qty_base"] = nouvelle_qty * facteur
            ligne["total"] = ligne["qty_base"] * ligne["prix"]
            self._recalculer_panier()   # palier éventuel + rafraîchissement
    
    def vider_panier(self):
        if self.lignes and messagebox.askyesno("Confirmation", "Vider le panier ?", parent=self):
            self.lignes = []
            self._refresh_panier()
    
    def _refresh_panier(self):
        self.tree.delete(*self.tree.get_children())
        total_brut = 0
        for i, l in enumerate(self.lignes):
            self.tree.insert("", "end", iid=str(i),
                values=(l["code"], l["designation"], f"{l['quantite']:.1f}", 
                    f"{l['prix']:.2f}", f"{l['total']:.2f}"))
            total_brut += l["total"]
        self.total_avant_remise = total_brut
        self.total_var.set(f"{total_brut:,.2f} DA")
        self.calculer_monnaie()
    
    def calculer_monnaie(self, event=None):
        try:
            total_str = self.total_var.get().replace(" DA", "").replace(",", "")
            total = float(total_str)
            recu = parse_decimal(self.montant_recu_var.get() or "0")
            if recu >= total:
                monnaie = recu - total
                self.monnaie_var.set(f"{monnaie:,.2f} DA")
            else:
                self.monnaie_var.set(f"Manque: {total - recu:,.2f} DA")
        except (ValueError, TypeError):
            self.monnaie_var.set("0.00 DA")
    
    def valider_vente(self):
        if not self.lignes:
            messagebox.showerror("Erreur", "Ajoutez des produits", parent=self)
            return
        
        total = self.total_avant_remise
        client_nom = self.client_nom.get()
        
        client_id = self.clients_map.get(client_nom)
        if not client_id:
            messagebox.showerror("Erreur", f"Client '{client_nom}' introuvable", parent=self)
            return
        
        try:
            recu = parse_decimal(self.montant_recu_var.get() or "0")
        except ValueError:
            recu = 0
        
        if recu < total:
            messagebox.showerror(
                "Erreur",
                f"Montant insuffisant!\nTotal: {total:,.2f} DA\nManque: {total-recu:,.2f} DA",
                parent=self
            )
            return
        
        monnaie = recu - total
        if not messagebox.askyesno(
            "Confirmation",
            f"✅ VALIDER ?\n\nClient: {client_nom}\nTotal: {total:,.2f} DA\n"
            f"Reçu: {recu:,.2f} DA\nMonnaie: {monnaie:,.2f} DA",
            parent=self
        ):
            return
        
        num = next_numero_tiers("BV", client_id)
        dt = date.today().strftime("%Y-%m-%d")
        
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO bons_vente(numero, date_bon, client_id, total, statut) VALUES(?,?,?,?,?)",
                (num, dt, client_id, total, "Validé")
            )
            bon_id = conn.execute(
                "SELECT id FROM bons_vente WHERE numero=?", (num,)
            ).fetchone()["id"]
            
            for l in self.lignes:
                facteur_l = float(l.get("facteur", 1) or 1)
                qty_base = l["quantite"] * facteur_l
                
                conn.execute(
                    "INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total) "
                    "VALUES(?,?,?,?,?)",
                    (bon_id, l["produit_id"], qty_base, l["prix"], l["total"])
                )
                # ✅ CORRECTION : réduire le coût du stock (PMP conservé, cout_total_stock ajusté)
                recalculer_cout_stock_apres_sortie(
                    conn, l["produit_id"], qty_base,
                    type_mouvement="VENTE", document_type="bon_vente",
                    document_id=bon_id, date_document=dt,
                    motif="Vente comptoir",
                )
               
            if client_nom != "COMPTOIR":
                conn.execute(
                    "UPDATE clients SET solde = solde + ? WHERE id=?", (total, client_id)
                )
            
            conn.commit()
            self.imprimer_ticket(num, client_nom, total, recu, monnaie)
            messagebox.showinfo(
                "Succès",
                f"✅ Vente enregistrée!\nBon: {num}\nMonnaie: {monnaie:,.2f} DA",
                parent=self
            )
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex), parent=self)
        finally:
            conn.close()
    
    def imprimer_ticket(self, num, client_nom, total, recu, monnaie):
        """Affiche le ticket avec bouton d'impression"""
        
        # ✅ Créer la fenêtre du ticket
        preview = tk.Toplevel(self)
        preview.title(f"TICKET N°{num}")
        preview.configure(bg="white")
        preview.geometry("400x600")
        preview.resizable(False, False)
        
        # ✅ Garder la fenêtre au premier plan
        preview.transient(self)
        preview.grab_set()
        preview.focus_force()
        preview.lift()
        
        # ✅ Centrer
        center_window(preview, 400, 600)
        
        # ✅ Conteneur principal
        main_frame = tk.Frame(preview, bg="white")
        main_frame.pack(fill="both", expand=True)
        
        # ✅ Zone de texte pour le ticket
        text_frame = tk.Frame(main_frame, bg="white")
        text_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        text_widget = tk.Text(text_frame, bg="white", fg="black", 
                            font=("Courier", 10), wrap="none",
                            relief="flat", highlightthickness=0)
        text_widget.pack(side="left", fill="both", expand=True)
        
        # ✅ Scrollbar
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # ✅ Construire le contenu du ticket
        content = []
        content.append("=" * 32)
        content.append("       VOTRE MAGASIN")
        content.append("=" * 32)
        content.append("")
        content.append(f"Ticket: {num}")
        content.append(f"Date  : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        content.append(f"Client: {client_nom}")
        content.append("")
        content.append("-" * 32)
        content.append("")
        
        # ✅ Lignes de produits
        for i, l in enumerate(self.lignes, 1):
            designation = l['designation'][:25]
            qty = l['quantite']
            total_ligne = l['total']
            content.append(f"{i:2d}. {designation}")
            content.append(f"    {qty:6.0f} x {l['prix']:8.2f} = {total_ligne:10.2f} DA")
            content.append("")
        
        content.append("-" * 32)
        content.append("")
        content.append(f"TOTAL À PAYER : {total:>12,.2f} DA")
        content.append(f"Montant reçu   : {recu:>12,.2f} DA")
        content.append(f"Monnaie        : {monnaie:>12,.2f} DA")
        content.append("")
        content.append("-" * 32)
        content.append("")
        content.append("         MERCI DE VOTRE VISITE !")
        content.append("")
        content.append("=" * 32)
        
        # ✅ Insérer le contenu
        text_widget.insert("1.0", "\n".join(content))
        text_widget.config(state="disabled")
        
        # ✅ Boutons en bas
        btn_frame = tk.Frame(main_frame, bg="white", pady=10)
        btn_frame.pack(fill="x", padx=15)
        
        # ✅ Bouton Imprimer
        btn_imprimer = tk.Button(
            btn_frame,
            text="🖨  IMPRIMER",
            command=lambda: self._imprimer_ticket_html(content, num),
            bg=CLR_ACCENT,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief="flat"
        )
        btn_imprimer.pack(side="left", expand=True, fill="x", padx=5)
        
        # ✅ Bouton Fermer
        btn_fermer = tk.Button(
            btn_frame,
            text="✕  FERMER",
            command=lambda: self._fermer_ticket(preview),
            bg=CLR_RED,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            relief="flat"
        )
        btn_fermer.pack(side="left", expand=True, fill="x", padx=5)
        
        # ✅ Focus sur le bouton Imprimer
        btn_imprimer.focus_set()
        
        # ✅ Raccourcis clavier
        preview.bind("<Escape>", lambda e: self._fermer_ticket(preview))
        preview.bind("<Return>", lambda e: self._imprimer_ticket_html(content, num))

    def _imprimer_ticket_html(self, content, num):
        """Imprime le ticket via HTML (ouvre dans le navigateur pour impression)"""
        try:
            # ✅ Construire le contenu HTML
            content_text = "\n".join(content)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Ticket N°{num}</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        font-size: 11pt;
                        padding: 20px;
                        margin: 0;
                        background: white;
                        color: black;
                        max-width: 380px;
                        margin: 0 auto;
                    }}
                    pre {{
                        font-family: 'Courier New', monospace;
                        font-size: 11pt;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        padding: 0;
                    }}
                    @media print {{
                        body {{
                            padding: 10px;
                            margin: 0;
                        }}
                        .no-print {{
                            display: none !important;
                        }}
                    }}
                </style>
            </head>
            <body>
                <pre>{content_text}</pre>
                <div class="no-print" style="text-align:center; margin-top:20px; padding:10px; border-top:1px solid #ccc;">
                    <p style="font-family:Arial; font-size:10px; color:#666;">
                        Utilisez <strong>Ctrl+P</strong> ou <strong>Fichier > Imprimer</strong>
                    </p>
                </div>
                <script>
                    // ✅ Impression automatique après 1 seconde
                    setTimeout(function() {{
                        window.print();
                    }}, 500);
                    
                    // ✅ Fermer la fenêtre après impression ou annulation
                    window.onafterprint = function() {{
                        setTimeout(function() {{
                            window.close();
                        }}, 500);
                    }};
                </script>
            </body>
            </html>
            """
            
            # ✅ Créer un fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.html', 
                delete=False, 
                encoding='utf-8'
            )
            temp_file.write(html_content)
            temp_file.close()
            
            # ✅ Ouvrir dans le navigateur
            webbrowser.open(temp_file.name)
            
            # ✅ Supprimer le fichier après 30 secondes
            self.after(30000, lambda: self._supprimer_fichier_temp(temp_file.name))
            
            # ✅ Message d'information
            messagebox.showinfo(
                "Impression", 
                "🖨️ Le ticket s'ouvre dans votre navigateur.\n\n"
                "➡️ L'impression se lance automatiquement.\n"
                "➡️ Si ce n'est pas le cas, utilisez Ctrl+P.",
                parent=self
            )
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'impression: {str(e)}")

    def _supprimer_fichier_temp(self, filepath):
        """Supprime le fichier temporaire"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except:
            pass

    def _fermer_ticket(self, preview_window):
        """Ferme la fenêtre du ticket et rend le focus à la caisse"""
        preview_window.destroy()
        # ✅ Redonner le focus à la fenêtre principale de la caisse
        self.focus_force()
        self.lift()
        self.code_barre_entry.focus_set()
    
    def imprimer_ticket_rapide(self):
        if not self.lignes:
            messagebox.showwarning("", "Panier vide", parent=self)
            return
        total = sum(l["total"] for l in self.lignes)
        recu = parse_decimal(self.montant_recu_var.get() or "0")
        monnaie = max(0, recu - total)
        self.imprimer_ticket("PREVIEW", self.client_nom.get(), total, recu, monnaie)


# ========== DIALOGUE BON (Achat/Vente) ==========

