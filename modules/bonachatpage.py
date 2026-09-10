from modules.core import *
from modules.bondialog import BonDialog
from modules.bondetaildialog import BonDetailDialog
from modules.boneditdialog import BonEditDialog

class BonAchatPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        logging.info("🚀 BonAchatPage.__init__() appelé")
        
        # ✅ Initialiser TOUTES les variables AVANT _build()
        self.fournisseur_filter_var = tk.StringVar(value="Tous")
        self.fournisseur_filter_combo = None
        self.sv = tk.StringVar()
        self.tree = None
        self.total_ht_global = tk.StringVar(value="0.00 DA")
        self.total_ttc_global = tk.StringVar(value="0.00 DA")
        self.situation_ttc_global = tk.StringVar(value="0.00 DA")
        
        try:
            self._build()
            logging.info("✅ _build() terminé")
            self.refresh()
            logging.info("✅ refresh() terminé")
        except Exception as e:
            logging.error(f"❌ ERREUR INIT: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self._afficher_erreur(e)

    def _build(self):
        logging.info("🏗️ _build() - Construction de la page...")
        
        try:
            hdr = tk.Frame(self, bg=CLR_BG)
            hdr.pack(fill="x", padx=20, pady=(20,10))
            lbl(hdr, "🛒  Bons d'Achat", 16, True).pack(side="left")
            logging.info("✅ En-tête créé")
            
            btn_frame = tk.Frame(hdr, bg=CLR_BG)
            btn_frame.pack(side="right")
            
            tk.Button(btn_frame, text="+ Nouveau Bon", command=self.new_bon,
                    bg=CLR_GREEN, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
            
            tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bons,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
            
            tk.Button(btn_frame, text="📊 Exporter", command=self.export_bons,
                    bg=CLR_ORANGE, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
            logging.info("✅ Boutons créés")

            # 🔹 BARRE DE RECHERCHE ET FILTRES
            sf = tk.Frame(self, bg=CLR_BG)
            sf.pack(fill="x", padx=20, pady=5)
            logging.info("✅ Frame de recherche créé")
            
            # Recherche textuelle
            lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
            self.sv.trace_add("write", lambda *a: self.refresh())
            entry(sf, width=20, textvariable=self.sv).pack(side="left", padx=8)
            logging.info("✅ Champ recherche créé")

            # ✅ COMBOBOX FILTRE PAR FOURNISSEUR
            try:
                logging.info("🔧 Création de la combobox fournisseur...")
                lbl(sf, "Fournisseur:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
                
                if not hasattr(self, 'fournisseur_filter_var'):
                    self.fournisseur_filter_var = tk.StringVar(value="Tous")
                    
                self.fournisseur_filter_combo = combo(sf, ["Tous"], width=25, textvariable=self.fournisseur_filter_var)
                self.fournisseur_filter_combo.pack(side="left", padx=5)
                self.fournisseur_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
                logging.info("✅ Combobox fournisseur créée")
            except Exception as e:
                logging.error(f"❌ Erreur création combobox: {e}")
                self.fournisseur_filter_combo = None
                self.fournisseur_filter_var = tk.StringVar(value="Tous")
                logging.warning("⚠️ Combobox de secours créée")

            # ✅ CHARGER LES FOURNISSEURS
            try:
                logging.info("🔄 Chargement des fournisseurs...")
                self.load_fournisseurs_list()
                logging.info("✅ Fournisseurs chargés")
            except Exception as e:
                logging.error(f"❌ Erreur chargement fournisseurs: {e}")
                if self.fournisseur_filter_combo:
                    self.fournisseur_filter_combo['values'] = ["Tous"]
                    self.fournisseur_filter_var.set("Tous")

            # ✅ TABLEAU
            try:
                logging.info("🔧 Création du tableau...")
                cols = ["Numéro", "Date création", "Date livraison", "Fournisseur", "Total HT", "Total TTC", "Statut", "Situation TTC", "Cartons"]
                widths = [120, 100, 100, 200, 100, 100, 80, 120, 100]
                tf, self.tree = make_tree(self, cols, widths)
                tf.pack(fill="both", expand=True, padx=20, pady=10)
                logging.info("✅ Tableau créé")
            except Exception as e:
                logging.error(f"❌ Erreur création tableau: {e}")
                raise

            # ✅ CADRE DE SYNTHÈSE
            try:
                logging.info("🔧 Création de la synthèse...")
                synthese_frame = tk.Frame(self, bg=CLR_CARD, padx=15, pady=10)
                synthese_frame.pack(fill="x", padx=20, pady=(0, 10))
                
                lbl(synthese_frame, "📊 SYNTHÈSE DES ACHATS", 11, True, CLR_ACCENT).pack(anchor="w", pady=(0, 5))
                tk.Frame(synthese_frame, bg=CLR_BORDER, height=1).pack(fill="x", pady=5)
                
                totals_frame = tk.Frame(synthese_frame, bg=CLR_CARD)
                totals_frame.pack(fill="x", pady=5)
                
                lbl(totals_frame, "Total HT:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.total_ht_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.total_ht_global, bg=CLR_CARD, 
                        fg=CLR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 20))

                lbl(totals_frame, "Total TTC:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.total_ttc_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.total_ttc_global, bg=CLR_CARD, 
                        fg=CLR_ORANGE, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 20))

                lbl(totals_frame, "Situation TTC:", 10, True, CLR_MUTED).pack(side="left", padx=(10, 5))
                self.situation_ttc_global = tk.StringVar(value="0.00 DA")
                tk.Label(totals_frame, textvariable=self.situation_ttc_global, bg=CLR_CARD, 
                        fg=CLR_GREEN, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 20))
                logging.info("✅ Synthèse créée")
            except Exception as e:
                logging.error(f"❌ Erreur création synthèse: {e}")
                self.total_ht_global = tk.StringVar(value="0.00 DA")
                self.total_ttc_global = tk.StringVar(value="0.00 DA")
                self.situation_ttc_global = tk.StringVar(value="0.00 DA")

            # ✅ BOUTONS D'ACTION
            try:
                logging.info("🔧 Création des boutons d'action...")
                bf = tk.Frame(self, bg=CLR_BG)
                bf.pack(fill="x", padx=20, pady=(0,15))
                
                for txt, cmd, clr in [
                    ("👁 Détail", self.view_bon, CLR_ACCENT),
                    ("✏ Modifier", self.edit_bon, CLR_ORANGE),
                    ("🗑 Supprimer", self.delete_bon, CLR_RED),
                    ("🗑 Annuler", self.cancel_bon, CLR_RED)
                ]:
                    tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                            font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
                logging.info("✅ Boutons d'action créés")
            except Exception as e:
                logging.error(f"❌ Erreur création boutons: {e}")

        except Exception as e:
            logging.error(f"❌ ERREUR DANS _build(): {e}")
            logging.error(traceback.format_exc())
            raise

    def load_fournisseurs_list(self):
        """Charge la liste des fournisseurs dans le combobox - AVEC LOGS"""
        try:
            logging.info("🔍 load_fournisseurs_list() - Début")
            
            # ✅ VÉRIFIER QUE LA COMBOBOX EXISTE
            if not hasattr(self, 'fournisseur_filter_combo') or self.fournisseur_filter_combo is None:
                logging.warning("❌ fournisseur_filter_combo n'existe pas ou est None !")
                # Créer une combobox de secours
                sf = tk.Frame(self, bg=CLR_BG)
                sf.pack(fill="x", padx=20, pady=5)
                lbl(sf, "Fournisseur:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
                self.fournisseur_filter_var = tk.StringVar(value="Tous")
                self.fournisseur_filter_combo = combo(sf, ["Tous"], width=25, textvariable=self.fournisseur_filter_var)
                self.fournisseur_filter_combo.pack(side="left", padx=5)
                self.fournisseur_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
                logging.info("✅ Combobox de secours créée")
            
            # ✅ CONNEXION À LA BASE
            logging.info(f"🔍 Connexion à la base: {DB_PATH}")
            conn = get_conn()
            logging.info("✅ Connexion OK")
            
            # ✅ VÉRIFIER LA TABLE fournisseurs
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fournisseurs'").fetchall()
            if not tables:
                logging.warning("⚠️ Table fournisseurs manquante !")
                conn.close()
                if self.fournisseur_filter_combo:
                    self.fournisseur_filter_combo['values'] = ["Tous"]
                    self.fournisseur_filter_var.set("Tous")
                return
            
            # ✅ COMPTER LES FOURNISSEURS
            count = conn.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0]
            logging.info(f"📊 {count} fournisseurs dans la base")
            
            # ✅ RÉCUPÉRER LES FOURNISSEURS
            fournisseurs = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
            conn.close()
            
            # ✅ CONSTRUIRE LA LISTE
            fournisseur_liste = ["Tous"]
            for f in fournisseurs:
                fournisseur_liste.append(f["nom"])
            
            logging.info(f"📋 Liste des fournisseurs: {fournisseur_liste}")
            
            # ✅ METTRE À JOUR LA COMBOBOX
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = fournisseur_liste
                self.fournisseur_filter_var.set("Tous")
                logging.info("✅ Combobox mise à jour avec succès")
            else:
                logging.error("❌ fournisseur_filter_combo est None après création !")
                
        except sqlite3.OperationalError as e:
            logging.error(f"❌ Erreur SQLite: {e}")
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = ["Tous"]
                self.fournisseur_filter_var.set("Tous")
        except Exception as e:
            logging.error(f"❌ Erreur load_fournisseurs_list: {e}")
            
            if self.fournisseur_filter_combo:
                self.fournisseur_filter_combo['values'] = ["Tous"]
                self.fournisseur_filter_var.set("Tous")


    def refresh(self):
        q = self.sv.get().lower()
        fournisseur_filter = self.fournisseur_filter_var.get()
        
        if self.tree:
            self.tree.delete(*self.tree.get_children())
        else:
            logging.warning("⚠️ self.tree est None dans refresh()")
            return
        
        conn = get_conn()
        
        try:
            # ✅ REQUÊTE PRINCIPALE : Récupérer TOUS les bons (y compris SI-F-)
            if fournisseur_filter != "Tous":
                rows = conn.execute("""
                    SELECT 
                        b.id,
                        b.numero,
                        b.date_bon,
                        b.date_livraison,
                        f.nom as fnom,
                        b.total as total_ttc,
                        b.statut,
                        b.ancien_solde,
                        b.nouveau_solde,
                        (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                        FROM lignes_achat la 
                        JOIN produits p ON la.produit_id = p.id 
                        WHERE la.bon_id = b.id) as total_cartons
                    FROM bons_achat b
                    JOIN fournisseurs f ON b.fournisseur_id = f.id
                    WHERE f.nom = ?
                    ORDER BY b.date_bon DESC, b.numero DESC
                """, (fournisseur_filter,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT 
                        b.id,
                        b.numero,
                        b.date_bon,
                        b.date_livraison,
                        f.nom as fnom,
                        b.total as total_ttc,
                        b.statut,
                        b.ancien_solde,
                        b.nouveau_solde,
                        (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                        FROM lignes_achat la 
                        JOIN produits p ON la.produit_id = p.id 
                        WHERE la.bon_id = b.id) as total_cartons
                    FROM bons_achat b
                    JOIN fournisseurs f ON b.fournisseur_id = f.id
                    ORDER BY b.date_bon DESC, b.numero DESC
                """).fetchall()
        except Exception as e:
            logging.error(f"❌ Erreur requête: {e}")
            conn.close()
            return
        
        conn.close()
        
        total_ht_global = 0
        total_ttc_global = 0

        for r in rows:
            # ✅ RECHERCHE TEXTUELLE (numéro + fournisseur)
            if q and q not in r["numero"].lower() and q not in r["fnom"].lower():
                continue
            
            # ✅ RÉCUPÉRER LES LIGNES DU BON AVEC UNE NOUVELLE CONNEXION
            conn2 = get_conn()
            try:
                lignes_bon = conn2.execute("""
                    SELECT 
                        COALESCE(total_ht, 0) as ht,
                        COALESCE(total_ttc, 0) as ttc,
                        COALESCE(tva_taux, 19) as tva,
                        COALESCE(total, 0) as total
                    FROM lignes_achat 
                    WHERE bon_id = ?
                """, (r["id"],)).fetchall()
            except Exception as e:
                logging.error(f"❌ Erreur récupération lignes bon {r['id']}: {e}")
                conn2.close()
                continue
            
            conn2.close()
            
            ht_bon = 0
            ttc_bon = 0
            
            # ✅ SI LE BON N'A PAS DE LIGNES (ex: solde initial), on utilise total_ttc
            if not lignes_bon:
                # Utiliser le total du bon (souvent dans b.total)
                try:
                    ttc_bon = float(r["total_ttc"] or 0)
                    ht_bon = ttc_bon  # Pour les soldes initiaux, on considère HT = TTC
                except Exception as e:
                    logging.warning(f"⚠️ Erreur conversion total bon: {e}")
                    ttc_bon = 0
                    ht_bon = 0
            else:
                # ✅ CALCUL À PARTIR DES LIGNES
                for lg in lignes_bon:
                    try:
                        # Conversion sécurisée
                        ht_val = float(str(lg["ht"]).replace(',', '.')) if lg["ht"] not in (None, '') else 0
                        ttc_val = float(str(lg["ttc"]).replace(',', '.')) if lg["ttc"] not in (None, '') else 0
                        tva_val = float(str(lg["tva"]).replace(',', '.')) if lg["tva"] not in (None, '') else 19
                        total_val = float(str(lg["total"]).replace(',', '.')) if lg["total"] not in (None, '') else 0
                        
                        # Si TTC manquant, le recalculer
                        if ttc_val == 0 and ht_val > 0:
                            ttc_val = ht_val * (1 + tva_val / 100)
                        
                        ht_bon += ht_val
                        ttc_bon += ttc_val
                        
                    except Exception as e:
                        logging.warning(f"⚠️ Erreur traitement ligne: {e}")
                        continue
            
            # ✅ SI APRÈS TOUT, LE TTC EST ENCORE À 0, UTILISER LA VALEUR GLOBALE DU BON
            if ttc_bon == 0 and ht_bon == 0:
                try:
                    ttc_bon = float(r["total_ttc"] or 0)
                    ht_bon = ttc_bon
                except Exception as e:
                    logging.warning(f"⚠️ Erreur conversion total bon (fallback): {e}")
                    ttc_bon = 0
                    ht_bon = 0

            total_ht_global += ht_bon
            total_ttc_global += ttc_bon
            
            cartons = r['total_cartons'] or 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            # ✅ DÉTERMINER SI C'EST UN SOLDE INITIAL POUR L'AFFICHAGE
            if r["numero"].startswith("SI-F-"):
                statut_affichage = "SOLDE INITIAL"
                tag = ("solde_initial",)
            else:
                statut_affichage = r["statut"]
                tag = None
            
            try:
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], 
                    r["date_bon"],
                    r["date_livraison"] or "-", 
                    r["fnom"],
                    f"{ht_bon:,.2f}", 
                    f"{ttc_bon:,.2f}",
                    statut_affichage, 
                    f"{ttc_bon:,.2f}",
                    cartons_text
                ), tags=tag if tag else ())
            except Exception as e:
                logging.error(f"❌ Erreur insertion dans treeview: {e}")

        # ✅ METTRE À JOUR LES TOTAUX GLOBAUX
        self.total_ht_global.set(f"{total_ht_global:,.2f} DA")
        self.total_ttc_global.set(f"{total_ttc_global:,.2f} DA")
        self.situation_ttc_global.set(f"{total_ttc_global:,.2f} DA")

        # ✅ CONFIGURER LE TAG "solde_initial"
        self.tree.tag_configure("solde_initial", foreground=CLR_PURPLE, font=("Segoe UI", 9, "bold"))

        logging.info("✅ refresh() terminé")
    def _afficher_erreur(self, error):
        """Affiche une erreur dans la page"""
        for w in self.winfo_children():
            w.destroy()
        
        error_frame = tk.Frame(self, bg=CLR_BG)
        error_frame.pack(fill="both", expand=True, padx=50, pady=50)
        
        tk.Label(error_frame, text="❌ Erreur de chargement", 
                bg=CLR_BG, fg=CLR_RED, font=("Segoe UI", 18, "bold")).pack(pady=20)
        
        tk.Label(error_frame, text=f"Erreur: {str(error)}", 
                bg=CLR_BG, fg=CLR_TEXT, font=("Segoe UI", 12)).pack(pady=10)
        
        tk.Label(error_frame, text=f"Base de données: {DB_PATH}", 
                bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 9)).pack(pady=5)
        
        if os.path.exists(DB_PATH):
            tk.Label(error_frame, text="✅ Fichier base trouvé", 
                    bg=CLR_BG, fg=CLR_GREEN, font=("Segoe UI", 9)).pack(pady=5)
        else:
            tk.Label(error_frame, text=f"❌ Fichier base NON trouvé: {DB_PATH}", 
                    bg=CLR_BG, fg=CLR_RED, font=("Segoe UI", 9)).pack(pady=5)
        
        tk.Button(error_frame, text="🔄 Réessayer", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(pady=20)

    def new_bon(self):
        d = BonDialog(self, "achat")
        self.wait_window(d)
        self.refresh()

    def view_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon")
            return
        d = BonDetailDialog(self, "achat", sel[0])
        self.wait_window(d)

    def edit_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à modifier")
            return
        bon_id = sel[0]
        conn = get_conn()
        bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (bon_id,)).fetchone()
        if bon["statut"] == "Annulé":
            messagebox.showwarning("", "Impossible de modifier un bon annulé")
            conn.close()
            return
        lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.prix_achat 
                                FROM lignes_achat l
                                JOIN produits p ON l.produit_id = p.id
                                WHERE l.bon_id=?""", (bon_id,)).fetchall()
        conn.close()
        d = BonEditDialog(self, "achat", bon_id, dict(bon), lignes)
        self.wait_window(d)
        self.refresh()

    def delete_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à supprimer")
            return
        if not messagebox.askyesno("Confirmation", 
                                "⚠️ Supprimer définitivement ce bon ?\n"
                                "Cette action est irréversible et ajustera le stock et les soldes."):
            return
        conn = get_conn()
        try:
            bon_id = sel[0]
            bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (bon_id,)).fetchone()
            lignes = conn.execute("SELECT * FROM lignes_achat WHERE bon_id=?", (bon_id,)).fetchall()
            if bon["statut"] != "Annulé":
                inverser_stock_achat(conn, lignes)
                conn.execute("UPDATE fournisseurs SET solde = solde - ? WHERE id=?", 
                        (bon["total"], bon["fournisseur_id"]))
            conn.execute("DELETE FROM lignes_achat WHERE bon_id=?", (bon_id,))
            conn.execute("DELETE FROM bons_achat WHERE id=?", (bon_id,))
            conn.commit()
            messagebox.showinfo("Succès", "Bon supprimé avec succès")
            self.refresh()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {str(ex)}")
        finally:
            conn.close()

    def cancel_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon")
            return
        if messagebox.askyesno("Annulation", "Annuler ce bon ? Le stock sera recalculé."):
            conn = get_conn()
            bon = conn.execute("SELECT * FROM bons_achat WHERE id=?", (sel[0],)).fetchone()
            if bon["statut"] == "Annulé":
                messagebox.showinfo("", "Déjà annulé")
                conn.close()
                return
            lignes = conn.execute("SELECT * FROM lignes_achat WHERE bon_id=?", (sel[0],)).fetchall()
            inverser_stock_achat(conn, lignes)
            fid = bon["fournisseur_id"]
            conn.execute("UPDATE fournisseurs SET solde = solde - ? WHERE id=?", (bon["total"], fid))
            conn.execute("UPDATE bons_achat SET statut='Annulé' WHERE id=?", (sel[0],))
            conn.commit()
            conn.close()
            self.refresh()

    def get_bons_data(self, fournisseur_filter=None):
        """Récupérer les données des bons avec filtre fournisseur"""
        conn = get_conn()
        
        if fournisseur_filter and fournisseur_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    f.nom as fournisseur, 
                    b.total as total_ttc,
                    b.statut,
                    (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                    FROM lignes_achat la 
                    JOIN produits p ON la.produit_id = p.id 
                    WHERE la.bon_id = b.id) as total_cartons
                FROM bons_achat b
                JOIN fournisseurs f ON b.fournisseur_id = f.id
                WHERE f.nom = ?
                ORDER BY b.date_bon DESC
            """, (fournisseur_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    f.nom as fournisseur, 
                    b.total as total_ttc,
                    b.statut,
                    (SELECT COALESCE(SUM(la.quantite / p.facteur_conversion), 0)
                    FROM lignes_achat la 
                    JOIN produits p ON la.produit_id = p.id 
                    WHERE la.bon_id = b.id) as total_cartons
                FROM bons_achat b
                JOIN fournisseurs f ON b.fournisseur_id = f.id
                ORDER BY b.date_bon DESC
            """).fetchall()
        
        conn.close()
        
        data = []
        total_general = 0
        for r in rows:
            total_ttc = r["total_ttc"]
            total_general += total_ttc
            cartons = r["total_cartons"] if r["total_cartons"] is not None else 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            data.append([
                r["numero"], 
                r["date_bon"], 
                r["fournisseur"], 
                f"{total_ttc:,.2f}", 
                r["statut"],
                cartons_text
            ])
        
        if data:
            data.append(["", "", "", "", "", ""])
            data.append(["", "", "TOTAL TTC", f"{total_general:,.2f} DA", "", ""])
        
        return data, total_general

    def print_bons(self):
        fournisseur_filter = self.fournisseur_filter_var.get()
        data, total_general = self.get_bons_data(fournisseur_filter)
        
        if not data or len(data) <= 1:
            messagebox.showinfo("Information", "Aucun bon d'achat trouvé pour ce fournisseur")
            return
        
        if fournisseur_filter and fournisseur_filter != "Tous":
            title = f"LISTE DES BONS D'ACHAT - {fournisseur_filter.upper()}"
        else:
            title = "LISTE DES BONS D'ACHAT - TOUS LES FOURNISSEURS"
        
        headers = ["Numéro", "Date", "Fournisseur", "Total TTC", "Statut", "Cartons"]
        
        footer_text = f"\n{'='*60}\nTOTAL GENERAL TTC: {total_general:,.2f} DA\n{'='*60}\n"
        footer_text += f"Nombre de bons: {len(data)-2}\n"
        footer_text += f"Date d'impression: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        print_preview(data, title, headers, footer_text=footer_text)

    def export_bons(self):
        data, _ = self.get_bons_data(self.fournisseur_filter_var.get())
        headers = ["Numéro", "Date", "Fournisseur", "Total", "Statut", "Cartons"]
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="bons_achat.csv"
        )
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "BONS D'ACHAT", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")

# ========== PAGE BONS DE VENTE ==========

