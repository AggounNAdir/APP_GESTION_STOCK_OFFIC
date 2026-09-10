from modules.core import *
from modules.facturedialog import FactureDialog
from modules.factureeditdialog import FactureEditDialog
from modules.facturedetaildialog import FactureDetailDialog

class FacturePage(tk.Frame):
    """Page de gestion des factures"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "🧾  Gestion des Factures", 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouvelle Facture", command=self.nouvelle_facture,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        # Filtre par statut
        lbl(sf, "Statut:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.statut_var = tk.StringVar(value="Tous")
        statut_combo = combo(sf, ["Tous", "Émise", "Payée", "Annulée"], width=12, textvariable=self.statut_var)
        statut_combo.pack(side="left", padx=5)
        statut_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        cols = ["Numéro", "Date", "Client", "Bon Vente", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        widths = [120, 100, 200, 100, 100, 60, 120, 100, 100]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_facture,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_facture,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_facture,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_factures,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="📊 Exporter", command=self.export_factures,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        # Double-clic pour modifier
        self.tree.bind("<Double-1>", lambda e: self.edit_facture())
    
    def refresh(self):
        q = self.search_var.get().lower()
        statut = self.statut_var.get()
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if statut == "Tous":
            rows = conn.execute("""
                SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
                FROM factures f
                JOIN clients c ON f.client_id = c.id
                JOIN bons_vente bv ON f.bon_vente_id = bv.id
                ORDER BY f.date_facture DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
                FROM factures f
                JOIN clients c ON f.client_id = c.id
                JOIN bons_vente bv ON f.bon_vente_id = bv.id
                WHERE f.statut = ?
                ORDER BY f.date_facture DESC
            """, (statut,)).fetchall()
        conn.close()
        
        for r in rows:
            if q in r["numero"].lower() or q in r["client_nom"].lower():
                # Couleur selon le statut
                tag = None
                if r["statut"] == "Payée":
                    tag = "payee"
                elif r["statut"] == "Annulée":
                    tag = "annulee"
                
                self.tree.insert("", "end", iid=r["id"], values=(
                    r["numero"], r["date_facture"], r["client_nom"],
                    r["bon_numero"], f"{r['total_ht']:,.2f}", 
                    f"{r['tva']:.0f}%", f"{r['total_ttc']:,.2f}",
                    r["statut"], r["date_echeance"] or ""
                ), tags=(tag,) if tag else ())
        
        self.tree.tag_configure("payee", foreground=CLR_GREEN)
        self.tree.tag_configure("annulee", foreground=CLR_RED)
    
    def nouvelle_facture(self):
        d = FactureDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def view_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture")
            return
        d = FactureDetailDialog(self, sel[0])
        self.wait_window(d)
    
    def edit_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture à modifier")
            return
        d = FactureEditDialog(self, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_facture(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une facture à supprimer")
            return
        
        if messagebox.askyesno("Confirmation", "⚠️ Supprimer définitivement cette facture ?\nCette action est irréversible."):
            conn = get_conn()
            try:
                facture_id = sel[0]
                conn.execute("DELETE FROM facture_tva_details WHERE facture_id=?", (facture_id,))
                conn.execute("DELETE FROM factures WHERE id=?", (facture_id,))
                conn.commit()
                messagebox.showinfo("Succès", "Facture supprimée")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()
    
    def get_factures_data(self):
        """Récupérer les données des factures pour export"""
        conn = get_conn()
        rows = conn.execute("""
            SELECT f.numero, f.date_facture, c.nom as client, 
                   f.total_ht, f.tva, f.total_ttc, f.statut, f.date_echeance
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            ORDER BY f.date_facture DESC
        """).fetchall()
        conn.close()
        
        data = []
        for r in rows:
            data.append([
                r["numero"], r["date_facture"], r["client"],
                f"{r['total_ht']:,.2f}", f"{r['tva']:.0f}%",
                f"{r['total_ttc']:,.2f}", r["statut"], r["date_echeance"] or ""
            ])
        return data
    
    def print_factures(self):
        data = self.get_factures_data()
        headers = ["Numéro", "Date", "Client", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        print_preview(data, "LISTE DES FACTURES", headers)
    
    def export_factures(self):
        data = self.get_factures_data()
        headers = ["Numéro", "Date", "Client", "Total HT", "TVA", "Total TTC", "Statut", "Échéance"]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="factures.csv"
        )
        if filename:
            if filename.endswith('.html'):
                export_to_html(data, filename, "LISTE DES FACTURES", headers)
                if messagebox.askyesno("Ouverture", "Fichier créé. Voulez-vous l'ouvrir ?"):
                    webbrowser.open(filename)
            else:
                export_to_csv(data, filename, headers)
                messagebox.showinfo("Succès", f"Exporté vers {filename}")


