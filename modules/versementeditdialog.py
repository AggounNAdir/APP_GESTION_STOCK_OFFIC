from modules.core import *


class VersementEditDialog(tk.Toplevel):

  def __init__(self, parent, vers_type, vers_id):
    super().__init__(parent)
    self.vers_type = vers_type
    self.vers_id = vers_id

    if vers_type == "client":
      self.table = "versements_clients"
      self.tiers_table = "clients"
      self.tiers_id_col = "client_id"
      self.tiers_label = "Client"
    elif vers_type == "prospect":
      self.table = "versements_prospects"
      self.tiers_table = "prospects_clients"
      self.tiers_id_col = "prospect_id"
      self.tiers_label = "Prospect"
    else:
      self.table = "versements_fournisseurs"
      self.tiers_table = "fournisseurs"
      self.tiers_id_col = "fournisseur_id"
      self.tiers_label = "Fournisseur"

    self.title(f"Modifier Versement - {self.tiers_label}")
    self.configure(bg=CLR_BG)
    self.geometry("500x450")
    self._load_data()
    self._build()
    center_window(self, 500, 450)

  def _load_data(self):
    conn = get_conn()
    self.versement = conn.execute(
        f"SELECT * FROM {self.table} WHERE id=?", (self.vers_id,)
    ).fetchone()
    conn.close()

  def _build(self):
    main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    lbl(main_frame, "✏ MODIFIER VERSEMENT", 14, True, CLR_ACCENT).pack(
        pady=(0, 15)
    )

    form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
    form_frame.pack(fill="x", pady=10)

    # Numéro (lecture seule)
    row1 = tk.Frame(form_frame, bg=CLR_CARD)
    row1.pack(fill="x", pady=5)
    lbl(row1, "Numéro:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.num_var = tk.StringVar(value=self.versement["numero"])
    entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(
        side="left", padx=10
    )

    # Date
    lbl(row1, "Date:", 9, False, CLR_MUTED).pack(side="left", padx=(20, 5))
    self.date_var = tk.StringVar(value=self.versement["date_vers"])
    entry(row1, width=15, textvariable=self.date_var).pack(
        side="left", padx=10
    )

    # Montant
    row2 = tk.Frame(form_frame, bg=CLR_CARD)
    row2.pack(fill="x", pady=5)
    lbl(row2, "Montant:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.montant_var = tk.StringVar(value=f"{self.versement['montant']:.2f}")
    entry(
        row2,
        width=15,
        textvariable=self.montant_var,
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left", padx=10)
    lbl(row2, "DA", 9, False, CLR_MUTED).pack(side="left")

    # Mode
    row3 = tk.Frame(form_frame, bg=CLR_CARD)
    row3.pack(fill="x", pady=5)
    lbl(row3, "Mode:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.mode_var = tk.StringVar(value=self.versement["mode"])
    mode_combo = combo(
        row3,
        ["Espèces", "Chèque", "Virement", "Carte"],
        width=15,
        textvariable=self.mode_var,
    )
    mode_combo.pack(side="left", padx=10)

    # Référence
    row4 = tk.Frame(form_frame, bg=CLR_CARD)
    row4.pack(fill="x", pady=5)
    lbl(row4, "Référence:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.ref_var = tk.StringVar(value=self.versement["reference"] or "")
    entry(row4, width=30, textvariable=self.ref_var).pack(side="left", padx=10)

    # Boutons
    btn_frame = tk.Frame(main_frame, bg=CLR_BG)
    btn_frame.pack(fill="x", pady=15)

    tk.Button(
        btn_frame,
        text="💾 ENREGISTRER",
        command=self.save,
        bg=CLR_GREEN,
        fg="white",
        relief="flat",
        font=("Segoe UI", 11, "bold"),
        padx=25,
        pady=10,
        cursor="hand2",
    ).pack(side="left", padx=10, expand=True, fill="x")

    tk.Button(
        btn_frame,
        text="❌ ANNULER",
        command=self.destroy,
        bg=CLR_RED,
        fg="white",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padx=20,
        pady=10,
        cursor="hand2",
    ).pack(side="right", padx=10)

  def save(self):
    try:
      montant = parse_decimal(self.montant_var.get() or "0")
      if montant <= 0:
        messagebox.showerror("Erreur", "Montant invalide.")
        return
    except ValueError:
      messagebox.showerror("Erreur", "Montant invalide.")
      return

    if not valider_date(self.date_var.get()):
      messagebox.showerror("Erreur", "Format de date invalide.")
      return

    conn = get_conn()
    try:
      old_vers = conn.execute(
          f"SELECT montant FROM {self.table} WHERE id=?", (self.vers_id,)
      ).fetchone()
      delta = montant - old_vers["montant"]

      conn.execute(
          f"""
                UPDATE {self.table} 
                SET date_vers=?, montant=?, mode=?, reference=?
                WHERE id=?
            """,
          (
              self.date_var.get(),
              montant,
              self.mode_var.get(),
              self.ref_var.get() or None,
              self.vers_id,
          ),
      )

      # Ajustement propre du solde du tiers concerné
      conn.execute(
          f"UPDATE {self.tiers_table} SET solde = solde - ? WHERE id=?",
          (delta, self.versement[self.tiers_id_col]),
      )

      conn.commit()
      messagebox.showinfo("Succès", "Versement modifié !")
      self.destroy()
    except Exception as e:
      messagebox.showerror("Erreur", str(e))
      conn.rollback()
    finally:
      conn.close()