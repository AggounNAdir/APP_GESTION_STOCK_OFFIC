from modules.core import *

class RetourEditDialog(tk.Toplevel):
    """Dialogue de modification de retour - simplifié"""
    
    def __init__(self, parent, retour_type, retour_id):
        super().__init__(parent)
        self.retour_type = retour_type
        self.retour_id = retour_id
        # ✅ AJOUT — ces attributs manquaient
        self.table = "retours_vente" if retour_type == "vente" else "retours_achat"
        self.lignes_table = "lignes_retour_vente" if retour_type == "vente" else "lignes_retour_achat"
        
        self.title("Modifier Retour")
        self.configure(bg=CLR_BG)
        self.geometry("600x500")
        self._load_data()
        self._build()
        center_window(self, 600, 500)
    
    def _load_data(self):
        conn = get_conn()
        self.retour = conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (self.retour_id,)).fetchone()
        self.lignes = conn.execute(f"SELECT * FROM {self.lignes_table} WHERE retour_id=?", (self.retour_id,)).fetchall()
        conn.close()
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"✏ MODIFIER LE MOTIF", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="x", pady=10)
        
        # Numéro (non modifiable)
        row1 = tk.Frame(form_frame, bg=CLR_CARD)
        row1.pack(fill="x", pady=5)
        lbl(row1, "Numéro:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        lbl(row1, self.retour["numero"], 9, False, CLR_TEXT).pack(side="left", padx=10)
        
        # Motif
        row2 = tk.Frame(form_frame, bg=CLR_CARD)
        row2.pack(fill="x", pady=10)
        lbl(row2, "Motif:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        self.motif_var = tk.StringVar(value=self.retour["motif"] or "")
        entry(row2, width=50, textvariable=self.motif_var).pack(side="left", padx=10, fill="x", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def save(self):
        conn = get_conn()
        try:
            conn.execute(f"UPDATE {self.table} SET motif=? WHERE id=?", 
                       (self.motif_var.get().strip(), self.retour_id))
            conn.commit()
            messagebox.showinfo("Succès", "Motif modifié")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()

