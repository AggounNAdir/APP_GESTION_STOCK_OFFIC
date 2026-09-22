from modules.core import *
from modules.bondialog import BonDialog
from modules.bondetaildialog import BonDetailDialog
from modules.boneditdialog import BonEditDialog
from modules.facturedialog import FactureDialog
from modules.ventecomptoirdialog import VenteComptoirDialog

class BonVentePage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self,bg=CLR_BG)
        hdr.pack(fill="x",padx=20,pady=(20,10))
        lbl(hdr,"🏷️  Bons de Vente",16,True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Bon", command=self.new_bon,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # ✅ AJOUT DU BOUTON IMPRIMER
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bons,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="📊 Exporter", command=self.export_bons,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🛒 Vente Comptoir", command=self.vente_comptoir,
            bg=CLR_ORANGE, fg="white", relief="flat",
            font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🧾 Créer Facture", command=self.creer_facture,
            bg=CLR_GREEN, fg="white", relief="flat",
            font=("Segoe UI",9,"bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)

        # 🔹 BARRE DE RECHERCHE ET FILTRES
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        
        # Recherche textuelle
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.sv = tk.StringVar()
        self.sv.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=20, textvariable=self.sv).pack(side="left", padx=8)

        # COMBOBOX FILTRE PAR CLIENT
        lbl(sf, "Client:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
        self.client_filter_var = tk.StringVar(value="Tous")
        self.client_filter_combo = combo(sf, [], width=25, textvariable=self.client_filter_var)
        self.client_filter_combo.pack(side="left", padx=5)
        self.client_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Charger la liste des clients
        self.load_clients_list()

        cols = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        widths = [120, 100, 200, 100, 80, 80, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)

        bf = tk.Frame(self,bg=CLR_BG)
        bf.pack(fill="x",padx=20,pady=(0,15))
        
        for txt, cmd, clr in [
            ("👁 Détail", self.view_bon, CLR_ACCENT),
            ("✏ Modifier", self.edit_bon, CLR_ORANGE),
            ("🗑 Supprimer", self.delete_bon, CLR_RED),
            ("🗑 Annuler", self.cancel_bon, CLR_RED)
        ]:
            tk.Button(bf, text=txt, command=cmd, bg=clr, fg="white", relief="flat",
                    font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    def get_bons_data(self, client_filter=None):
        """Récupérer les données des bons avec filtre client"""
        conn = get_conn()
        
        if client_filter and client_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    c.nom as client, 
                    b.total, 
                    b.statut,
                    CASE WHEN f.id IS NOT NULL THEN '✅ Oui' ELSE '❌ Non' END as facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id
                LEFT JOIN factures f ON b.id = f.bon_vente_id
                WHERE c.nom = ?
                ORDER BY b.date_bon DESC
            """, (client_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.numero, 
                    b.date_bon, 
                    c.nom as client, 
                    b.total, 
                    b.statut,
                    CASE WHEN f.id IS NOT NULL THEN '✅ Oui' ELSE '❌ Non' END as facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id
                LEFT JOIN factures f ON b.id = f.bon_vente_id
                ORDER BY b.date_bon DESC
            """).fetchall()
        
        conn.close()
        
        data = []
        total_general = 0
        for r in rows:
            # ✅ ACCÈS CORRECT avec le nom de la colonne
            total = r["total"]  # ✅ r["total"] est disponible
            total_general += total
            cartons = r["total_cartons"] if r["total_cartons"] is not None else 0
            cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
            
            data.append([
                r["numero"], 
                r["date_bon"], 
                r["client"], 
                f"{total:,.2f}", 
                r["statut"], 
                r["facture"],
                cartons_text
            ])
        
        # Ajouter la ligne de total en bas
        if data:
            data.append(["", "", "", "", "", "", ""])
            data.append(["", "", "TOTAL GENERAL", f"{total_general:,.2f} DA", "", "", ""])
        
        return data, total_general                
    def print_bons(self):
        """Imprimer les bons du client sélectionné avec total"""
        client_filter = self.client_filter_var.get()
        
        # ✅ Récupérer les données via get_bons_data()
        data, total_general = self.get_bons_data(client_filter)
        
        if not data or len(data) <= 1:
            messagebox.showinfo("Information", "Aucun bon de vente trouvé pour ce client")
            return
        
        if client_filter and client_filter != "Tous":
            title = f"LISTE DES BONS DE VENTE - {client_filter.upper()}"
        else:
            title = "LISTE DES BONS DE VENTE - TOUS LES CLIENTS"
        
        # ✅ En-têtes avec la colonne Cartons
        headers = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        
        footer_text = f"\n{'='*60}\nTOTAL GENERAL: {total_general:,.2f} DA\n{'='*60}\n"
        footer_text += f"Nombre de bons: {len(data)-2}\n"
        footer_text += f"Date d'impression: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        print_preview(data, title, headers, footer_text=footer_text)
    def export_bons(self):
        """Exporter les bons de vente en CSV ou HTML"""
        client_filter = self.client_filter_var.get()
        
        # ✅ Récupérer les données via get_bons_data()
        data, total_general = self.get_bons_data(client_filter)
        
        if not data or len(data) <= 1:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter")
            return
        
        # ✅ En-têtes avec la colonne Cartons
        headers = ["Numéro", "Date", "Client", "Total", "Statut", "Facturé", "Cartons"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="bons_vente.csv"
        )
        
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "BONS DE VENTE", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")
    def vente_comptoir(self):
        d = VenteComptoirDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def creer_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon de vente")
            return
        
        conn = get_conn()
        # Vérifier si une facture existe déjà
        existing = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if existing:
            messagebox.showwarning("", "Ce bon a déjà une facture associée")
            conn.close()
            return
        
        bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        # Ouvrir le dialogue de création de facture avec le bon pré-sélectionné
        d = FactureDialog(self, pre_selected_bon=dict(bon))
        self.wait_window(d)
        self.refresh()
    def load_clients_list(self):
        """Charge la liste des clients dans le combobox"""
        conn = get_conn()
        clients = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()
        conn.close()
        
        client_liste = ["Tous"] + [f"{c['nom']}" for c in clients]
        self.client_filter_combo['values'] = client_liste
        if client_liste:
            self.client_filter_var.set("Tous")

    def refresh(self):
        q = self.sv.get().lower()
        client_filter = self.client_filter_var.get()
        
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        
        # 🔹 REQUÊTE AVEC FILTRE CLIENT ET CALCUL DES CARTONS
        if client_filter != "Tous":
            rows = conn.execute("""
                SELECT 
                    b.*, 
                    c.nom as cnom,
                    (SELECT COUNT(*) FROM factures WHERE bon_vente_id = b.id) as a_facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id 
                WHERE c.nom = ?
                ORDER BY b.date_bon DESC, b.numero DESC
            """, (client_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT 
                    b.*, 
                    c.nom as cnom,
                    (SELECT COUNT(*) FROM factures WHERE bon_vente_id = b.id) as a_facture,
                    (SELECT COALESCE(SUM(lv.quantite / p.facteur_conversion), 0)
                    FROM lignes_vente lv 
                    JOIN produits p ON lv.produit_id = p.id 
                    WHERE lv.bon_id = b.id) as total_cartons
                FROM bons_vente b
                JOIN clients c ON b.client_id = c.id 
                ORDER BY b.date_bon DESC, b.numero DESC
            """).fetchall()
        conn.close()
        
        for r in rows:
            if q in r["numero"].lower() or q in r["cnom"].lower():
                facture_info = "✅ Oui" if r["a_facture"] > 0 else "❌ Non"
                cartons = r['total_cartons'] or 0
                cartons_text = f"{cartons:.2f} cartons" if cartons > 0 else "-"
                
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], 
                    r["date_bon"], 
                    r["cnom"],
                    f"{r['total']:.2f}", 
                    r["statut"], 
                    facture_info,
                    cartons_text  # ✅ Nouvelle colonne
                ))

    def new_bon(self):
        d = BonDialog(self,"vente")
        self.wait_window(d)
        self.refresh()

    def view_bon(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("","Sélectionnez un bon")
            return
        d = BonDetailDialog(self,"vente",sel[0])
        self.wait_window(d)

    def edit_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à modifier")
            return
        bon_id = sel[0]
        conn = get_conn()
        bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (bon_id,)).fetchone()
        if bon["statut"] == "Annulé":
            messagebox.showwarning("", "Impossible de modifier un bon annulé")
            conn.close()
            return
        # Vérifier si une facture existe
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (bon_id,)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible de modifier un bon qui a déjà une facture")
            conn.close()
            return
        lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.prix_vente 
                                FROM lignes_vente l
                                JOIN produits p ON l.produit_id = p.id
                                WHERE l.bon_id=?""", (bon_id,)).fetchall()
        conn.close()
        d = BonEditDialog(self, "vente", bon_id, dict(bon), lignes)
        self.wait_window(d)
        self.refresh()

    def delete_bon(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un bon à supprimer")
            return
        conn = get_conn()
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible de supprimer un bon qui a une facture associée")
            conn.close()
            return
        conn.close()
        
        if not messagebox.askyesno("Confirmation", 
                                "⚠️ Supprimer définitivement ce bon ?\n"
                                "Cette action est irréversible et ajustera le stock et les soldes."):
            return
        conn = get_conn()
        try:
            bon_id = sel[0]
            bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (bon_id,)).fetchone()
            lignes = conn.execute("SELECT * FROM lignes_vente WHERE bon_id=?", (bon_id,)).fetchall()
            if bon["statut"] != "Annulé":
                for l in lignes:
                    # ✅ CORRECTION : recalculer le coût du stock en même temps que la quantité
                    entree_stock_annulation_vente(
                        conn, l["produit_id"], l["quantite"],
                        document_type="bon_vente", document_id=bon_id,
                        motif="Suppression du bon de vente",
                    )
                # ✅ CORRECTION — ne pas toucher au solde COMPTOIR
                client = conn.execute("SELECT nom FROM clients WHERE id=?",
                                    (bon["client_id"],)).fetchone()
                if client and client["nom"] != "COMPTOIR":
                    conn.execute("UPDATE clients SET solde = solde - ? WHERE id=?", 
                            (bon["total"], bon["client_id"]))
            conn.execute("DELETE FROM lignes_vente WHERE bon_id=?", (bon_id,))
            conn.execute("DELETE FROM bons_vente WHERE id=?", (bon_id,))
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
    
        conn = get_conn()
        facture = conn.execute("SELECT id FROM factures WHERE bon_vente_id=?", (sel[0],)).fetchone()
        if facture:
            messagebox.showwarning("", "Impossible d'annuler un bon qui a une facture associée")
            conn.close()
            return
    
        if messagebox.askyesno("Annulation", "Annuler ce bon de vente ?"):
            bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (sel[0],)).fetchone()
            if bon["statut"] == "Annulé":
                messagebox.showinfo("", "Déjà annulé")
                conn.close()
                return
    
            lignes = conn.execute("SELECT * FROM lignes_vente WHERE bon_id=?", (sel[0],)).fetchall()
            for l in lignes:
                # ✅ CORRECTION
                entree_stock_annulation_vente(
                    conn, l["produit_id"], l["quantite"],
                    document_type="bon_vente", document_id=bon["id"],
                    motif="Annulation du bon de vente",
                )
    
            # ✅ CORRECTION : ne pas toucher au solde du client COMPTOIR
            client = conn.execute(
                "SELECT nom FROM clients WHERE id=?", (bon["client_id"],)
            ).fetchone()
            if client and client["nom"] != "COMPTOIR":
                conn.execute(
                    "UPDATE clients SET solde=solde-? WHERE id=?",
                    (bon["total"], bon["client_id"])
                )
    
            conn.execute("UPDATE bons_vente SET statut='Annulé' WHERE id=?", (sel[0],))
            conn.commit()
            conn.close()
            self.refresh()
 


# ========== DIALOGUE VENTE COMPTOIR ==========

