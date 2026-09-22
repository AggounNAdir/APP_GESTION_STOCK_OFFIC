from modules.core import *
from modules.paliersdialog import PaliersDialog
from api import princing
from api.stock_journal import enregistrer_mouvement

class ProduitDialog(tk.Toplevel):
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Produit")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.data = data
        self.paliers = []               # paliers de quantité (enregistrés avec le produit)
        self._paliers_modifies = False
        self._build()
        self.update_idletasks()
        center_window(self, self.winfo_width(), self.winfo_height())

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=30, pady=20)
        f.pack()
        
        if not self.data:
            code_auto = generer_code_unique("PROD", "produits", mode="sequentiel")
        else:
            code_auto = self.data["code"]
        
        fields = [
            ("Code *", "code", True),
            ("Code Barre", "barcode", False),
            ("Désignation *", "designation", False),
            ("Unité", "unite", False),
            ("Facteur Conversion (ex: 24 carton)", "facteur_conversion", False),
            ("🏷️ Marque/Fournisseur *", "fournisseur", False),  # ✅ AJOUTÉ
            # Le « Prix Achat » se saisit UNIQUEMENT dans la Grille de Prix ci-dessous
            # (un champ en double, non relié à l'enregistrement, faisait perdre la valeur).
            ("TVA (%)", "tva", False),
            ("Stock actuel", "stock_actuel", False),
            ("Stock minimum (cartons)", "stock_min", False),
        ]
        
        self.vars = {}
        for i, (lbl_text, key, readonly) in enumerate(fields):
            lbl(f, lbl_text, color=CLR_MUTED).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            
            if key == "code" and not self.data:
                v.set(code_auto)
            elif self.data and key in self.data:
                if key == "stock_min":
                    try:
                        facteur = float(self.data["facteur_conversion"] or 1) if self.data["facteur_conversion"] else 1.0
                        v.set(f"{float(self.data[key]) / facteur:.2f}")
                    except Exception:
                        v.set(str(self.data[key]))
                elif self.data[key] is not None:
                    v.set(str(self.data[key]))
            elif key == "facteur_conversion":
                v.set("1")
            elif key == "tva" and not self.data:
                v.set("19")
            elif key == "fournisseur" and not self.data:  # ✅ AJOUTÉ
                v.set("")  # Vide par défaut
            
            # ✅ Pour le champ unité, ajouter une combobox avec les unités courantes (g, kg, L, mL, Pièce, Carton, Paquet, etc.)
            if key == "unite":
                # Récupérer les unités existantes de la base de données
                conn = get_conn()
                unites_db = conn.execute(
                    "SELECT DISTINCT unite FROM produits WHERE unite != '' ORDER BY unite"
                ).fetchall()
                conn.close()
                
                unites_defaut = ["Pièce", "g", "kg", "L", "mL", "Pcs", "Carton", "Paquet", "Bouteille", "Sachet", "Boîte", "Mètre", "Cm"]
                unites_existantes = [u["unite"] for u in unites_db if u["unite"]]
                
                # Combiner sans doublons
                unites_liste = list(dict.fromkeys(unites_defaut + unites_existantes))
                
                cb_unite = combo(f, unites_liste, width=28, textvariable=v)
                cb_unite.grid(row=i, column=1, padx=(10, 0), pady=4)
                
                # Bouton pour ajouter une nouvelle unité personnalisée
                btn_new_unite = tk.Button(
                    f, text="➕", 
                    command=self.ajouter_nouvelle_unite,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                    cursor="hand2"
                )
                btn_new_unite.grid(row=i, column=2, padx=5, pady=4)

            elif key == "fournisseur":
                # Récupérer les marques existantes
                conn = get_conn()
                marques = conn.execute(
                    "SELECT DISTINCT fournisseur FROM produits WHERE fournisseur != '' ORDER BY fournisseur"
                ).fetchall()
                conn.close()
                
                marques_liste = [""] + [m["fournisseur"] for m in marques]
                
                # Utiliser une Combobox au lieu d'un Entry
                cb = combo(f, marques_liste, width=28, textvariable=v)
                cb.grid(row=i, column=1, padx=(10, 0), pady=4)
                
                # Ajouter un bouton pour créer une nouvelle marque
                btn_new_marque = tk.Button(
                    f, text="➕", 
                    command=self.ajouter_nouvelle_marque,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                    cursor="hand2"
                )
                btn_new_marque.grid(row=i, column=2, padx=5, pady=4)
                
            else:
                e = entry(f, width=28, textvariable=v)
                e.grid(row=i, column=1, padx=(10, 0), pady=4)
            
            if key == "code" and not self.data:
                e.config(state="readonly", readonlybackground=CLR_INPUT)
            
            if key == "barcode":
                def on_barcode_change(*args, var=v):
                    raw = var.get()
                    if not raw:
                        return
                    cleaned = re.sub(r"[^A-Za-z0-9\-_\.]", "", raw)
                    cleaned = cleaned.upper()
                    if cleaned != raw:
                        var.trace_remove("write", var.trace_info()[0][1])
                        var.set(cleaned)
                        var.trace_add("write", on_barcode_change)
                v.trace_add("write", on_barcode_change)
            
            self.vars[key] = v
        
        # Prix niveaux (comme avant)
        pnf = prix_niveaux.PrixNiveauxFrame(f, self.vars, self.data)
        pnf.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=8)

        # Paliers de quantité (ouvre un écran dédié ; enregistrés avec la fiche)
        if self.data and self.data.get("id"):
            self.paliers = self._charger_paliers(self.data["id"])
        pal_frame = tk.Frame(f, bg=CLR_BG)
        pal_frame.grid(row=len(fields)+1, column=0, columnspan=3, sticky="ew")
        self.btn_paliers = tk.Button(
            pal_frame, command=self.ouvrir_paliers,
            bg=CLR_ORANGE, fg="white", relief="flat",
            font=("Segoe UI", 9, "bold"), padx=12, pady=5, cursor="hand2")
        self.btn_paliers.pack(side="left")
        self._maj_bouton_paliers()

        if not self.data:
            tk.Button(f, text="🔄 Régénérer", command=self.regenerate_code,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=10, pady=2,
                    cursor="hand2").grid(row=0, column=2, padx=5, pady=4)
        
        bf = tk.Frame(f, bg=CLR_BG)
        bf.grid(row=len(fields)+2, column=0, columnspan=3, pady=15)
        tk.Button(bf, text="💾 Enregistrer", command=self.save,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=14, pady=7,
                cursor="hand2").pack(side="left", padx=6)
        tk.Button(bf, text="Annuler", command=self.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=14, pady=7,
                cursor="hand2").pack(side="left", padx=6)

    # ── Paliers de quantité ─────────────────────────────────────────────────

    def _charger_paliers(self, produit_id):
        conn = get_conn()
        try:
            return princing.lire_paliers(conn, produit_id)
        finally:
            conn.close()

    def _maj_bouton_paliers(self):
        n = len(self.paliers)
        self.btn_paliers.config(
            text=f"📦 Paliers de quantité ({n})" if n else "📦 Paliers de quantité (aucun)")

    def _facteur_courant(self):
        try:
            return parse_decimal(self.vars["facteur_conversion"].get() or 1) or 1
        except ValueError:
            return 1

    def _prix_niveau_saisi(self, niveau):
        """Prix normal saisi dans la grille pour ce niveau (0 si vide) – sert au contrôle."""
        try:
            return parse_decimal(self.vars.get(princing.NIVEAU_COLONNE[niveau]).get() or 0)
        except (ValueError, AttributeError, KeyError):
            return 0.0

    def _cout_saisi(self):
        try:
            return parse_decimal(self.vars["prix_achat"].get() or 0)
        except ValueError:
            return 0.0

    def ouvrir_paliers(self):
        PaliersDialog(
            self,
            self.vars["designation"].get().strip() or "(nouveau produit)",
            self.paliers,
            self._paliers_valides,
            facteur_fn=self._facteur_courant,
            prix_niveau_fn=self._prix_niveau_saisi,
            cout_fn=self._cout_saisi,
        )

    def _paliers_valides(self, paliers):
        self.paliers = princing.normaliser_paliers(paliers)
        self._paliers_modifies = True
        self._maj_bouton_paliers()

    def ajouter_nouvelle_unite(self):
        """Ajouter une nouvelle unité personnalisée"""
        nouvelle_unite = simpledialog.askstring(
            "Nouvelle Unité",
            "Entrez la nouvelle unité (ex: g, kg, L, mL, Pièce, etc.) :",
            parent=self
        )
        if nouvelle_unite and nouvelle_unite.strip():
            unite = nouvelle_unite.strip()
            self.vars["unite"].set(unite)
            messagebox.showinfo("Succès", f"✅ Unité '{unite}' ajoutée avec succès !")

    def ajouter_nouvelle_marque(self):
        """Ajouter une nouvelle marque/fournisseur"""
        nouvelle_marque = simpledialog.askstring(
            "Nouvelle Marque",
            "Entrez le nom de la nouvelle marque/fournisseur :",
            parent=self
        )
        if nouvelle_marque and nouvelle_marque.strip():
            marque = nouvelle_marque.strip().upper()
            # Mettre à jour la combobox
            self.vars["fournisseur"].set(marque)
            messagebox.showinfo("Succès", f"✅ Marque '{marque}' ajoutée avec succès !")
    
    def regenerate_code(self):
        nouveau_code = generer_code_unique("PROD", "produits", mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")

    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        
        # ✅ Validation : Le fournisseur est facultatif, mais vous pouvez le rendre obligatoire
        # if not v.get("fournisseur", ""):
        #     messagebox.showerror("Erreur", "La marque/fournisseur est obligatoire")
        #     return
        
        if not v["code"] or not v["designation"]:
            messagebox.showerror("Erreur", "Code et désignation obligatoires")
            return
        try:
            fc = parse_decimal(v["facteur_conversion"] or 1)
            pa = parse_decimal(v["prix_achat"] or 0)
            tva = parse_decimal(v.get("tva", "19") or "19")
            # Récupérer les 4 niveaux de prix
            prix_sg = parse_decimal(v.get("prix_super_gros", "0") or "0")
            prix_g = parse_decimal(v.get("prix_gros", "0") or "0")
            prix_d = parse_decimal(v.get("prix_detail", "0") or "0")
            prix_sp = parse_decimal(v.get("prix_special", "0") or "0")
            # prix_vente = prix détail par défaut
            pv = princing.prix_vente_defaut(pa, prix_d)
            sa = parse_decimal(v["stock_actuel"] or 0)
            sm_cartons = parse_decimal(v["stock_min"] or 0)
            sm = sm_cartons * fc
            
            # ✅ Récupérer le fournisseur
            fournisseur = v.get("fournisseur", "")
            
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides")
            return

        # ⛔ Aucun prix de vente (niveaux ET paliers) ne doit être inférieur au prix d'achat
        erreurs = princing.prix_sous_le_cout(
            pa,
            {"super_gros": prix_sg, "gros": prix_g, "detail": prix_d, "special": prix_sp},
            self.paliers,
        )
        if erreurs:
            messagebox.showerror(
                "⛔ Prix de vente inférieur au prix d'achat",
                "\n".join(erreurs)
                + "\n\nCorrigez ces prix : le produit n'est pas enregistré.",
                parent=self)
            return

        # ⚠️ Prix Détail vide : la vente retombera sur un prix par défaut (ou 0)
        alerte = princing.avertissement_prix_detail(pa, prix_d)
        if alerte and not messagebox.askyesno(
                "⚠️ Prix Détail vide",
                alerte + "\n\nEnregistrer quand même ?", parent=self):
            return

        conn = get_conn()
        try:
            ancien_stock = None
            if self.data:
                barcode_val = v["barcode"] if v["barcode"] else None
                _r = conn.execute("SELECT stock_actuel FROM produits WHERE id=?",
                                  (self.data["id"],)).fetchone()
                ancien_stock = float(_r[0] or 0) if _r else 0.0
                # ✅ UPDATE avec fournisseur
                conn.execute("""UPDATE produits SET 
                    code=?, barcode=?, designation=?, unite=?,
                    facteur_conversion=?, prix_achat=?, prix_vente=?, tva=?,
                    prix_super_gros=?, prix_gros=?, prix_detail=?, prix_special=?,
                    stock_actuel=?, stock_min=?, fournisseur=? 
                    WHERE id=?""",
                    (v["code"], barcode_val, v["designation"], v["unite"], 
                    fc, pa, pv, tva,
                    prix_sg, prix_g, prix_d, prix_sp, 
                    sa, sm, fournisseur, self.data["id"]))
                produit_id = self.data["id"]
                # Journal : la fiche produit permet de corriger le stock à la main
                if abs(sa - ancien_stock) > 1e-9:
                    enregistrer_mouvement(
                        conn, produit_id, "AJUSTEMENT",
                        stock_avant=ancien_stock, stock_apres=sa,
                        cout_unitaire=pa,
                        motif="Correction du stock depuis la fiche produit",
                    )
            else:
                existing = conn.execute("SELECT id FROM produits WHERE code = ?", (v["code"],)).fetchone()
                if existing:
                    messagebox.showerror("Erreur", 
                        f"Le code '{v['code']}' existe déjà.\n"
                        "Cliquez sur 'Régénérer' pour obtenir un nouveau code.")
                    conn.close()
                    return
                barcode_val = v["barcode"] if v["barcode"] else None
                # ✅ INSERT avec fournisseur
                cur = conn.execute("""INSERT INTO produits(
                    code, barcode, designation, unite,
                    facteur_conversion, prix_achat, prix_vente, tva,
                    prix_super_gros, prix_gros, prix_detail, prix_special,
                    stock_actuel, stock_min, fournisseur)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (v["code"], barcode_val, v["designation"], v["unite"], 
                    fc, pa, pv, tva,
                    prix_sg, prix_g, prix_d, prix_sp, 
                    sa, sm, fournisseur))
                produit_id = cur.lastrowid
                # Journal : stock saisi à la création du produit
                if sa:
                    enregistrer_mouvement(
                        conn, produit_id, "STOCK_INITIAL",
                        stock_avant=0, stock_apres=sa, cout_unitaire=pa,
                        motif="Stock saisi à la création du produit",
                    )
            # Paliers de quantité : seulement si l'utilisateur les a modifiés
            if self._paliers_modifies:
                princing.enregistrer_paliers(conn, produit_id, self.paliers)
            conn.commit()
            messagebox.showinfo("Succès", "Produit enregistré avec succès !")
            self.notifier_toutes_les_fenetres()
            self.destroy()
        except sqlite3.IntegrityError as e:
            if "code" in str(e):
                messagebox.showerror("Erreur", f"Le code '{v['code']}' existe déjà.")
            elif "barcode" in str(e):
                messagebox.showerror("Erreur", f"Le code barre '{v['barcode']}' est déjà utilisé.")
            else:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
        except Exception as ex:
            messagebox.showerror("Erreur", f"Erreur: {str(ex)}")
        finally:
            conn.close()
    def notifier_toutes_les_fenetres(self):
        """Notifie toutes les fenêtres Toplevel ouvertes qu'un produit a changé"""
        # Méthode 1 : Utiliser un événement virtuel global
        # Envoyer un événement à la fenêtre principale
        root = self.winfo_toplevel()
        root.event_generate("<<ProduitsModifies>>", when="tail")
        
        # Méthode 2 : Parcourir toutes les fenêtres Toplevel
        for fenetre in root.winfo_children():
            if isinstance(fenetre, tk.Toplevel):
                # Essayer de trouver une méthode refresh_produits dans la fenêtre
                if hasattr(fenetre, 'refresh_produits'):
                    fenetre.refresh_produits()
                # Ou chercher dans les enfants de la fenêtre
                else:
                    self._chercher_refresh_dans_enfants(fenetre)
    
    def _chercher_refresh_dans_enfants(self, widget):
        """Recherche récursivement un widget avec refresh_produits"""
        if hasattr(widget, 'refresh_produits'):
            widget.refresh_produits()
            return True
        
        if hasattr(widget, 'winfo_children'):
            for enfant in widget.winfo_children():
                if self._chercher_refresh_dans_enfants(enfant):
                    return True
        return False        

# ========== PAGE TABLEAU DE BORD ==========

