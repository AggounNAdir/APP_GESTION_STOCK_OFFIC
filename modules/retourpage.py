from modules.core import *
from modules.retourdetaildialog import RetourDetailDialog
from modules.retourdialog import RetourDialog
from modules.retoureditdialog import RetourEditDialog

class RetourPage(tk.Frame):
    """Page de gestion des retours (vente/achat)"""
    
    def __init__(self, parent, retour_type="vente"):
        self.retour_type = retour_type  # "vente" ou "achat"
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        self.bons_table = "bons_vente" if retour_type == "vente" else "bons_achat"
        self.tiers_table = "clients" if retour_type == "vente" else "fournisseurs"
        self.produits_table = "produits"
        self.prefix = "RV" if retour_type == "vente" else "RA"
        self.tiers_label = "Client" if retour_type == "vente" else "Fournisseur"
        
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        title = f"↩️ Retours {self.tiers_label}s" if self.retour_type == "vente" else "↩️ Retours Fournisseurs"
        lbl(hdr, title, 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Retour", command=self.nouveau_retour,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Recherche
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        # Tableau
        cols = ["Numéro", "Date", self.tiers_label, "Total", "Motif", "Bon associé"]
        widths = [120, 100, 200, 100, 150, 120]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_retour,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_retour,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_retour,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_retours,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def refresh(self):
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if self.retour_type == "vente":
            query = f"""
                SELECT r.*, c.nom as tiers_nom, bv.numero as bon_numero
                FROM {self.table} r
                JOIN {self.tiers_table} c ON r.client_id = c.id
                LEFT JOIN {self.bons_table} bv ON r.bon_vente_id = bv.id
                ORDER BY r.date_retour DESC
            """
        else:
            query = f"""
                SELECT r.*, f.nom as tiers_nom, ba.numero as bon_numero
                FROM {self.table} r
                JOIN {self.tiers_table} f ON r.fournisseur_id = f.id
                LEFT JOIN {self.bons_table} ba ON r.bon_achat_id = ba.id
                ORDER BY r.date_retour DESC
            """
        rows = conn.execute(query).fetchall()
        conn.close()
        
        for r in rows:
            if q and q not in r["numero"].lower() and q not in r["tiers_nom"].lower():
                continue
            
            self.tree.insert("", "end", iid=r["id"], values=(
                r["numero"], r["date_retour"], r["tiers_nom"],
                f"{r['total']:,.2f} DA", r["motif"] or "-", r["bon_numero"] or "-"
            ))
    
    def nouveau_retour(self):
        d = RetourDialog(self, self.retour_type)
        self.wait_window(d)
        self.refresh()
    
    def view_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return
        d = RetourDetailDialog(self, self.retour_type, sel[0])
        self.wait_window(d)
    
    def edit_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return
        d = RetourEditDialog(self, self.retour_type, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_retour(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un retour")
            return

        if not messagebox.askyesno("Confirmation", "⚠️ Supprimer ce retour ?\nLe stock sera recalculé."):
            return

        conn = get_conn()
        try:
            retour_id = sel[0]

            # Récupérer le retour AVANT de supprimer les lignes
            retour = conn.execute(
                f"SELECT * FROM {self.table} WHERE id=?", (retour_id,)
            ).fetchone()

            lignes = conn.execute(
                f"SELECT * FROM {self.lignes_table} WHERE retour_id=?", (retour_id,)
            ).fetchall()

            for l in lignes:
                if self.retour_type == "vente":
                    # ✅ CORRECTION : supprimer un retour vente = annuler ce retour
                    # Le retour avait remis les articles EN stock → on les ressort
                    recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])
                    
                    # Recalculer le PMP après la sortie
                    produit = conn.execute(
                        "SELECT stock_actuel, cout_total_stock FROM produits WHERE id=?",
                        (l["produit_id"],)
                    ).fetchone()
                    if produit["stock_actuel"] > 0:
                        nouveau_pmp = produit["cout_total_stock"] / produit["stock_actuel"]
                        conn.execute(
                            "UPDATE produits SET prix_moyen_pondere = ? WHERE id=?",
                            (nouveau_pmp, l["produit_id"])
                        )
                    else:
                        conn.execute(
                            "UPDATE produits SET prix_moyen_pondere = 0, cout_total_stock = 0 WHERE id=?",
                            (l["produit_id"],)
                        )

                else:
                    # ✅ CORRECTION : supprimer un retour achat = annuler ce retour
                    # Le retour avait retiré les articles du stock → on les remet
                    nouveau_pmp, nouveau_cout = calculer_pmp(
                        conn, l["produit_id"], l["quantite"], l["prix_unitaire"]
                    )
                    conn.execute(
                        """UPDATE produits
                        SET stock_actuel       = stock_actuel + ?,
                            prix_moyen_pondere = ?,
                            cout_total_stock   = ?
                        WHERE id = ?""",
                        (l["quantite"], nouveau_pmp, nouveau_cout, l["produit_id"])
                    )

            # ✅ CORRECTION : ajuster le solde dans le bon sens selon le type
            if self.retour_type == "vente":
                # Le retour avait diminué le solde client → supprimer le retour
                # remet le client débiteur → solde remonte
                conn.execute(
                    f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?",
                    (retour["total"], retour["client_id"])
                )
            else:
                # Le retour avait diminué le solde fournisseur → supprimer le retour
                # remet le fournisseur créditeur → solde remonte
                conn.execute(
                    f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?",
                    (retour["total"], retour["fournisseur_id"])
                )

            # Supprimer les lignes puis le retour
            conn.execute(f"DELETE FROM {self.lignes_table} WHERE retour_id=?", (retour_id,))
            conn.execute(f"DELETE FROM {self.table} WHERE id=?", (retour_id,))

            conn.commit()
            messagebox.showinfo("Succès", "Retour supprimé et stock recalculé")
            self.refresh()

        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def print_retours(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        headers = ["Numéro", "Date", self.tiers_label, "Total", "Motif", "Bon associé"]
        print_preview(data, f"LISTE DES RETOURS", headers)

