from modules.core import *

class VersementDetailDialog(tk.Toplevel):
    """Dialogue de détail de versement"""
    
    def __init__(self, parent, vers_type, vers_id):
        super().__init__(parent)
        self.vers_type = vers_type
        self.vers_id = vers_id
        self.table = "versements_clients" if vers_type == "client" else "versements_fournisseurs"
        self.tiers_table = "clients" if vers_type == "client" else "fournisseurs"
        self.tiers_label = "Client" if vers_type == "client" else "Fournisseur"
        
        self.title(f"Détail Versement - {self.tiers_label}")
        self.configure(bg=CLR_BG)
        self.geometry("600x400")
        self._load_data()
        self._build()
        center_window(self, 600, 400)
    
    def _load_data(self):
        conn = get_conn()
        if self.vers_type == "client":
            self.versement = conn.execute(f"""
                SELECT v.*, c.nom as tiers_nom, c.solde
                FROM {self.table} v
                JOIN {self.tiers_table} c ON v.client_id = c.id
                WHERE v.id = ?
            """, (self.vers_id,)).fetchone()
        else:
            self.versement = conn.execute(f"""
                SELECT v.*, f.nom as tiers_nom, f.solde
                FROM {self.table} v
                JOIN {self.tiers_table} f ON v.fournisseur_id = f.id
                WHERE v.id = ?
            """, (self.vers_id,)).fetchone()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"📄 DÉTAIL VERSEMENT", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        info_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        info_frame.pack(fill="x", pady=10)
        
        details = [
            ("Numéro:", self.versement["numero"]),
            ("Date:", self.versement["date_vers"]),
            (f"{self.tiers_label}:", self.versement["tiers_nom"]),
            ("Montant:", f"{self.versement['montant']:,.2f} DA"),
            ("Mode:", self.versement["mode"]),
            ("Référence:", self.versement["reference"] or "-"),
            ("Solde après versement:", f"{self.versement['solde']:,.2f} DA"),
        ]
        
        for i, (label, value) in enumerate(details):
            row = tk.Frame(info_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=4)
            lbl(row, label, 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            lbl(row, str(value), 9, False, CLR_TEXT).pack(side="left", padx=5)
        
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_versement,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="left", padx=10, expand=True)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2").pack(side="right", padx=10)
    
    def print_versement(self):
        data = [[
            self.versement["numero"],
            self.versement["date_vers"],
            self.versement["tiers_nom"],
            f"{self.versement['montant']:,.2f} DA",
            self.versement["mode"],
            self.versement["reference"] or "-"
        ]]
        headers = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
        print_preview(data, f"VERSEMENT N°{self.versement['numero']}", headers)

