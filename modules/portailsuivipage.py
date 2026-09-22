"""
Écran de supervision de la Tournée Vendeur & Prospects (Silwane Androway).

Affiche en direct depuis SQLite (gestion_stock.db) :
  - Uniquement les commandes passées pour les Prospects (table commandes_prospects)
  - Les pointages GPS effectués sur le terrain

Intègre également, sous forme d'onglets, les pages autonomes :
  - Prospects (ProspectsPage) : recherche, filtre par statut, conversion en
    client officiel, suppression
  - Commandes Portail (CommandesClientsPage)
  - Vendeurs (VendeurPage)
"""
import sqlite3
from modules.core import *
from modules.stock_service import valider_transaction_vente
from modules.commandesclientpage import CommandesClientsPage
from modules.prospectspage import ProspectsPage
from modules.vendeurpage import VendeurPage


class PortailSuiviPage(tk.Frame):
    """Page de supervision 100% dédiée aux Prospects et à la Tournée Vendeur."""

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        # Pages intégrées (None si leur création a échoué)
        self.page_prospects_vendeurs = None
        self.page_cmd_portail = None
        self.page_vendeurs = None
        self._build()
        self.refresh()

    # ══════════════════════ CONSTRUCTION ══════════════════════

    def _build(self):
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(fill="x", padx=20, pady=(15, 5))
        lbl(header, "🎯 Suivi Tournée Vendeur & Prospects", 16, True, CLR_ACCENT).pack(side="left")
        tk.Button(header, text="🔄 Actualiser", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=5, cursor="hand2").pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_commandes = tk.Frame(self.notebook, bg=CLR_BG)
        self.tab_tournee = tk.Frame(self.notebook, bg=CLR_BG)
        # Onglet unique Prospects (ex « Fiches Prospects » + « Prospects Vendeurs »)
        self.tab_prospects_vendeurs = tk.Frame(self.notebook, bg=CLR_BG)
        # Pages déplacées depuis le menu latéral
        self.tab_cmd_portail = tk.Frame(self.notebook, bg=CLR_BG)
        self.tab_vendeurs = tk.Frame(self.notebook, bg=CLR_BG)

        self.notebook.add(self.tab_commandes, text="🛒 Commandes Prospects")
        self.notebook.add(self.tab_tournee, text="📍 Tournée Terrain (GPS)")
        self.notebook.add(self.tab_prospects_vendeurs, text="🎯 Prospects")
        self.notebook.add(self.tab_cmd_portail, text="📩 Commandes Portail")
        self.notebook.add(self.tab_vendeurs, text="👔 Vendeurs")

        self._build_tab_commandes()
        self._build_tab_tournee()
        self._build_embedded_tabs()

    # ---------- Onglets intégrés (pages existantes) ----------

    def _build_embedded_tabs(self):
        self.page_prospects_vendeurs = self._embed(self.tab_prospects_vendeurs, ProspectsPage)
        self.page_cmd_portail = self._embed(self.tab_cmd_portail, CommandesClientsPage)
        self.page_vendeurs = self._embed(self.tab_vendeurs, VendeurPage)

    def _embed(self, container, page_cls):
        """Instancie une page existante dans un onglet.

        La page est créée dans un Frame conteneur : elle garde ainsi son propre
        pack()/layout sans entrer en conflit avec le Notebook. Si sa création
        échoue, l'erreur s'affiche dans l'onglet sans casser le reste du suivi.
        """
        try:
            page = page_cls(container)
            page.pack(fill="both", expand=True)
            return page
        except Exception as e:
            print(f"Erreur chargement onglet {page_cls.__name__}: {e}")
            lbl(container, f"⚠️ Impossible de charger cet onglet :\n{e}",
                10, color=CLR_RED).pack(padx=20, pady=20, anchor="w")
            return None

    def _refresh_embedded(self):
        if self.page_prospects_vendeurs:
            self.page_prospects_vendeurs.refresh()
        if self.page_cmd_portail:
            self.page_cmd_portail.load_commandes()
        if self.page_vendeurs:
            # refresh_list() vide l'arbre et ferait perdre `selected_id` (le
            # formulaire resterait rempli mais un « Enregistrer » ferait un
            # INSERT au lieu d'un UPDATE) : on restaure donc la sélection.
            sid = self.page_vendeurs.selected_id
            self.page_vendeurs.refresh_list()
            if sid and self.page_vendeurs.tree.exists(str(sid)):
                self.page_vendeurs.tree.selection_set(str(sid))

    # ---------- Onglet Commandes Prospects ----------

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

        cols = ["N° Commande", "Date", "Prospect", "Montant Total", "Statut", "Observations"]
        widths = [140, 100, 200, 120, 100, 230]
        tf, self.tree_cmd = make_tree(f, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)
        self.tree_cmd.bind("<<TreeviewSelect>>", self._on_select_commande)

        # Détail des lignes de la commande prospect avec affichage clair du colisage
        detail_frame = tk.LabelFrame(f, text="Articles commandés par le prospect",
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 9, "bold"))
        detail_frame.pack(fill="x", pady=5)
        cols2 = ["Produit", "Qté Commandée", "Conditionnement", "Prix Unitaire", "Total Ligne"]
        tf2, self.tree_lignes_cmd = make_tree(detail_frame, cols2, [210, 100, 110, 110, 120])
        tf2.pack(fill="x", padx=5, pady=5)
        self.tree_lignes_cmd.configure(height=4)

        btns = tk.Frame(f, bg=CLR_BG)
        btns.pack(fill="x", pady=8)
        tk.Button(btns, text="✅ Valider la commande (Créer Bon de Vente)", command=self.valider_commande,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="❌ Rejeter la commande", command=self.rejeter_commande,
                  bg=CLR_RED, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)

    # ---------- Onglet Tournée ----------

    def _build_tab_tournee(self):
        f = self.tab_tournee
        info = lbl(f, "Pointages GPS effectués par les vendeurs sur le terrain.",
                   9, color=CLR_MUTED)
        info.pack(anchor="w", pady=(10, 5))

        cols = ["Date/Heure", "Code Prospect", "Nom Établissement", "Latitude", "Longitude", "Observations"]
        widths = [140, 110, 180, 90, 90, 220]
        tf, self.tree_tournee = make_tree(f, cols, widths)
        tf.pack(fill="both", expand=True, pady=5)

    # ══════════════════════ CHARGEMENT DES DONNÉES ══════════════════════

    def refresh(self):
        self.refresh_commandes()
        self.refresh_tournee()
        self._refresh_embedded()

    def refresh_commandes(self):
        """Charge EXCLUSIVEMENT les commandes depuis la table commandes_prospects."""
        self.tree_cmd.delete(*self.tree_cmd.get_children())
        self.tree_lignes_cmd.delete(*self.tree_lignes_cmd.get_children())
        conn = get_conn()
        try:
            statut = self.filtre_statut_cmd.get()
            query = """
                SELECT cp.*, 
                       COALESCE(p.nom, 'Prospect #' || cp.prospect_id) AS nom_prospect
                FROM commandes_prospects cp
                LEFT JOIN prospects_clients p ON cp.prospect_id = p.id
                WHERE 1=1
            """
            params = []
            if statut != "Toutes":
                query += " AND cp.statut=?"
                params.append(statut)
            query += " ORDER BY cp.date_commande DESC, cp.id DESC"
            
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                col_keys = r.keys()
                if "montant_total" in col_keys and r["montant_total"] is not None:
                    montant = float(r["montant_total"])
                elif "total_estime" in col_keys and r["total_estime"] is not None:
                    montant = float(r["total_estime"])
                else:
                    montant = 0.0

                obs = str(r["observations"] or "")
                nom_affiche = r["nom_prospect"]
                if "[Prospect:" in obs:
                    try:
                        nom_affiche = obs.split("[Prospect:")[1].split("]")[0].strip()
                    except Exception:
                        pass

                self.tree_cmd.insert("", "end", iid=r["id"], values=(
                    r["numero"],
                    str(r["date_commande"])[:10],
                    nom_affiche,
                    f"{montant:.2f} DA",
                    r["statut"],
                    obs,
                ))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    def _on_select_commande(self, event=None):
        """Affiche les lignes avec indication claire du produit, de la quantité et du montant direct."""
        self.tree_lignes_cmd.delete(*self.tree_lignes_cmd.get_children())
        sel = self.tree_cmd.selection()
        if not sel:
            return
        commande_id = int(sel[0])

        conn = get_conn()
        try:
            rows = conn.execute(
                """SELECT l.*, p.designation,
                          COALESCE(p.facteur_conversion, 1) as facteur_produit,
                          COALESCE(p.unite, 'U') as unite_produit
                   FROM lignes_commande_prospect l
                   LEFT JOIN produits p ON l.produit_id = p.id
                   WHERE l.commande_id=?""",
                (commande_id,),
            ).fetchall()

            for l in rows:
                col_keys = l.keys()
                qte = float(l["quantite"] or 0)
                prix = float(l["prix_unitaire"] if "prix_unitaire" in col_keys else (l["prix_unitaire_estime"] if "prix_unitaire_estime" in col_keys else 0.0))
                total_direct = float(l["total"] if "total" in col_keys else (l["total_estime"] if "total_estime" in col_keys else (qte * prix)))
                
                facteur = float(l["facteur_produit"] if "facteur_produit" in col_keys and l["facteur_produit"] else 1.0)
                unite = str(l["unite_produit"] if "unite_produit" in col_keys and l["unite_produit"] else "Pièce")
                
                cond_text = f"x{int(facteur) if facteur.is_integer() else facteur} ({unite})" if facteur > 1 else unite

                self.tree_lignes_cmd.insert("", "end", values=(
                    l["designation"] or f"Produit #{l['produit_id']}",
                    f"{qte:g}",
                    cond_text,
                    f"{prix:.2f} DA",
                    f"{total_direct:.2f} DA",
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
                    str(r["date_pointage"])[:16],
                    r["code_client"] or "",
                    r["nom_client"] or "",
                    f"{r['latitude']:.5f}" if r["latitude"] is not None else "",
                    f"{r['longitude']:.5f}" if r["longitude"] is not None else "",
                    r["observations"] or "",
                ))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    # ══════════════════════ ACTIONS : COMMANDES PROSPECTS ══════════════════════

    def valider_commande(self):
        """Valide la commande prospect en créant automatiquement un client s'il ne l'est pas encore."""
        sel = self.tree_cmd.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez une commande prospect à valider.")
            return
        commande_id = int(sel[0])

        conn = get_conn()
        try:
            cmd = conn.execute("SELECT * FROM commandes_prospects WHERE id=?", (commande_id,)).fetchone()
            if not cmd:
                messagebox.showerror("Erreur", "Commande prospect introuvable.")
                return
            if cmd["statut"] != "En attente":
                messagebox.showwarning("Impossible", f"Cette commande est déjà « {cmd['statut']} ».")
                return

            rows_lignes = conn.execute(
                """SELECT l.*, COALESCE(p.facteur_conversion, 1) as facteur_produit
                   FROM lignes_commande_prospect l
                   LEFT JOIN produits p ON l.produit_id = p.id
                   WHERE l.commande_id=?""",
                (commande_id,)
            ).fetchall()

            if not rows_lignes:
                messagebox.showerror("Erreur", "Cette commande n'a aucune ligne.")
                return

            lignes_panier = []
            for l in rows_lignes:
                col_keys = l.keys()
                qte = float(l["quantite"] or 0)
                facteur = float(l["facteur_produit"] if "facteur_produit" in col_keys and l["facteur_produit"] else 1.0)
                if facteur <= 0:
                    facteur = 1.0

                prix = float(l["prix_unitaire"] if "prix_unitaire" in col_keys and l["prix_unitaire"] is not None 
                             else (l["prix_unitaire_estime"] if "prix_unitaire_estime" in col_keys and l["prix_unitaire_estime"] is not None else 0.0))
                tot = float(l["total"] if "total" in col_keys and l["total"] is not None 
                            else (l["total_estime"] if "total_estime" in col_keys and l["total_estime"] is not None else (qte * prix)))

                lignes_panier.append({
                    "produit_id": l["produit_id"],
                    "quantite": qte,
                    "prix": prix,
                    "total": tot,
                })

            total = sum(l["total"] for l in lignes_panier)

            prospect = conn.execute("SELECT * FROM prospects_clients WHERE id=?", (cmd["prospect_id"],)).fetchone()
            nom_p = prospect["nom"] if prospect else "Prospect"

            client_id = prospect["client_id"] if (prospect and "client_id" in prospect.keys() and prospect["client_id"]) else None

            if not client_id:
                if not messagebox.askyesno(
                    "Validation Commande Prospect",
                    f"La commande {cmd['numero']} ({total:.2f} DA) appartient au prospect « {nom_p} ».\n\n"
                    "Convertir automatiquement ce prospect en Client officiel pour générer le Bon de Vente ?",
                ):
                    return

                # Créer le client officiel
                last_id = conn.execute("SELECT MAX(id) FROM clients").fetchone()[0] or 0
                code_client = f"CLT-{last_id + 1:04d}"
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO clients (code, nom, tel, adresse, ville, solde)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        code_client,
                        nom_p,
                        prospect["tel"] if prospect else "",
                        prospect["adresse"] if prospect else "",
                        prospect["wilaya"] if prospect else "Algérie",
                        0.0,
                    ),
                )
                client_id = cur.lastrowid
                cur.execute(
                    "UPDATE prospects_clients SET statut='Converti', client_id=? WHERE id=?",
                    (client_id, cmd["prospect_id"]),
                )
                conn.commit()

        finally:
            conn.close()

        # Valider la vente (décrémentation stock + bon de vente)
        success, result = valider_transaction_vente(client_id, total, lignes_panier)

        if not success:
            messagebox.showerror("Échec de la validation", result)
            return

        conn = get_conn()
        try:
            conn.execute(
                "UPDATE commandes_prospects SET statut='Validée' WHERE id=?",
                (commande_id,),
            )
            conn.commit()
        finally:
            conn.close()

        messagebox.showinfo("Succès", f"Commande validée ! Bon de vente {result} créé avec succès.")
        self.refresh_commandes()
        # La validation peut convertir un prospect en client : on met à jour l'onglet Prospects
        if self.page_prospects_vendeurs:
            self.page_prospects_vendeurs.refresh()

    def rejeter_commande(self):
        """Rejette une commande prospect."""
        sel = self.tree_cmd.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez une commande à rejeter.")
            return
        commande_id = int(sel[0])

        motif = simpledialog.askstring("Rejeter la commande", "Motif du rejet :", parent=self)
        if motif is None:
            return

        conn = get_conn()
        try:
            cmd = conn.execute("SELECT statut, observations FROM commandes_prospects WHERE id=?", (commande_id,)).fetchone()
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
                "UPDATE commandes_prospects SET statut='Rejetée', observations=? WHERE id=?",
                (obs, commande_id),
            )
            conn.commit()
        finally:
            conn.close()

        messagebox.showinfo("Commande rejetée", "La commande prospect a été marquée comme « Rejetée ».")
        self.refresh_commandes()
