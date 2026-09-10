from modules.core import *
from modules.versementdialog import VersementDialog
from modules.versementdetaildialog import VersementDetailDialog
from modules.versementeditdialog import VersementEditDialog

class VersementPage(tk.Frame):
    """Page de gestion des versements clients/fournisseurs"""
    
    def __init__(self, parent, vers_type="client"):
        self.vers_type = vers_type  # "client" ou "fournisseur"
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.prefix = "VC" if vers_type == "client" else "VF"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        title = f"💳 Versements {self.tiers_label}s" if self.vers_type == "client" else f"💳 Versements Fournisseurs"
        lbl(hdr, title, 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Versement", command=self.nouveau_versement,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Filtres
        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        entry(sf, width=30, textvariable=self.search_var).pack(side="left", padx=8)
        
        lbl(sf, f"{self.tiers_label}:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.tiers_filter_var = tk.StringVar(value="Tous")
        self.load_tiers_list()
        tiers_combo = combo(sf, ["Tous"] + self.tiers_list, width=20, textvariable=self.tiers_filter_var)
        tiers_combo.pack(side="left", padx=5)
        tiers_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        lbl(sf, "Mode:", color=CLR_MUTED).pack(side="left", padx=(20,5))
        self.mode_filter_var = tk.StringVar(value="Tous")
        mode_combo = combo(sf, ["Tous", "Espèces", "Chèque", "Virement", "Carte"], width=12, textvariable=self.mode_filter_var)
        mode_combo.pack(side="left", padx=5)
        mode_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        # Tableau
        cols = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        widths = [120, 100, 200, 120, 100, 150]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="👁 Détail", command=self.view_versement,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_versement,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_versement,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🖨 Imprimer", command=self.print_versements,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def load_tiers_list(self):
        conn = get_conn()
        tiers = conn.execute(f"SELECT nom FROM {self.tiers_table} ORDER BY nom").fetchall()
        conn.close()
        self.tiers_list = [t["nom"] for t in tiers]
    
    def refresh(self):
        q = self.search_var.get().lower()
        tiers_filter = self.tiers_filter_var.get()
        mode_filter = self.mode_filter_var.get()
        
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        if self.vers_type == "client":
            query = f"""
                SELECT v.*, c.nom as tiers_nom
                FROM {self.table} v
                JOIN {self.tiers_table} c ON v.client_id = c.id
                ORDER BY v.date_vers DESC
            """
        else:
            query = f"""
                SELECT v.*, f.nom as tiers_nom
                FROM {self.table} v
                JOIN {self.tiers_table} f ON v.fournisseur_id = f.id
                ORDER BY v.date_vers DESC
            """
        rows = conn.execute(query).fetchall()
        conn.close()
        
        for r in rows:
            if q and q not in r["numero"].lower() and q not in r["tiers_nom"].lower():
                continue
            if tiers_filter != "Tous" and r["tiers_nom"] != tiers_filter:
                continue
            if mode_filter != "Tous" and r["mode"] != mode_filter:
                continue
            
            self.tree.insert("", "end", iid=r["id"], values=(
                r["numero"], r["date_vers"], r["tiers_nom"],
                f"{r['montant']:,.2f} DA", r["mode"], r["reference"] or ""
            ))
    
    def nouveau_versement(self):
        d = VersementDialog(self, self.vers_type)
        self.wait_window(d)
        self.load_tiers_list()
        self.refresh()
    
    def view_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        d = VersementDetailDialog(self, self.vers_type, sel[0])
        self.wait_window(d)
    
    def edit_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        d = VersementEditDialog(self, self.vers_type, sel[0])
        self.wait_window(d)
        self.refresh()
    
    def delete_versement(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un versement")
            return
        
        if messagebox.askyesno("Confirmation", "⚠️ Supprimer ce versement ?\nLe solde sera recalculé."):
            conn = get_conn()
            try:
                vers_id = sel[0]
                # Récupérer les infos avant suppression
                if self.vers_type == "client":
                    vers = conn.execute(f"SELECT client_id, montant FROM {self.table} WHERE id=?", (vers_id,)).fetchone()
                    if vers:
                        # Recalculer le solde client
                        conn.execute(f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?", 
                                   (vers["montant"], vers["client_id"]))
                else:
                    vers = conn.execute(f"SELECT fournisseur_id, montant FROM {self.table} WHERE id=?", (vers_id,)).fetchone()
                    if vers:
                        conn.execute(f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?", 
                                   (vers["montant"], vers["fournisseur_id"]))
                
                conn.execute(f"DELETE FROM {self.table} WHERE id=?", (vers_id,))
                conn.commit()
                messagebox.showinfo("Succès", "Versement supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                conn.rollback()
            finally:
                conn.close()
    
    def print_versements(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            data.append(values)
        
        headers = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        print_preview(data, f"LISTE DES VERSEMENTS {self.tiers_label.upper()}S", headers)


