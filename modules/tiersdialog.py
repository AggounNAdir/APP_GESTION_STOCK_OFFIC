from modules.core import *

class TiersDialog(tk.Toplevel):
    def __init__(self, parent, tiers_type, data=None):
        super().__init__(parent)
        self.tiers_type = tiers_type
        self.parent = parent
        self.title("Client" if tiers_type == "client" else "Fournisseur")
        self.configure(bg=CLR_BG)
        self.resizable(True, True)  # ✅ Permettre le redimensionnement
        self.table = "clients" if tiers_type == "client" else "fournisseurs"
        self.data = data
        self._build()
        self.update_idletasks()
        # ✅ Agrandir la fenêtre
        self.geometry("700x650")
        center_window(self, 700, 650)

    def _build(self):
        # ✅ Frame principal avec padding
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # ✅ Titre
        titre = "CLIENT" if self.tiers_type == "client" else "FOURNISSEUR"
        lbl(main_frame, f"📋 INFORMATIONS {titre}", 14, True, CLR_ACCENT).pack(pady=(0, 10))
        
        # ✅ Canvas + Scrollbar pour le formulaire
        canvas_frame = tk.Frame(main_frame, bg=CLR_BG)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=650)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ✅ Formulaire dans le frame scrollable
        f = tk.Frame(scrollable_frame, bg=CLR_BG, padx=10, pady=10)
        f.pack(fill="both", expand=True)
        
        # Génération du code
        if not self.data:
            prefix = "CLT" if self.tiers_type == "client" else "FRN"
            code_auto = generer_code_unique(prefix, self.table, mode="sequentiel")
        else:
            code_auto = self.data["code"]
        
        # ✅ Dictionnaire pour stocker les variables
        self.vars = {}
        row_idx = 0
        
        # ✅ SECTION 1: INFORMATIONS DE BASE
        lbl(f, "🏷️ INFORMATIONS DE BASE", 11, True, CLR_ACCENT).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(10, 5)
        )
        row_idx += 1
        
        # Séparateur
        sep = tk.Frame(f, bg=CLR_BORDER, height=2)
        sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=5)
        row_idx += 1
        
        fields_base = [
            ("Code *", "code", True),
            ("Nom *", "nom", False),
            ("Adresse", "adresse", False),
            ("Ville", "ville", False),
            ("Téléphone", "tel", False),
            ("Email", "email", False),
        ]
        
        for lbl_text, key, readonly in fields_base:
            lbl(f, lbl_text, color=CLR_MUTED, size=9).grid(
                row=row_idx, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            v = tk.StringVar()
            if key == "code" and not self.data:
                v.set(code_auto)
            elif self.data and self.data.get(key):
                v.set(str(self.data[key]))
            
            # ✅ Plus large pour les champs de base
            e = entry(f, width=40, textvariable=v)
            e.grid(row=row_idx, column=1, padx=(0, 10), pady=5, sticky="w")
            
            if key == "code" and not self.data:
                e.config(state="readonly", readonlybackground=CLR_INPUT)
                # Bouton régénérer
                btn_regenerate = tk.Button(
                    f, text="🔄", command=self.regenerate_code,
                    bg=CLR_ACCENT, fg="white", relief="flat",
                    font=("Segoe UI", 8, "bold"), padx=8, pady=2, cursor="hand2"
                )
                btn_regenerate.grid(row=row_idx, column=2, padx=5, pady=5)
            
            self.vars[key] = v
            row_idx += 1
        
        # ✅ SECTION 2: INFORMATIONS COMMERCIALES
        lbl(f, "🏢 INFORMATIONS COMMERCIALES", 11, True, CLR_ACCENT).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(15, 5)
        )
        row_idx += 1
        
        # Séparateur
        sep = tk.Frame(f, bg=CLR_BORDER, height=2)
        sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=5)
        row_idx += 1
        
        fields_commercial = [
            ("NIF (N° Identification Fiscale)", "nif", False),
            ("NIS (N° Identification Statistique)", "nis", False),
            ("NRC (N° Registre de Commerce)", "nrc", False),
            ("Article d'imposition", "art_imp", False),
            ("Registre de commerce", "registre_commerce", False),
            ("Capital social", "capitale_social", False),
        ]
        
        for lbl_text, key, readonly in fields_commercial:
            lbl(f, lbl_text, color=CLR_MUTED, size=9).grid(
                row=row_idx, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            v = tk.StringVar()
            if self.data and self.data.get(key):
                v.set(str(self.data[key]))
            e = entry(f, width=40, textvariable=v)
            e.grid(row=row_idx, column=1, padx=(0, 10), pady=5, sticky="w")
            self.vars[key] = v
            row_idx += 1
        
        # ✅ BOUTONS EN BAS
        btn_frame = tk.Frame(f, bg=CLR_BG)
        btn_frame.grid(row=row_idx, column=0, columnspan=3, pady=25)
        
        tk.Button(
            btn_frame, text="💾 Enregistrer", command=self.save,
            bg=CLR_GREEN, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=25, pady=8, cursor="hand2"
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame, text="❌ Annuler", command=self.destroy,
            bg=CLR_RED, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=25, pady=8, cursor="hand2"
        ).pack(side="left", padx=10)
    
    def regenerate_code(self):
        prefix = "CLT" if self.tiers_type == "client" else "FRN"
        nouveau_code = generer_code_unique(prefix, self.table, mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")

    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        if not v["code"] or not v["nom"]:
            messagebox.showerror("Erreur", "Code et nom obligatoires")
            return
        
        conn = get_conn()
        try:
            if self.data:
                conn.execute(f"""
                    UPDATE {self.table} 
                    SET code=?, nom=?, adresse=?, ville=?, tel=?, email=?,
                        nif=?, nis=?, nrc=?, art_imp=?, registre_commerce=?, capitale_social=?
                    WHERE id=?
                """, (
                    v["code"], v["nom"], v["adresse"], v["ville"], v["tel"], v["email"],
                    v["nif"], v["nis"], v["nrc"], v["art_imp"], v["registre_commerce"], v["capitale_social"],
                    self.data["id"]
                ))
            else:
                conn.execute(f"""
                    INSERT INTO {self.table}(code, nom, adresse, ville, tel, email,
                        nif, nis, nrc, art_imp, registre_commerce, capitale_social)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    v["code"], v["nom"], v["adresse"], v["ville"], v["tel"], v["email"],
                    v["nif"], v["nis"], v["nrc"], v["art_imp"], v["registre_commerce"], v["capitale_social"]
                ))
            
            conn.commit()
            conn.close()
            if hasattr(self.parent, 'refresh'):
                self.parent.refresh()
            messagebox.showinfo("Succès", f"{'Client' if self.tiers_type == 'client' else 'Fournisseur'} enregistré avec succès !")
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Code déjà existant")
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))


# ========== PAGE BONS D'ACHAT ==========

