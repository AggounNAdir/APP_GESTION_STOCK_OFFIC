"""
Écran de supervision du Portail Client (Silwane Androway).

Affiche, en lecture depuis la même base SQLite que l'API (aucun appel HTTP
nécessaire, l'app bureau et l'API partagent gestion_stock.db) :
  - les commandes passées depuis le portail, avec validation -> Bon de Vente
  - les pointages GPS de la tournée terrain
  - les prospects saisis sur le terrain, avec conversion -> Client réel
"""
from modules.core import *
from modules.stock_service import valider_transaction_vente


class PortailSuiviPage(tk.Frame):
    """Page de suivi du portail client / tournée terrain."""

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    # ══════════════════════ CONSTRUCTION ══════════════════════

    def _build(self):
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(fill="x", padx=20, pady=(15, 5))
        lbl(header, "🌐 Suivi Portail Client", 16, True, CLR_ACCENT).pack(side="left")
        tk.Button(header, text="🔄 Actualiser", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=5, cursor="hand2").pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_commandes = tk.Frame(self.notebook, bg=CLR_BG)
        self.tab_tournee = tk.Frame(self.notebook, bg=CLR_BG)
        self.tab_prospects = tk.Frame(self.notebook, bg=CLR_BG)

        self.notebook.add(self.tab_commandes, text="🛒 Commandes Portail")
        self.notebook.add(self.tab_tournee, text="📍 Tournée Terrain")
        self.notebook.add(self.tab_prospects, text="🧑‍🤝‍🧑 Prospects")

        self._build_tab_commandes()
        self._build_tab_tournee()
        self._build_tab_prospects()

    # ---------- Onglet Commandes ----------

    def _build_tab_commandes(self):
        f = self.tab_commandes

        filtre = tk.Frame(f, bg=CLR_BG)
        filtre.pack(fill="x", pady=(10, 5))
        lbl(filtre, "Statut :", 9, color=CLR_MUTED).pack(side="left", padx=(0, 5))
        self.filtre_statut_cmd = tk.StringVar(value="En attente")
        cb = ttk.Combobox(filtre, textvariable=self.filtre_statut_cmd, state="readonly",
                           values=["Toutes", "En attente", "Validée", "Rejetée"], width=15)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_commandes())

        cols = ["N°", "Date", "Client", "Total estimé", "Statut", "Observations"]
        widths = [140, 100, 180, 110, 100, 220]
        tf, self.tree_cmd = make_tree(f, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)
        self.tree_cmd.bind("<<TreeviewSelect>>", self._on_select_commande)

        # Détail des lignes de la commande sélectionnée
        detail_frame = tk.LabelFrame(f, text="Lignes de la commande sélectionnée",
                                      bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 9, "bold"))
        detail_frame.pack(fill="x", pady=5)
        cols2 = ["Produit", "Qté", "Prix unitaire estimé", "Total estimé"]
        tf2, self.tree_lignes_cmd = make_tree(detail_frame, cols2, [200, 80, 140, 120])
        tf2.pack(fill="x", padx=5, pady=5)
        self.tree_lignes_cmd.configure(height=4)

        btns = tk.Frame(f, bg=CLR_BG)
        btns.pack(fill="x", pady=8)
        tk.Button(btns, text="✅ Valider → Créer le Bon de Vente", command=self.valider_commande,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="❌ Rejeter la commande", command=self.rejeter_commande,
                  bg=CLR_RED, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)

    # ---------- Onglet Tournée ----------

    def _build_tab_tournee(self):
        f = self.tab_tournee

        info = lbl(f, "Pointages GPS effectués par les commerciaux en tournée (lecture seule).",
                    9, color=CLR_MUTED)
        info.pack(anchor="w", pady=(10, 5))

        cols = ["Date/Heure", "Code Client", "Nom Client", "Latitude", "Longitude", "Observations"]
        widths = [150, 100, 180, 100, 100, 220]
        tf, self.tree_tournee = make_tree(f, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)

    # ---------- Onglet Prospects ----------

    def _build_tab_prospects(self):
        f = self.tab_prospects

        filtre = tk.Frame(f, bg=CLR_BG)
        filtre.pack(fill="x", pady=(10, 5))
        lbl(filtre, "Statut :", 9, color=CLR_MUTED).pack(side="left", padx=(0, 5))
        self.filtre_statut_prospect = tk.StringVar(value="Nouveau")
        cb = ttk.Combobox(filtre, textvariable=self.filtre_statut_prospect, state="readonly",
                           values=["Tous", "Nouveau", "Converti"], width=15)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_prospects())

        cols = ["Code", "Nom", "Téléphone", "Adresse", "Wilaya", "Date", "Statut"]
        widths = [110, 160, 100, 160, 100, 100, 90]
        tf, self.tree_prospects = make_tree(f, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)

        btns = tk.Frame(f, bg=CLR_BG)
        btns.pack(fill="x", pady=8)
        tk.Button(btns, text="➕ Convertir en client", command=self.convertir_prospect,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)

    # ══════════════════════ CHARGEMENT DES DONNÉES ══════════════════════

    def refresh(self):
        self.refresh_commandes()
        self.refresh_tournee()
        self.refresh_prospects()

    def refresh_commandes(self):
        self.tree_cmd.delete(*self.tree_cmd.get_children())
        self.tree_lignes_cmd.delete(*self.tree_lignes_cmd.get_children())
        conn = get_conn()
        try:
            statut = self.filtre_statut_cmd.get()
            query = """SELECT cc.*, cl.nom AS nom_client
                       FROM commandes_clients cc
                       LEFT JOIN clients cl ON cc.client_id = cl.id
                       WHERE 1=1"""
            params = []
            if statut != "Toutes":
                query += " AND cc.statut=?"
                params.append(statut)
            query += " ORDER BY cc.date_commande DESC, cc.id DESC"
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                self.tree_cmd.insert("", "end", iid=r["id"], values=(
                    r["numero"], r["date_commande"], r["nom_client"] or "?",
                    f"{r['total_estime']:.2f}", r["statut"], r["observations"] or "",
                ))
        except sqlite3.OperationalError:
            # Table pas encore créée (API jamais démarrée) : rien à afficher.
            pass
        finally:
            conn.close()

    def _on_select_commande(self, event=None):
        self.tree_lignes_cmd.delete(*self.tree_lignes_cmd.get_children())
        sel = self.tree_cmd.selection()
        if not sel:
            return
        commande_id = sel[0]
        conn = get_conn()
        try:
            rows = conn.execute(
                """SELECT l.*, p.designation FROM lignes_commande_client l
                   LEFT JOIN produits p ON l.produit_id = p.id
                   WHERE l.commande_id=?""",
                (commande_id,),
            ).fetchall()
            for l in rows:
                self.tree_lignes_cmd.insert("", "end", values=(
                    l["designation"] or f"Produit #{l['produit_id']}",
                    l["quantite"], f"{l['prix_unitaire_estime']:.2f}", f"{l['total_estime']:.2f}",
                ))
        finally:
            conn.close()

    def refresh_tournee(self):
        self.tree_tournee.delete(*self.tree_tournee.get_children())
        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM tournee_pointages ORDER BY date_pointage DESC, id DESC LIMIT 200"
            ).fetchall()
            for r in rows:
                self.tree_tournee.insert("", "end", values=(
                    r["date_pointage"], r["code_client"] or "", r["nom_client"] or "",
                    f"{r['latitude']:.5f}" if r["latitude"] is not None else "",
                    f"{r['longitude']:.5f}" if r["longitude"] is not None else "",
                    r["observations"] or "",
                ))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    def refresh_prospects(self):
        self.tree_prospects.delete(*self.tree_prospects.get_children())
        conn = get_conn()
        try:
            statut = self.filtre_statut_prospect.get()
            query = "SELECT * FROM prospects_clients WHERE 1=1"
            params = []
            if statut != "Tous":
                query += " AND statut=?"
                params.append(statut)
            query += " ORDER BY date_creation DESC, id DESC"
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                self.tree_prospects.insert("", "end", iid=r["id"], values=(
                    r["code"], r["nom"], r["tel"] or "", r["adresse"] or "",
                    r["wilaya"] or "", r["date_creation"][:10], r["statut"],
                ))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    # ══════════════════════ ACTIONS : COMMANDES ══════════════════════

    def valider_commande(self):
        sel = self.tree_cmd.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez une commande à valider.")
            return
        commande_id = int(sel[0])

        conn = get_conn()
        try:
            cmd = conn.execute("SELECT * FROM commandes_clients WHERE id=?", (commande_id,)).fetchone()
            if not cmd:
                messagebox.showerror("Erreur", "Commande introuvable.")
                return
            if cmd["statut"] != "En attente":
                messagebox.showwarning("Impossible", f"Cette commande est déjà « {cmd['statut']} ».")
                return

            lignes = conn.execute(
                "SELECT * FROM lignes_commande_client WHERE commande_id=?", (commande_id,)
            ).fetchall()
            if not lignes:
                messagebox.showerror("Erreur", "Cette commande n'a aucune ligne.")
                return

            lignes_panier = [
                {
                    "produit_id": l["produit_id"],
                    "quantite": l["quantite"],
                    "prix": l["prix_unitaire_estime"],
                    "total": l["total_estime"],
                }
                for l in lignes
            ]
            total = sum(l["total"] for l in lignes_panier)

            client_nom = conn.execute(
                "SELECT nom FROM clients WHERE id=?", (cmd["client_id"],)
            ).fetchone()
            client_nom = client_nom["nom"] if client_nom else "?"

            if not messagebox.askyesno(
                "Confirmer la validation",
                f"Transformer la commande {cmd['numero']} ({client_nom}, {total:.2f}) "
                "en Bon de Vente réel ?\n\nLe stock sera décrémenté immédiatement.",
            ):
                return
        finally:
            conn.close()

        # ✅ Réutilise la même logique métier que le reste de l'app (vérif
        # stock, PMP, solde client) : aucune règle de vente dupliquée ici.
        success, result = valider_transaction_vente(cmd["client_id"], total, lignes_panier)

        if not success:
            messagebox.showerror("Échec de la validation", result)
            return

        conn = get_conn()
        try:
            bon = conn.execute("SELECT id FROM bons_vente WHERE numero=?", (result,)).fetchone()
            conn.execute(
                "UPDATE commandes_clients SET statut='Validée', bon_vente_id=? WHERE id=?",
                (bon["id"] if bon else None, commande_id),
            )
            conn.commit()
        finally:
            conn.close()

        messagebox.showinfo("Succès", f"Commande validée. Bon de vente {result} créé.")
        self.refresh_commandes()

    def rejeter_commande(self):
        sel = self.tree_cmd.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez une commande à rejeter.")
            return
        commande_id = int(sel[0])

        motif = simpledialog.askstring(
            "Rejeter la commande", "Motif du rejet (optionnel) :", parent=self
        )
        if motif is None:  # Annulé
            return

        conn = get_conn()
        try:
            cmd = conn.execute("SELECT statut, observations FROM commandes_clients WHERE id=?", (commande_id,)).fetchone()
            if not cmd:
                messagebox.showerror("Erreur", "Commande introuvable.")
                return
            if cmd["statut"] != "En attente":
                messagebox.showwarning("Impossible", f"Cette commande est déjà « {cmd['statut']} ».")
                return

            obs = cmd["observations"] or ""
            if motif:
                obs = (obs + f"\n[Rejet] {motif}").strip()
            conn.execute(
                "UPDATE commandes_clients SET statut='Rejetée', observations=? WHERE id=?",
                (obs, commande_id),
            )
            conn.commit()
        finally:
            conn.close()

        messagebox.showinfo("Commande rejetée", "Le client verra le statut « Rejetée » sur le portail.")
        self.refresh_commandes()

    # ══════════════════════ ACTIONS : PROSPECTS ══════════════════════

    # ══════════════════════ ACTIONS : PROSPECTS ══════════════════════

    def convertir_prospect(self):
        """
        Action déclenchée par le bouton 'Convertir en client'.
        Récupère le prospect sélectionné, le transfère dans la table 'clients'
        avec ses versements, ses commandes et son solde, puis actualise l'affichage.
        """
        sel = self.tree_prospects.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un prospect à convertir.")
            return

        prospect_id = int(sel[0])

        conn = get_conn()
        try:
            # 1. Récupérer le prospect (supporte 'prospects_clients' ou 'prospects_client')
            table_prospect = "prospects_clients"
            try:
                prospect = conn.execute(
                    f"SELECT * FROM {table_prospect} WHERE id = ?", (prospect_id,)
                ).fetchone()
            except sqlite3.OperationalError:
                table_prospect = "prospects_client"
                prospect = conn.execute(
                    f"SELECT * FROM {table_prospect} WHERE id = ?", (prospect_id,)
                ).fetchone()

            if not prospect:
                messagebox.showerror("Erreur", "Prospect introuvable dans la base.")
                return

            p = dict(prospect)

            if p.get("statut") == "Converti":
                messagebox.showinfo("Information", "Ce prospect a déjà été converti en client.")
                return

            if not messagebox.askyesno(
                "Confirmation",
                f"Voulez-vous convertir le prospect « {p.get('nom')} » en Client officiel ?\n\n"
                "Ses coordonnées, ses versements et son solde seront transférés dans la table Clients."
            ):
                return

            cursor = conn.cursor()

            # 2. Générer un code client officiel unique (ex: CLT-0005)
            last_id = cursor.execute("SELECT MAX(id) FROM clients").fetchone()[0] or 0
            code_client = f"CLT-{last_id + 1:04d}"

            # 3. Récupérer le solde du prospect s'il existe
            solde_prospect = float(p.get("solde", 0.0) or 0.0)

            # 4. Insérer le nouveau client dans la table 'clients'
            cursor.execute(
                """INSERT INTO clients (code, nom, tel, adresse, ville, solde)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    code_client,
                    p.get("nom", "Nouveau Client"),
                    p.get("tel", "") or "",
                    p.get("adresse", "") or "",
                    p.get("wilaya", "") or p.get("ville", "Algérie") or "Algérie",
                    solde_prospect,
                ),
            )
            nouveau_client_id = cursor.lastrowid

            # 5. Transférer tous les versements du prospect vers son nouveau compte client
            try:
                cursor.execute(
                    """UPDATE versements_clients 
                       SET client_id = ?, prospect_id = NULL 
                       WHERE prospect_id = ?""",
                    (nouveau_client_id, prospect_id),
                )
            except Exception:
                pass

            # 6. Transférer les commandes éventuelles du prospect
            try:
                cursor.execute(
                    """UPDATE commandes_clients 
                       SET client_id = ? 
                       WHERE prospect_id = ?""",
                    (nouveau_client_id, prospect_id),
                )
            except Exception:
                pass

            # 7. Transférer les pointages de visite GPS
            try:
                cursor.execute(
                    """UPDATE tournee_pointages 
                       SET client_id = ?, prospect_id = NULL 
                       WHERE prospect_id = ?""",
                    (nouveau_client_id, prospect_id),
                )
            except Exception:
                pass

            # 8. Mettre à jour le statut du prospect à 'Converti'
            cursor.execute(
                f"UPDATE {table_prospect} SET statut = 'Converti' WHERE id = ?",
                (prospect_id,),
            )

            conn.commit()

            messagebox.showinfo(
                "Succès",
                f"Le prospect « {p.get('nom')} » a été converti avec succès !\n\n"
                f"Nouveau Code Client : {code_client}\n"
                f"ID Client : {nouveau_client_id}"
            )

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur de conversion", f"Une erreur est survenue : {e}")
        finally:
            conn.close()

        # 9. Rafraîchir les tableaux pour afficher les statuts à jour
        self.refresh_prospects()