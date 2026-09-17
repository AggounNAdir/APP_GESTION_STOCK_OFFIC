from datetime import date
import sqlite3
import tkinter as tk
from tkinter import messagebox
from modules.core import *


class VersementDialog(tk.Toplevel):
  """Dialogue de création de versement (Client, Prospect ou Fournisseur)"""

  def __init__(self, parent, vers_type):
    super().__init__(parent)
    self.vers_type = vers_type

    if vers_type == "client":
      self.table = "versements_clients"
      self.tiers_table = "clients"
      self.tiers_id_col = "client_id"
      self.prefix = "VC"
      self.tiers_label = "Client"
    elif vers_type == "prospect":
      self.table = "versements_prospects"
      self.tiers_table = "prospects_clients"
      self.tiers_id_col = "prospect_id"
      self.prefix = "VP"
      self.tiers_label = "Prospect"
    else:
      self.table = "versements_fournisseurs"
      self.tiers_table = "fournisseurs"
      self.tiers_id_col = "fournisseur_id"
      self.prefix = "VF"
      self.tiers_label = "Fournisseur"

    self.title(f"Nouveau Versement - {self.tiers_label}")
    self.configure(bg=CLR_BG)
    self.geometry("500x470")
    self._build()
    center_window(self, 500, 470)

  def _build(self):
    main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    lbl(
        main_frame,
        f"💰 NOUVEAU VERSEMENT {self.tiers_label.upper()}",
        14,
        True,
        CLR_ACCENT,
    ).pack(pady=(0, 15))

    form_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=20, pady=15)
    form_frame.pack(fill="x", pady=10)

    # Numéro
    row1 = tk.Frame(form_frame, bg=CLR_CARD)
    row1.pack(fill="x", pady=5)
    lbl(row1, "Numéro:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.num_var = tk.StringVar(value=next_numero(self.prefix, self.table))
    entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(
        side="left", padx=10
    )

    # Date
    lbl(row1, "Date:", 9, False, CLR_MUTED).pack(side="left", padx=(20, 5))
    self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
    entry(row1, width=15, textvariable=self.date_var).pack(
        side="left", padx=10
    )

    # Sélection Tiers (Clients ou Prospects)
    row2 = tk.Frame(form_frame, bg=CLR_CARD)
    row2.pack(fill="x", pady=5)
    lbl(row2, f"{self.tiers_label}:", 9, False, CLR_MUTED).pack(
        side="left", padx=5
    )

    conn = get_conn()
    try:
      tiers = conn.execute(
          f"SELECT id, nom, COALESCE(solde, 0.0) as solde FROM {self.tiers_table} ORDER BY nom"
      ).fetchall()
    finally:
      conn.close()

    self.tiers_map = {
        t["nom"]: {"id": t["id"], "solde": t["solde"]} for t in tiers
    }
    self.tiers_var = tk.StringVar()
    tiers_combo = combo(
        row2,
        list(self.tiers_map.keys()),
        width=30,
        textvariable=self.tiers_var,
    )
    tiers_combo.pack(side="left", padx=10)
    self.tiers_var.trace_add("write", self.on_tiers_selected)

    # Solde actuel
    row3 = tk.Frame(form_frame, bg=CLR_CARD)
    row3.pack(fill="x", pady=5)
    lbl(row3, "Solde actuel:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.solde_var = tk.StringVar(value="0.00 DA")
    tk.Label(
        row3,
        textvariable=self.solde_var,
        bg=CLR_CARD,
        fg=CLR_ORANGE,
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left", padx=10)

    # Montant
    row4 = tk.Frame(form_frame, bg=CLR_CARD)
    row4.pack(fill="x", pady=5)
    lbl(row4, "Montant:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.montant_var = tk.StringVar()
    entry(
        row4,
        width=15,
        textvariable=self.montant_var,
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left", padx=10)
    lbl(row4, "DA", 9, False, CLR_MUTED).pack(side="left")

    # Mode
    row5 = tk.Frame(form_frame, bg=CLR_CARD)
    row5.pack(fill="x", pady=5)
    lbl(row5, "Mode:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.mode_var = tk.StringVar(value="Espèces")
    mode_combo = combo(
        row5,
        ["Espèces", "Chèque", "Virement", "Carte"],
        width=15,
        textvariable=self.mode_var,
    )
    mode_combo.pack(side="left", padx=10)

    # Référence
    row6 = tk.Frame(form_frame, bg=CLR_CARD)
    row6.pack(fill="x", pady=5)
    lbl(row6, "Référence:", 9, False, CLR_MUTED).pack(side="left", padx=5)
    self.ref_var = tk.StringVar()
    entry(row6, width=30, textvariable=self.ref_var).pack(side="left", padx=10)

    # Nouveau solde
    row7 = tk.Frame(form_frame, bg=CLR_CARD)
    row7.pack(fill="x", pady=(10, 5))
    lbl(row7, "Nouveau solde:", 10, True, CLR_MUTED).pack(side="left", padx=5)
    self.nouveau_solde_var = tk.StringVar(value="0.00 DA")
    tk.Label(
        row7,
        textvariable=self.nouveau_solde_var,
        bg=CLR_CARD,
        fg=CLR_GREEN,
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left", padx=10)

    self.montant_var.trace_add("write", self.calculer_nouveau_solde)

    # Boutons
    btn_frame = tk.Frame(main_frame, bg=CLR_BG)
    btn_frame.pack(fill="x", pady=15)

    tk.Button(
        btn_frame,
        text="✅ ENREGISTRER",
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

  def on_tiers_selected(self, *args):
    tiers_nom = self.tiers_var.get()
    if tiers_nom in self.tiers_map:
      solde = self.tiers_map[tiers_nom]["solde"]
      self.solde_var.set(f"{solde:,.2f} DA")
      self.calculer_nouveau_solde()

  def calculer_nouveau_solde(self, *args):
    tiers_nom = self.tiers_var.get()
    if tiers_nom not in self.tiers_map:
      return
    try:
      montant = parse_decimal(self.montant_var.get() or "0")
      solde_actuel = self.tiers_map[tiers_nom]["solde"]
      nouveau_solde = solde_actuel - montant
      self.nouveau_solde_var.set(f"{nouveau_solde:,.2f} DA")
    except Exception:
      pass

  def save(self):
    tiers_nom = self.tiers_var.get()
    if tiers_nom not in self.tiers_map:
      messagebox.showerror(
          "Erreur", f"Sélectionnez un {self.tiers_label.lower()}."
      )
      return

    try:
      montant = parse_decimal(self.montant_var.get() or "0")
      if montant <= 0:
        messagebox.showerror("Erreur", "Montant invalide.")
        return
    except ValueError:
      messagebox.showerror("Erreur", "Montant invalide.")
      return

    if not valider_date(self.date_var.get()):
      messagebox.showerror("Erreur", "Format de date invalide (YYYY-MM-DD).")
      return

    tiers_id = self.tiers_map[tiers_nom]["id"]
    conn = get_conn()
    try:
      conn.execute(
          f"""
                INSERT INTO {self.table}(numero, date_vers, {self.tiers_id_col}, montant, mode, reference)
                VALUES(?, ?, ?, ?, ?, ?)
            """,
          (
              self.num_var.get(),
              self.date_var.get(),
              tiers_id,
              montant,
              self.mode_var.get(),
              self.ref_var.get() or None,
          ),
      )
      # Mise à jour du solde
      conn.execute(
          f"UPDATE {self.tiers_table} SET solde = solde - ? WHERE id=?",
          (montant, tiers_id),
      )
      conn.commit()
      messagebox.showinfo(
          "Succès", f"Versement {self.num_var.get()} enregistré avec succès !"
      )
      self.destroy()
    except sqlite3.IntegrityError:
      nouveau_num = next_numero(self.prefix, self.table)
      self.num_var.set(nouveau_num)
      messagebox.showwarning("Numéro dupliqué", f"Nouveau numéro : {nouveau_num}")
    except Exception as e:
      messagebox.showerror("Erreur", str(e))
      conn.rollback()
    finally:
      conn.close()