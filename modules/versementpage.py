import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from modules.core import *
from modules.versementdetaildialog import VersementDetailDialog
from modules.versementdialog import VersementDialog
from modules.versementeditdialog import VersementEditDialog


class VersementPage(tk.Frame):
  """Page de gestion des versements avec sélection Client ou Prospect"""

  def __init__(self, parent, vers_type="general"):
    super().__init__(parent, bg=CLR_BG)
    self.base_mode = (
        vers_type  # "general" (clients/prospects) ou "fournisseur"
    )
    self.target_type = "client" if vers_type != "fournisseur" else "fournisseur"
    self._update_table_config()
    self._ensure_tables()
    self._build()
    self.refresh()

  def _update_table_config(self):
    if self.target_type == "client":
      self.table = "versements_clients"
      self.tiers_table = "clients"
      self.tiers_id_col = "client_id"
      self.tiers_label = "Client"
      self.prefix = "VC"
    elif self.target_type == "prospect":
      self.table = "versements_prospects"
      self.tiers_table = "prospects_clients"
      self.tiers_id_col = "prospect_id"
      self.tiers_label = "Prospect"
      self.prefix = "VP"
    else:
      self.table = "versements_fournisseurs"
      self.tiers_table = "fournisseurs"
      self.tiers_id_col = "fournisseur_id"
      self.tiers_label = "Fournisseur"
      self.prefix = "VF"

  def _ensure_tables(self):
    conn = get_conn()
    try:
      # Tables/colonnes (prospects_clients.solde, versements_prospects) : voir api/schema.py
      pass
    finally:
      conn.close()

  def _build(self):
    # En-tête
    hdr = tk.Frame(self, bg=CLR_BG)
    hdr.pack(fill="x", padx=20, pady=(15, 5))

    self.title_lbl = lbl(hdr, "💳  Gestion des Versements", 16, True)
    self.title_lbl.pack(side="left")

    btn_frame = tk.Frame(hdr, bg=CLR_BG)
    btn_frame.pack(side="right")

    tk.Button(
        btn_frame,
        text="+ Nouveau Versement",
        command=self.nouveau_versement,
        bg=CLR_GREEN,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=14,
        pady=7,
        cursor="hand2",
    ).pack(side="left", padx=4)

    tk.Button(
        btn_frame,
        text="🔄 Actualiser",
        command=self.refresh,
        bg=CLR_ACCENT,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=14,
        pady=7,
        cursor="hand2",
    ).pack(side="left", padx=4)

    # 🔘 SÉLECTEUR CLIENT / PROSPECT (affiché seulement si ce n'est pas Fournisseur)
    if self.base_mode != "fournisseur":
      sel_frame = tk.Frame(self, bg=CLR_BG)
      sel_frame.pack(fill="x", padx=20, pady=(5, 10))

      lbl(sel_frame, "Type de versement :", 10, True, CLR_MUTED).pack(
          side="left", padx=(0, 10)
      )

      self.btn_client = tk.Button(
          sel_frame,
          text="👤 Versements Clients",
          command=lambda: self.switch_target("client"),
          relief="flat",
          font=("Segoe UI", 9, "bold"),
          padx=15,
          pady=5,
          cursor="hand2",
      )
      self.btn_client.pack(side="left", padx=3)

      self.btn_prospect = tk.Button(
          sel_frame,
          text="🎯 Versements Prospects",
          command=lambda: self.switch_target("prospect"),
          relief="flat",
          font=("Segoe UI", 9, "bold"),
          padx=15,
          pady=5,
          cursor="hand2",
      )
      self.btn_prospect.pack(side="left", padx=3)
      self._update_tab_buttons()

    # Barre de Filtres
    sf = tk.Frame(self, bg=CLR_BG)
    sf.pack(fill="x", padx=20, pady=5)

    lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
    self.search_var = tk.StringVar()
    self.search_var.trace_add("write", lambda *a: self.refresh())
    entry(sf, width=25, textvariable=self.search_var).pack(side="left", padx=8)

    self.lbl_tiers = lbl(sf, f"{self.tiers_label}:", color=CLR_MUTED)
    self.lbl_tiers.pack(side="left", padx=(15, 5))

    self.tiers_filter_var = tk.StringVar(value="Tous")
    self.tiers_combo = combo(
        sf, ["Tous"], width=22, textvariable=self.tiers_filter_var
    )
    self.tiers_combo.pack(side="left", padx=5)
    self.tiers_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

    lbl(sf, "Mode:", color=CLR_MUTED).pack(side="left", padx=(15, 5))
    self.mode_filter_var = tk.StringVar(value="Tous")
    mode_combo = combo(
        sf,
        ["Tous", "Espèces", "Chèque", "Virement", "Carte"],
        width=12,
        textvariable=self.mode_filter_var,
    )
    mode_combo.pack(side="left", padx=5)
    mode_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

    # Tableau
    cols = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
    widths = [120, 100, 220, 120, 100, 150]
    tf, self.tree = make_tree(self, cols, widths)
    tf.pack(fill="both", expand=True, padx=20, pady=10)

    # Actions en bas
    action_frame = tk.Frame(self, bg=CLR_BG)
    action_frame.pack(fill="x", padx=20, pady=(0, 15))

    tk.Button(
        action_frame,
        text="👁 Détail",
        command=self.view_versement,
        bg=CLR_ACCENT,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

    tk.Button(
        action_frame,
        text="✏ Modifier",
        command=self.edit_versement,
        bg=CLR_ORANGE,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

    tk.Button(
        action_frame,
        text="🗑 Supprimer",
        command=self.delete_versement,
        bg=CLR_RED,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

    tk.Button(
        action_frame,
        text="🖨 Imprimer",
        command=self.print_versements,
        bg=CLR_ACCENT,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

  def _update_tab_buttons(self):
    """Mise en surbrillance de l'onglet actif"""
    if self.base_mode == "fournisseur":
      return
    if self.target_type == "client":
      self.btn_client.config(bg="#2563EB", fg="white")  # Bleu
      self.btn_prospect.config(bg="#E2E8F0", fg="#475569")  # Gris clair
      self.title_lbl.config(text="💳  Versements Clients")
    else:
      self.btn_client.config(bg="#E2E8F0", fg="#475569")
      self.btn_prospect.config(bg="#7C3AED", fg="white")  # Violet
      self.title_lbl.config(text="💳  Versements Prospects (Terrain)")

  def switch_target(self, new_type):
    if self.target_type == new_type:
      return
    self.target_type = new_type
    self._update_table_config()
    self._update_tab_buttons()
    self.lbl_tiers.config(text=f"{self.tiers_label}:")

    # Mettre à jour l'en-tête de la colonne 3
    self.tree.heading(
        self.tree["columns"][2],
        text=self.tiers_label,
        anchor="center",
    )

    self.tiers_filter_var.set("Tous")
    self.load_tiers_list()
    self.refresh()

  def load_tiers_list(self):
    conn = get_conn()
    try:
      tiers = conn.execute(
          f"SELECT nom FROM {self.tiers_table} ORDER BY nom"
      ).fetchall()
      self.tiers_list = [t["nom"] for t in tiers]
      self.tiers_combo["values"] = ["Tous"] + self.tiers_list
    finally:
      conn.close()

  def refresh(self):
    self.load_tiers_list()
    q = self.search_var.get().lower()
    tiers_filter = self.tiers_filter_var.get()
    mode_filter = self.mode_filter_var.get()

    self.tree.delete(*self.tree.get_children())

    conn = get_conn()
    try:
      query = f"""
                SELECT v.*, t.nom as tiers_nom
                FROM {self.table} v
                JOIN {self.tiers_table} t ON v.{self.tiers_id_col} = t.id
                ORDER BY v.date_vers DESC, v.id DESC
            """
      rows = conn.execute(query).fetchall()
    except Exception as e:
      print(f"Erreur chargement versements ({self.table}): {e}")
      rows = []
    finally:
      conn.close()

    for r in rows:
      if (
          q
          and q not in str(r["numero"]).lower()
          and q not in str(r["tiers_nom"]).lower()
      ):
        continue
      if tiers_filter != "Tous" and r["tiers_nom"] != tiers_filter:
        continue
      if mode_filter != "Tous" and r["mode"] != mode_filter:
        continue

      self.tree.insert(
          "",
          "end",
          iid=r["id"],
          values=(
              r["numero"],
              r["date_vers"],
              r["tiers_nom"],
              f"{float(r['montant']):,.2f} DA",
              r["mode"],
              r["reference"] or "",
          ),
      )

  def nouveau_versement(self):
    d = VersementDialog(self, self.target_type)
    self.wait_window(d)
    self.refresh()

  def view_versement(self):
    sel = self.tree.selection()
    if not sel:
      messagebox.showwarning("", "Sélectionnez un versement.")
      return
    d = VersementDetailDialog(self, self.target_type, sel[0])
    self.wait_window(d)

  def edit_versement(self):
    sel = self.tree.selection()
    if not sel:
      messagebox.showwarning("", "Sélectionnez un versement.")
      return
    d = VersementEditDialog(self, self.target_type, sel[0])
    self.wait_window(d)
    self.refresh()

  def delete_versement(self):
    sel = self.tree.selection()
    if not sel:
      messagebox.showwarning("", "Sélectionnez un versement.")
      return

    if messagebox.askyesno(
        "Confirmation",
        f"⚠️ Supprimer ce versement ?\nLe solde du {self.tiers_label.lower()} sera recalculé.",
    ):
      conn = get_conn()
      try:
        vers_id = sel[0]
        vers = conn.execute(
            f"SELECT {self.tiers_id_col}, montant FROM {self.table} WHERE id=?",
            (vers_id,),
        ).fetchone()
        if vers:
          conn.execute(
              f"UPDATE {self.tiers_table} SET solde = solde + ? WHERE id=?",
              (vers["montant"], vers[self.tiers_id_col]),
          )
        conn.execute(f"DELETE FROM {self.table} WHERE id=?", (vers_id,))
        conn.commit()
        messagebox.showinfo("Succès", "Versement supprimé.")
        self.refresh()
      except Exception as e:
        messagebox.showerror("Erreur", str(e))
      finally:
        conn.close()

  def print_versements(self):
    data = []
    for item in self.tree.get_children():
      data.append(self.tree.item(item)["values"])
    headers = ["Numéro", "Date", self.tiers_label, "Montant", "Mode", "Référence"]
    print_preview(
        data, f"LISTE DES VERSEMENTS {self.tiers_label.upper()}S", headers
    )