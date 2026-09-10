from modules.core import *
from modules.tiersdialog import TiersDialog
from modules.prixspeciauxclientdialog import PrixSpeciauxClientDialog

class TiersPage(tk.Frame):
    def __init__(self, parent, tiers_type="client"):
        self.tiers_type = tiers_type
        self.table = "clients" if tiers_type == "client" else "fournisseurs"
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
        self.tiers_list = []


    def _build(self):
        title = "👥  Clients" if self.tiers_type == "client" else "🏭  Fournisseurs"
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, title, 16, True).pack(side="left")
        nom = "Client" if self.tiers_type == "client" else "Fournisseur"
        tk.Button(hdr, text=f"+ Nouveau {nom}", command=self.new_item,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="right")
        # Dans TiersPage._build(), après les autres boutons
        
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)

        # ✅ AJOUTER PLUS DE COLONNES
        cols = ["Code", "Nom", "Adresse", "Ville", "Téléphone", "Email", "NIF", "Solde"]
        widths = [80, 150, 150, 80, 100, 130, 100, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0,15))
        
        for txt, cmd, clr in [
            ("✏ Modifier", self.edit_item, CLR_ACCENT),
            ("💰 Prix spéciaux", self.gestion_prix_speciaux, CLR_ORANGE),
            ("🗑 Supprimer", self.del_item, CLR_RED),
            ("💸 Dette", self.gestion_dette, CLR_ORANGE),  
            ("🗑 Supprimer Solde Initial", self.supprimer_solde_initial, CLR_RED),  # ✅ NOUVEAU


        ]:
            tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)  
    def gestion_dette(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return

        conn = get_conn()
        tiers = conn.execute(
            f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)
        ).fetchone()
        conn.close()

        if not tiers:
            return

        if self.tiers_type == "client" and tiers["nom"].upper() == "COMPTOIR":
            messagebox.showwarning("Action impossible",
                "Le client 'COMPTOIR' est un compte technique.")
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Gestion des dettes — {tiers['nom']}")
        dlg.configure(bg=CLR_BG)
        dlg.geometry("600x750")  # PLUS GRAND
        dlg.minsize(550, 650)    # TAILLE MINIMUM
        dlg.resizable(True, True)
        dlg.grab_set()
        center_window(dlg, 600, 750)

        main = tk.Frame(dlg, bg=CLR_BG, padx=25, pady=20)
        main.pack(fill="both", expand=True)

        # En-tête
        lbl(main, "💸 GESTION DES DETTES", 14, True, CLR_ACCENT).pack(anchor="w")
        lbl(main, tiers["nom"], 11, True, CLR_TEXT).pack(anchor="w", pady=(2, 0))
        solde_color = CLR_RED if tiers["solde"] < 0 else CLR_ORANGE
        lbl(main, f"Solde actuel : {tiers['solde']:,.2f} DA",
            10, False, solde_color).pack(anchor="w", pady=(0, 15))

        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=(0, 15))

        # Choix du type
        lbl(main, "Type d'opération :", 9, True, CLR_MUTED).pack(anchor="w", pady=(0, 8))

        type_var = tk.StringVar(value="solde_initial")

        choix_frame = tk.Frame(main, bg=CLR_BG)
        choix_frame.pack(fill="x", pady=(0, 15))
        choix_frame.grid_columnconfigure(0, weight=1)
        choix_frame.grid_columnconfigure(1, weight=1)

        card_si = tk.Frame(choix_frame, bg=CLR_CARD, relief="flat",
                        padx=15, pady=12,
                        highlightthickness=2,
                        highlightbackground=CLR_ACCENT)
        card_si.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        card_remb = tk.Frame(choix_frame, bg=CLR_CARD, relief="flat",
                            padx=15, pady=12,
                            highlightthickness=1,
                            highlightbackground=CLR_BORDER)
        card_remb.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        if self.tiers_type == "fournisseur":
            remb_titre  = "🛒 Achat en nature / avoir"
            remb_desc   = "Marchandise ou service reçu\n(ex: frigos, équipements…)\n→ Augmente le solde fournisseur"
            remb_couleur = CLR_ORANGE
            # solde_initial : dette de départ → augmente aussi le solde
            si_desc = "Dette antérieure au démarrage\n→ Augmente le solde fournisseur"
        else:
            remb_titre  = "↩️ Remboursement client"
            remb_desc   = "Somme à rembourser au client\n→ Diminue son solde"
            remb_couleur = CLR_GREEN
            si_desc = "Dette antérieure au démarrage\n→ Augmente le solde client"

        lbl(card_si, "📋 Solde initial", 10, True, CLR_ACCENT).pack(anchor="w")
        lbl(card_si, si_desc, 8, False, CLR_MUTED).pack(anchor="w", pady=(3, 0))

        lbl(card_remb, remb_titre, 10, True, CLR_TEXT).pack(anchor="w")
        lbl(card_remb, remb_desc, 8, False, CLR_MUTED).pack(anchor="w", pady=(3, 0))

        def select_si(e=None):
            type_var.set("solde_initial")
            card_si.config(highlightthickness=2, highlightbackground=CLR_ACCENT)
            card_remb.config(highlightthickness=1, highlightbackground=CLR_BORDER)
            update_preview()

        def select_remb(e=None):
            type_var.set("remboursement")
            card_remb.config(highlightthickness=2, highlightbackground=remb_couleur)
            card_si.config(highlightthickness=1, highlightbackground=CLR_BORDER)
            update_preview()

        for w in [card_si] + list(card_si.winfo_children()):
            w.bind("<Button-1>", select_si)
        for w in [card_remb] + list(card_remb.winfo_children()):
            w.bind("<Button-1>", select_remb)

        # Montant
        lbl(main, "Montant (DA) :", 9, False, CLR_MUTED).pack(anchor="w", pady=(5, 3))
        montant_var = tk.StringVar()
        entry(main, width=30, textvariable=montant_var,
            font=("Segoe UI", 12, "bold")).pack(anchor="w")

        # Motif
        lbl(main, "Motif :", 9, False, CLR_MUTED).pack(anchor="w", pady=(10, 3))
        motif_var = tk.StringVar()
        entry(main, width=50, textvariable=motif_var).pack(anchor="w", fill="x")

        # Date
        lbl(main, "Date :", 9, False, CLR_MUTED).pack(anchor="w", pady=(10, 3))
        date_var = tk.StringVar(value="2025-12-31")
        entry(main, width=18, textvariable=date_var).pack(anchor="w")

        # Aperçu solde
        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=15)

        preview = tk.Frame(main, bg=CLR_CARD, padx=15, pady=12)
        preview.pack(fill="x")

        r1 = tk.Frame(preview, bg=CLR_CARD)
        r1.pack(fill="x", pady=2)
        lbl(r1, "Solde avant :", 9, False, CLR_MUTED).pack(side="left")
        lbl(r1, f"{tiers['solde']:,.2f} DA", 9, False, CLR_TEXT).pack(side="right")

        r2 = tk.Frame(preview, bg=CLR_CARD)
        r2.pack(fill="x", pady=2)
        lbl(r2, "Opération :", 9, False, CLR_MUTED).pack(side="left")
        op_var = tk.StringVar(value="+ 0,00 DA")
        tk.Label(r2, textvariable=op_var, bg=CLR_CARD,
                fg=CLR_ACCENT, font=("Segoe UI", 9, "bold")).pack(side="right")

        tk.Frame(preview, bg=CLR_BORDER, height=1).pack(fill="x", pady=6)

        r3 = tk.Frame(preview, bg=CLR_CARD)
        r3.pack(fill="x", pady=2)
        lbl(r3, "Nouveau solde :", 10, True, CLR_MUTED).pack(side="left")
        nv_var = tk.StringVar(value=f"{tiers['solde']:,.2f} DA")
        tk.Label(r3, textvariable=nv_var, bg=CLR_CARD,
                fg=CLR_GREEN, font=("Segoe UI", 11, "bold")).pack(side="right")

        def update_preview(*args):
            try:
                montant = parse_decimal(montant_var.get() or "0")
            except ValueError:
                montant = 0
            solde = tiers["solde"]
            type_op = type_var.get()

            if type_op == "solde_initial":
                # Solde initial → toujours augmente (client ou fournisseur)
                nouveau = solde + montant
                op_var.set(f"+ {montant:,.2f} DA")
            else:
                if self.tiers_type == "fournisseur":
                    # Achat en nature → augmente le solde fournisseur
                    nouveau = solde + montant
                    op_var.set(f"+ {montant:,.2f} DA")
                else:
                    # Remboursement client → diminue son solde
                    nouveau = solde - montant
                    op_var.set(f"- {montant:,.2f} DA")

            nv_var.set(f"{nouveau:,.2f} DA")

        montant_var.trace_add("write", update_preview)

        # Boutons
        tk.Frame(main, bg=CLR_BORDER, height=1).pack(fill="x", pady=15)
        btn_frame = tk.Frame(main, bg=CLR_BG)
        btn_frame.pack(fill="x")

        def enregistrer():
            try:
                montant = parse_decimal(montant_var.get() or "0")
                if montant <= 0:
                    messagebox.showerror("Erreur", "Montant invalide", parent=dlg)
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Montant invalide", parent=dlg)
                return

            motif = motif_var.get().strip()
            if not motif:
                messagebox.showerror("Erreur", "Le motif est obligatoire", parent=dlg)
                return

            date_val = date_var.get().strip()
            if not valider_date(date_val):
                messagebox.showerror("Erreur",
                    "Date invalide (format YYYY-MM-DD)", parent=dlg)
                return

            type_op = type_var.get()

            if type_op == "solde_initial":
                # ── Vérifier doublon solde initial ──────────────────────────
                conn2 = get_conn()
                if self.tiers_type == "client":
                    existing = conn2.execute(
                        "SELECT id, numero, total FROM bons_vente "
                        "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                        (tiers["id"],)
                    ).fetchone()
                else:
                    existing = conn2.execute(
                        "SELECT id, numero, total FROM bons_achat "
                        "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                        (tiers["id"],)
                    ).fetchone()
                conn2.close()

                if existing:
                    messagebox.showwarning(
                        "Solde initial déjà existant",
                        f"Un solde initial existe déjà :\n"
                        f"📄 {existing['numero']} : {existing['total']:,.2f} DA\n\n"
                        "Supprimez-le d'abord via 'Supprimer Solde Initial'.",
                        parent=dlg
                    )
                    return

                ok = self.ajouter_solde_initial(
                    tiers["id"], montant, motif, date_val
                )
                if ok:
                    messagebox.showinfo("Succès",
                        f"✅ Solde initial enregistré !\n\n"
                        f"Montant : {montant:,.2f} DA\n"
                        f"Motif   : {motif}\n"
                        f"Date    : {date_val}", parent=dlg)
                    dlg.destroy()
                    self.refresh()

            else:
                # ── Achat en nature (fournisseur) ou remboursement (client) ─
                if self.tiers_type == "fournisseur":
                    # Enregistrer comme bon d'achat spécial
                    ok = self._enregistrer_achat_nature(
                        tiers["id"], montant, motif, date_val
                    )
                else:
                    # Remboursement client → diminue le solde
                    ok = self._enregistrer_remboursement_client(
                        tiers["id"], montant, motif, date_val
                    )
                if ok:
                    type_label = ("Achat en nature" if self.tiers_type == "fournisseur"
                                else "Remboursement client")
                    messagebox.showinfo("Succès",
                        f"✅ {type_label} enregistré !\n\n"
                        f"Montant : {montant:,.2f} DA\n"
                        f"Motif   : {motif}\n"
                        f"Date    : {date_val}", parent=dlg)
                    dlg.destroy()
                    self.refresh()

        tk.Button(btn_frame, text="✅ Enregistrer", command=enregistrer,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", padx=(0, 10), expand=True, fill="x")

        tk.Button(btn_frame, text="❌ Annuler", command=dlg.destroy,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 10, "bold"),
                padx=20, pady=8, cursor="hand2").pack(side="left", expand=True, fill="x")

    def _generer_numero_avoir(self, conn, type_avoir):
        """
        Génère un numéro séquentiel pour les AVOIR par type
        type_avoir: "client" ou "fournisseur"
        Retourne: "AVOIR-C-001" ou "AVOIR-F-001"
        """
        if type_avoir == "client":
            table = "bons_vente"
            prefix = "AVOIR-C"
        else:
            table = "bons_achat"
            prefix = "AVOIR-F"
        
        # Compter le nombre d'AVOIR existants pour ce type
        count = conn.execute(f"""
            SELECT COUNT(*) FROM {table} 
            WHERE numero LIKE '{prefix}-%'
        """).fetchone()[0]
        
        # Générer le prochain numéro
        next_num = count + 1
        return f"{prefix}-{next_num:03d}"  # Format AVOIR-C-001 ou AVOIR-F-001
    def _enregistrer_achat_nature(self, fournisseur_id, montant, motif, date_bon):
        """
        Enregistre un achat en nature (ex: frigos fournis par le fournisseur).
        Augmente le solde fournisseur.
        Préfixe : AVOIR-YYYY-TIMESTAMP
        """
        conn = get_conn()
        try:
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            if not produit:
                conn.execute("""
                    INSERT INTO produits(code, designation, unite,
                        prix_achat, prix_vente, stock_actuel, stock_min, actif, tva)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, ("SOLDE_INITIAL", "Opération comptable", "Pcs",
                    0, 0, 0, 0, 0, 0))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code='SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]

            today = datetime.now()
            current_year = today.strftime("%Y")
            timestamp = today.strftime("%Y%m%d%H%M%S%f")
            num = self._generer_numero_avoir(conn, "fournisseur")

            fournisseur = conn.execute(
                "SELECT solde FROM fournisseurs WHERE id=?", (fournisseur_id,)
            ).fetchone()
            ancien_solde = fournisseur["solde"] if fournisseur else 0
            nouveau_solde = ancien_solde + montant

            conn.execute("""
                INSERT INTO bons_achat(
                    numero, date_bon, fournisseur_id, total, statut,
                    date_creation, observations, ancien_solde, nouveau_solde)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (num, date_bon, fournisseur_id, montant, "Validé",
                today.strftime("%Y-%m-%d %H:%M:%S"),
                motif, ancien_solde, nouveau_solde))

            bon_id = conn.execute(
                "SELECT id FROM bons_achat WHERE numero=?", (num,)
            ).fetchone()["id"]

            conn.execute("""
                INSERT INTO lignes_achat(
                    bon_id, produit_id, quantite, prix_unitaire,
                    total, total_ht, tva_taux, total_ttc)
                VALUES(?,?,?,?,?,?,?,?)
            """, (bon_id, produit_id, 1, montant, montant,
                montant, 0, montant))

            conn.execute(
                "UPDATE fournisseurs SET solde = solde + ? WHERE id=?",
                (montant, fournisseur_id)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()


    def _enregistrer_remboursement_client(self, client_id, montant, motif, date_bon):
        """
        Enregistre un remboursement au client.
        Diminue le solde client.
        Préfixe : REMB-C-YYYY-TIMESTAMP
        """
        conn = get_conn()
        try:
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            if not produit:
                conn.execute("""
                    INSERT INTO produits(code, designation, unite,
                        prix_achat, prix_vente, stock_actuel, stock_min, actif, tva)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, ("SOLDE_INITIAL", "Opération comptable", "Pcs",
                    0, 0, 0, 0, 0, 0))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code='SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]

            today = datetime.now()
            current_year = today.strftime("%Y")
            timestamp = today.strftime("%Y%m%d%H%M%S%f")
            num = self._generer_numero_avoir(conn, "client")

            conn.execute("""
                INSERT INTO bons_vente(
                    numero, date_bon, client_id, total, statut, observations)
                VALUES(?,?,?,?,?,?)
            """, (num, date_bon, client_id, montant, "Validé", motif))

            bon_id = conn.execute(
                "SELECT id FROM bons_vente WHERE numero=?", (num,)
            ).fetchone()["id"]

            conn.execute("""
                INSERT INTO lignes_vente(
                    bon_id, produit_id, quantite, prix_unitaire, total)
                VALUES(?,?,?,?,?)
            """, (bon_id, produit_id, 1, montant, montant))

            conn.execute(
                "UPDATE clients SET solde = solde - ? WHERE id=?",
                (montant, client_id)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()          
    def supprimer_solde_initial(self):
        """Supprimer le solde initial d'un client/fournisseur"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return
        
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        if not tiers:
            return
        
        # Chercher le(s) solde(s) initial(aux)
        conn = get_conn()
        if self.tiers_type == "client":
            soldes = conn.execute(
                "SELECT id, numero, total FROM bons_vente "
                "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchall()
        else:
            soldes = conn.execute(
                "SELECT id, numero, total FROM bons_achat "
                "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchall()
        conn.close()
        
        if not soldes:
            messagebox.showinfo("Information", f"Aucun solde initial trouvé pour {tiers['nom']}")
            return
        
        # Afficher les soldes existants
        msg = f"🗑 Supprimer le(s) solde(s) initial(aux) de {tiers['nom']} ?\n\n"
        total_si = 0
        for si in soldes:
            msg += f"   📄 {si['numero']} : {si['total']:,.2f} DA\n"
            total_si += si['total']
        msg += f"\n💰 Total à supprimer : {total_si:,.2f} DA"
        msg += f"\n📊 Solde actuel : {tiers['solde']:,.2f} DA"
        msg += f"\n📊 Nouveau solde : {tiers['solde'] - total_si:,.2f} DA\n\n"
        msg += "⚠️ Cette action est irréversible !"
        
        if not messagebox.askyesno("⚠️ Confirmation", msg):
            return
        
        # Supprimer les soldes initiaux
        conn = get_conn()
        try:
            for si in soldes:
                if self.tiers_type == "client":
                    # Supprimer le bon de vente
                    conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (si["id"],))
                    conn.execute("DELETE FROM bons_vente WHERE id=?", (si["id"],))
                else:
                    # Supprimer le bon d'achat
                    conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (si["id"],))
                    conn.execute("DELETE FROM bons_achat WHERE id=?", (si["id"],))
            
            # Mettre à jour le solde
            conn.execute(
                f"UPDATE {self.table} SET solde = solde - ? WHERE id=?",
                (total_si, tiers["id"])
            )
            conn.commit()
            messagebox.showinfo("Succès", f"✅ Solde initial supprimé avec succès !")
            self.refresh()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
        finally:
            conn.close()        
    def gestion_solde_initial(self):
        """Dialogue pour ajouter un solde initial (dette antérieure)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un élément")
            return
        
        conn = get_conn()
        tiers = conn.execute(f"SELECT id, nom, solde FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        if not tiers:
            return
        
        # ❌ EXCLURE LE CLIENT COMPTOIR
        if self.tiers_type == "client" and tiers["nom"].upper() == "COMPTOIR":
            messagebox.showwarning(
                "⚠️ Action impossible",
                "Le client 'COMPTOIR' est un compte technique.\n"
                "Les soldes initiaux ne peuvent pas être ajoutés pour ce client."
            )
            return
        
        # ✅ VÉRIFIER SI UN SOLDE INITIAL EXISTE DÉJÀ
        conn = get_conn()
        if self.tiers_type == "client":
            existing = conn.execute(
                "SELECT id, numero, total, date_bon FROM bons_vente "
                "WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id, numero, total, date_bon FROM bons_achat "
                "WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'",
                (tiers["id"],)
            ).fetchone()
        conn.close()
        
        # ❌ BLOQUER SI UN SOLDE INITIAL EXISTE DÉJÀ
        if existing:
            messagebox.showwarning(
                "⚠️ Solde initial déjà existant",
                f"Un solde initial existe déjà pour {tiers['nom']} :\n\n"
                f"📄 {existing['numero']} : {existing['total']:,.2f} DA\n"
                f"📅 Date : {existing['date_bon']}\n\n"
                f"Solde actuel : {tiers['solde']:,.2f} DA\n\n"
                f"❌ Impossible d'ajouter un deuxième solde initial.\n"
                f"💡 Si vous devez corriger le montant, supprimez d'abord le solde initial existant."
            )
            return  # ✅ Le return est ici, après tout est bon
        
        # ✅ DEMANDER LE MONTANT (après le return)
        montant = simpledialog.askfloat(
            "💰 Solde Initial",
            f"Entrez le montant du solde initial pour {tiers['nom']} :\n\n"
            f"Solde actuel : {tiers['solde']:,.2f} DA\n\n"
            f"💡 Montant du solde initial :",
            parent=self,
            minvalue=0,
            initialvalue=0
        )
        
        if montant is None or montant <= 0:
            return
        
        # ✅ DEMANDER LE MOTIF
        motif = simpledialog.askstring(
            "Motif",
            "Motif du solde initial :",
            initialvalue="Solde initial",
            parent=self
        )
        
        if motif is None:
            return
        
        # ✅ DEMANDER LA DATE
        date_si = simpledialog.askstring(
            "Date du solde initial",
            "Date du solde initial (YYYY-MM-DD) :\n"
            "💡 Laisser vide pour utiliser 2025-12-31",
            initialvalue="2025-12-31",
            parent=self
        )
        
        # ✅ VALIDER LA DATE
        if date_si and valider_date(date_si):
            date_bon = date_si
        else:
            date_bon = "2025-12-31"
            if date_si:  # Si une date a été saisie mais invalide
                messagebox.showwarning(
                    "Date invalide",
                    f"La date '{date_si}' n'est pas valide.\n"
                    "Utilisation de la date par défaut : 2025-12-31"
                )
        
        # ✅ CRÉER LE BON SPÉCIAL AVEC LA DATE
        if self.ajouter_solde_initial(tiers["id"], montant, motif, date_bon):
            messagebox.showinfo("Succès", 
                f"✅ Solde initial ajouté avec succès !\n\n"
                f"{'Client' if self.tiers_type == 'client' else 'Fournisseur'} : {tiers['nom']}\n"
                f"Montant : {montant:,.2f} DA\n"
                f"Date : {date_bon}\n"
                f"Motif : {motif}"
            )
            self.refresh()
    def ajouter_solde_initial(self, tiers_id, montant, motif="Solde initial", date_bon=None):
        """
        Ajoute un solde initial pour un client OU un fournisseur.
        Retourne True si succès, False sinon.
        """
        conn = get_conn()
        try:
            # 1. Créer le produit "SOLDE_INITIAL" s'il n'existe pas
            produit = conn.execute(
                "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
            ).fetchone()
            
            if not produit:
                conn.execute("""
                    INSERT INTO produits(
                        code, designation, unite, prix_achat, prix_vente, 
                        stock_actuel, stock_min, actif, tva
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "SOLDE_INITIAL",
                    f"Solde initial {self.tiers_type}",
                    "Pcs", 0, 0, 0, 0, 0, 0
                ))
                produit_id = conn.execute(
                    "SELECT id FROM produits WHERE code = 'SOLDE_INITIAL'"
                ).fetchone()["id"]
            else:
                produit_id = produit["id"]
            
            # 2. Générer un numéro unique avec l'année en cours
            today = datetime.now()
            current_year = today.strftime("%Y")
            prefix = "SI-C" if self.tiers_type == "client" else "SI-F"
            
            # ✅ CORRECTION : Table correcte
            table_bons = "bons_vente" if self.tiers_type == "client" else "bons_achat"
            
            # ✅ CORRECTION : Compter les soldes initiaux existants
            # Construire le pattern complet
            pattern = f"{prefix}-{current_year}-%"
            
            # ✅ CORRECTION : Utiliser une requête simple SANS f-string pour le LIKE
            query = f"SELECT COUNT(*) FROM {table_bons} WHERE numero LIKE ? AND statut='Validé'"
            count = conn.execute(query, (pattern,)).fetchone()[0]
            
            num = f"{prefix}-{current_year}-{count + 1:03d}"
            
            # ✅ Utiliser la date passée ou la date par défaut
            if date_bon is None:
                date_bon = "2025-12-31"
            
            # 3. Récupérer le solde actuel
            tiers = conn.execute(
                f"SELECT solde FROM {self.table} WHERE id=?", (tiers_id,)
            ).fetchone()
            ancien_solde = tiers["solde"] if tiers else 0
            nouveau_solde = ancien_solde + montant
            
            # 4. Créer le bon selon le type
            if self.tiers_type == "client":
                # ✅ CLIENTS → bon de vente
                conn.execute("""
                    INSERT INTO bons_vente(
                        numero, date_bon, client_id, total, statut, observations
                    ) VALUES(?, ?, ?, ?, ?, ?)
                """, (num, date_bon, tiers_id, montant, "Validé", motif))
                
                bon_id = conn.execute(
                    "SELECT id FROM bons_vente WHERE numero=?", (num,)
                ).fetchone()["id"]
                
                conn.execute("""
                    INSERT INTO lignes_vente(
                        bon_id, produit_id, quantite, prix_unitaire, total
                    ) VALUES(?, ?, ?, ?, ?)
                """, (bon_id, produit_id, 1, montant, montant))
                
            else:
                # ✅ FOURNISSEURS → bon d'achat
                conn.execute("""
                    INSERT INTO bons_achat(
                        numero, date_bon, fournisseur_id, total, statut,
                        date_creation, observations,
                        ancien_solde, nouveau_solde
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    num, date_bon, tiers_id, montant, "Validé",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    motif, ancien_solde, nouveau_solde
                ))
                
                bon_id = conn.execute(
                    "SELECT id FROM bons_achat WHERE numero=?", (num,)
                ).fetchone()["id"]
                
                conn.execute("""
                    INSERT INTO lignes_achat(
                        bon_id, produit_id, quantite, prix_unitaire, total,
                        total_ht, tva_taux, total_ttc
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bon_id, produit_id, 1, montant, montant,
                    montant, 0, montant
                ))
            
            # 5. Mettre à jour le solde
            conn.execute(
                f"UPDATE {self.table} SET solde = ? WHERE id=?",
                (nouveau_solde, tiers_id)
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(e)}")
            return False
        finally:
            conn.close()
            
    def gestion_prix_speciaux(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un client")
            return
        
        conn = get_conn()
        client = conn.execute(f"SELECT id, nom FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        d = PrixSpeciauxClientDialog(self, client["id"], client["nom"])
        self.wait_window(d)
    def refresh(self):
        """Rafraîchit la liste et met à jour la liste des noms"""
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        rows = conn.execute(f"SELECT * FROM {self.table} ORDER BY nom").fetchall()
        
        # ✅ METTRE À JOUR LA LISTE DES TIERS
        self.tiers_list = []
        
        for r in rows:
            if q in r["code"].lower() or q in r["nom"].lower():
                tiers_id = r["id"]
                
                # ✅ Calculer le solde réel
                if self.tiers_type == "client":
                    # Récupérer les soldes initiaux
                    si = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_vente 
                        WHERE client_id=? AND numero LIKE 'SI-C-%' AND statut='Validé'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les ventes
                    ventes = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_vente 
                        WHERE client_id=? AND statut='Validé' AND numero NOT LIKE 'SI-C-%'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les retours
                    retours = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM retours_vente 
                        WHERE client_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les versements
                    versements = conn.execute("""
                        SELECT COALESCE(SUM(montant),0) FROM versements_clients 
                        WHERE client_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Calculer le solde réel
                    solde_reel = si + ventes - retours - versements
                    
                else:  # fournisseur
                    # Récupérer les soldes initiaux
                    si = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_achat 
                        WHERE fournisseur_id=? AND numero LIKE 'SI-F-%' AND statut='Validé'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les achats
                    achats = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM bons_achat 
                        WHERE fournisseur_id=? AND statut='Validé' AND numero NOT LIKE 'SI-F-%'
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les retours
                    retours = conn.execute("""
                        SELECT COALESCE(SUM(total),0) FROM retours_achat 
                        WHERE fournisseur_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Récupérer les versements
                    versements = conn.execute("""
                        SELECT COALESCE(SUM(montant),0) FROM versements_fournisseurs 
                        WHERE fournisseur_id=?
                    """, (tiers_id,)).fetchone()[0]
                    
                    # Calculer le solde réel
                    solde_reel = si + achats - retours - versements
                
                # ✅ Afficher le solde réel
                clr = CLR_RED if solde_reel < 0 else CLR_TEXT
                
                # ✅ Ajouter une indication si le solde enregistré est différent
                solde_enregistre = r["solde"]
               
                solde_affichage = f"{solde_reel:.2f}"
                
                self.tree.insert("", "end", iid=r["id"],
                    values=(
                        r["code"], 
                        r["nom"], 
                        r["adresse"] or "",
                        r["ville"] or "",
                        r["tel"] or "",
                        r["email"] or "",
                        r["nif"] or "",
                        solde_affichage  # ✅ Solde réel calculé
                    ),
                    tags=("neg",) if solde_reel < 0 else ())
                
                self.tiers_list.append(r["nom"])  # ✅ AJOUTER À LA LISTE
        
        self.tree.tag_configure("neg", foreground=CLR_RED)
        conn.close()
        
        # ✅ METTRE À JOUR LES COMBOBOX DANS LES AUTRES PAGES
        self.update_comboboxes()
    def update_comboboxes(self):
        """Met à jour les combobox des autres pages"""
        # Si nous sommes dans la page des clients, mettre à jour les combos de ventes
        if self.tiers_type == "client":
            if hasattr(self.master, '_pages') and 'bons_vente' in self.master._pages:
                bon_vente_page = self.master._pages['bons_vente']
                if hasattr(bon_vente_page, 'load_clients_list'):
                    bon_vente_page.load_clients_list()
        # Si nous sommes dans la page des fournisseurs, mettre à jour les combos d'achats
        elif self.tiers_type == "fournisseur":
            if hasattr(self.master, '_pages') and 'bons_achat' in self.master._pages:
                bon_achat_page = self.master._pages['bons_achat']
                if hasattr(bon_achat_page, 'load_fournisseurs_list'):
                    bon_achat_page.load_fournisseurs_list()
    def _form(self, data=None):
        d = TiersDialog(self, self.tiers_type, data)
        self.wait_window(d)
        self.refresh()

    def new_item(self): 
        self._form()
        
    def edit_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un élément")
            return
        conn = get_conn()
        r = conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        self._form(dict(r))

    def del_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un élément")
            return
        if messagebox.askyesno("Confirmation","Supprimer ?"):
            try:
                conn = get_conn()
                conn.execute(f"DELETE FROM {self.table} WHERE id=?", (sel[0],))
                conn.commit()
                conn.close()
                self.refresh()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

