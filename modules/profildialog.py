from modules.core import *

class ProfilDialog(tk.Toplevel):
    """Dialogue de création/édition de profil entreprise"""
    
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.data = data
        self.title("Profil Entreprise")
        self.configure(bg=CLR_BG)
        self.geometry("700x650")
        self._build()
        center_window(self, 700, 650)
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, "🏢 INFORMATIONS DE L'ENTREPRISE", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Formulaire avec scroll
        canvas = tk.Canvas(main_frame, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Champs du formulaire
        form_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=20, pady=15)
        form_frame.pack(fill="both", expand=True, pady=5)
        
        fields = [
            ("Code *", "code", True),
            ("Nom de l'entreprise *", "nom", False),
            ("Type de profil", "type_profil", False, ["simple", "complet"]),
            ("Adresse", "adresse", False),
            ("Ville", "ville", False),
            ("Téléphone", "telephone", False),
            ("Email", "email", False),
            ("Site web", "site_web", False),
            ("NIF (Numéro d'Identification Fiscale)", "nif", False),
            ("NIS (Numéro d'Identification Statistique)", "nis", False),
            ("NRC (Numéro Registre de Commerce)", "nrc", False),
            ("Article d'imposition", "art_imp", False),
            ("Registre de commerce", "registre_commerce", False),
            ("Capital social", "capitale_social", False),
        ]
        
        self.vars = {}
        
        for i, field in enumerate(fields):
            if len(field) == 4:
                lbl_text, key, readonly, choices = field
            else:
                lbl_text, key, readonly = field
                choices = None
            
            row = tk.Frame(form_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=4)
            
            lbl(row, lbl_text, 9, False, CLR_MUTED).pack(side="left", padx=5, ipadx=10, anchor="w")
            
            v = tk.StringVar()
            if self.data and key in self.data and self.data[key]:
                v.set(str(self.data[key]))
            elif key == "type_profil":
                v.set("simple")
            elif key == "code" and not self.data:
                v.set(generer_code_unique("PROF", "profils_entreprise", mode="sequentiel"))
            
            if choices:
                widget = combo(row, choices, width=30, textvariable=v)
            else:
                widget = entry(row, width=40, textvariable=v)
                if key == "code" and not self.data:
                    widget.config(state="readonly", readonlybackground=CLR_INPUT)
            
            widget.pack(side="left", padx=10, fill="x", expand=True)
            self.vars[key] = v
            
            if not self.data and key == "code":
                tk.Button(row, text="🔄", command=self.regenerate_code,
                         bg=CLR_ACCENT, fg="white", relief="flat",
                         font=("Segoe UI", 8, "bold"), padx=5, pady=2,
                         cursor="hand2").pack(side="left", padx=5)
        
        # Logo
        row_logo = tk.Frame(form_frame, bg=CLR_CARD)
        row_logo.pack(fill="x", pady=10)
        lbl(row_logo, "Logo:", 9, False, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
        self.logo_path_var = tk.StringVar(value=self.data["logo_path"] if self.data and self.data.get("logo_path") else "")
        entry(row_logo, width=30, textvariable=self.logo_path_var).pack(side="left", padx=10)
        tk.Button(row_logo, text="Parcourir", command=self.browse_logo,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 8, "bold"),
                 padx=8, pady=3, cursor="hand2").pack(side="left", padx=5)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=15)
        
        tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
        
        tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def regenerate_code(self):
        nouveau_code = generer_code_unique("PROF", "profils_entreprise", mode="sequentiel")
        self.vars["code"].set(nouveau_code)
        messagebox.showinfo("Code régénéré", f"Nouveau code: {nouveau_code}")
    
    def browse_logo(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner un logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Tous", "*.*")]
        )
        if filename:
            self.logo_path_var.set(filename)
    
    def save(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        
        if not v["code"] or not v["nom"]:
            messagebox.showerror("Erreur", "Code et nom sont obligatoires")
            return
        
        conn = get_conn()
        try:
            if self.data:
                conn.execute("""
                    UPDATE profils_entreprise 
                    SET code=?, nom=?, type_profil=?, adresse=?, ville=?, 
                        telephone=?, email=?, site_web=?, nif=?, nis=?, nrc=?,
                        art_imp=?, registre_commerce=?, capitale_social=?, logo_path=?
                    WHERE id=?
                """, (v["code"], v["nom"], v["type_profil"], v["adresse"], v["ville"],
                      v["telephone"], v["email"], v["site_web"], v["nif"], v["nis"], v["nrc"],
                      v["art_imp"], v["registre_commerce"], v["capitale_social"],
                      self.logo_path_var.get(), self.data["id"]))
            else:
                conn.execute("""
                    INSERT INTO profils_entreprise(code, nom, type_profil, adresse, ville,
                        telephone, email, site_web, nif, nis, nrc, art_imp,
                        registre_commerce, capitale_social, logo_path)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (v["code"], v["nom"], v["type_profil"], v["adresse"], v["ville"],
                      v["telephone"], v["email"], v["site_web"], v["nif"], v["nis"], v["nrc"],
                      v["art_imp"], v["registre_commerce"], v["capitale_social"],
                      self.logo_path_var.get()))
            conn.commit()
            messagebox.showinfo("Succès", "Profil enregistré")
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Code déjà existant")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
