from modules.core import *
from modules.profildialog import ProfilDialog

class GestionProfilsPage(tk.Frame):
    """Page de gestion des profils entreprise"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "🏢 Gestion des Profils Entreprise", 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Profil", command=self.nouveau_profil,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Configuration des types de documents
        config_frame = tk.LabelFrame(self, text="📄 Association Profil → Document", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        
        self.doc_types = [
            ("Facture", "facture"),
            ("Bon de livraison", "bon_livraison"),
            ("Devis", "devis"),
            ("Situation", "situation"),
        ]
        
        self.doc_vars = {}
        self.doc_combos = {}  # Garder une référence aux combobox
        for i, (label, key) in enumerate(self.doc_types):
            row = tk.Frame(config_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=5)
            lbl(row, f"{label}:", 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            
            self.doc_vars[key] = tk.StringVar()
            cb = combo(row, [], width=30, textvariable=self.doc_vars[key])
            cb.pack(side="left", padx=10)
            self.doc_combos[key] = cb  # Stocker la référence
        
        tk.Button(config_frame, text="💾 Enregistrer la configuration", command=self.save_config,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(pady=10)
        
        # Tableau des profils
        cols = ["Code", "Nom", "Type", "Téléphone", "Email", "Défaut"]
        widths = [100, 200, 100, 120, 180, 80]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_profil,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="⭐ Définir par défaut", command=self.set_default,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_profil,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        profils = conn.execute("SELECT * FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        for p in profils:
            default_mark = "✅" if p["est_defaut"] else ""
            self.tree.insert("", "end", iid=p["id"], values=(
                p["code"], p["nom"], p["type_profil"],
                p["telephone"] or "-", p["email"] or "-", default_mark
            ))
        
        # Charger la configuration
        self.load_config()
    
    def load_config(self):
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        conn = get_conn()
        profils = conn.execute("SELECT id, code, nom FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        profil_liste = ["-- Aucun --"] + [f"{p['code']} - {p['nom']}" for p in profils]
        
        # Mettre à jour les valeurs des combobox
        for doc_key, var in self.doc_vars.items():
            var.set(config.get(doc_key, "-- Aucun --"))
            # Mettre à jour les valeurs du combobox via la référence stockée
            if doc_key in self.doc_combos:
                self.doc_combos[doc_key]['values'] = profil_liste
    
    def save_config(self):
        config = {}
        for doc_key, var in self.doc_vars.items():
            val = var.get()
            if val and val != "-- Aucun --":
                config[doc_key] = val
        
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Succès", "Configuration enregistrée")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def nouveau_profil(self):
        d = ProfilDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def edit_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT * FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        d = ProfilDialog(self, dict(profil) if profil else None)
        self.wait_window(d)
        self.refresh()
    
    def set_default(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        try:
            conn.execute("UPDATE profils_entreprise SET est_defaut = 0")
            conn.execute("UPDATE profils_entreprise SET est_defaut = 1 WHERE id=?", (sel[0],))
            conn.commit()
            messagebox.showinfo("Succès", "Profil défini par défaut")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
    
    def delete_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT nom, est_defaut FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        
        if profil["est_defaut"]:
            messagebox.showwarning("", "Impossible de supprimer le profil par défaut")
            conn.close()
            return
        
        if messagebox.askyesno("Confirmation", f"Supprimer le profil '{profil['nom']}' ?"):
            try:
                conn.execute("DELETE FROM profils_entreprise WHERE id=?", (sel[0],))
                conn.commit()
                messagebox.showinfo("Succès", "Profil supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        conn.close()

