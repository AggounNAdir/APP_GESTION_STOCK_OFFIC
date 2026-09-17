from modules.core import *


class VersementDetailDialog(tk.Toplevel):

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

    self.title(f"Détail Versement - {self.tiers_label}")
    self.configure(bg=CLR_BG)
    self.geometry("600x400")
    self._load_data()
    self._build()
    center_window(self, 600, 400)

  def _load_data(self):
    conn = get_conn()
    try:
      self.versement = conn.execute(
          f"""
                SELECT v.*, t.nom as tiers_nom, COALESCE(t.solde, 0.0) as solde
                FROM {self.table} v
                JOIN {self.tiers_table} t ON v.{self.tiers_id_col} = t.id
                WHERE v.id = ?
            """,
          (self.vers_id,),
      ).fetchone()
    finally:
      conn.close()

  def _build(self):
    main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    if not self.versement:
      lbl(main_frame, "Versement introuvable", 12, True, CLR_RED).pack()
      return

    lbl(
        main_frame,
        f"📄 REÇU VERSEMENT N° {self.versement['numero']}",
        14,
        True,
        CLR_ACCENT,
    ).pack(pady=(0, 15))

    card = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
    card.pack(fill="both", expand=True)

    def add_row(parent, label, value, val_color=CLR_TEXT, is_bold=False):
      r = tk.Frame(parent, bg=CLR_CARD)
      r.pack(fill="x", pady=4)
      lbl(r, f"{label}:", 10, False, CLR_MUTED).pack(side="left")
      lbl(r, str(value), 10, is_bold, val_color).pack(side="right")

    add_row(card, "Numéro de reçu", self.versement["numero"], CLR_ACCENT, True)
    add_row(card, "Date du versement", self.versement["date_vers"])
    add_row(
        card,
        self.tiers_label,
        self.versement["tiers_nom"],
        is_bold=True,
    )
    add_row(
        card,
        "Montant versé",
        f"{float(self.versement['montant']):,.2f} DA",
        CLR_GREEN,
        True,
    )
    add_row(card, "Mode de règlement", self.versement["mode"])
    add_row(card, "Référence / N° Chèque", self.versement["reference"] or "-")
    add_row(
        card,
        f"Solde actuel du {self.tiers_label.lower()}",
        f"{float(self.versement['solde']):,.2f} DA",
        CLR_ORANGE,
        True,
    )

    tk.Button(
        main_frame,
        text="Fermer",
        command=self.destroy,
        bg=CLR_CARD,
        fg=CLR_TEXT,
        relief="flat",
        font=("Segoe UI", 10),
        padx=20,
        pady=6,
        cursor="hand2",
    ).pack(pady=(15, 0))