import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from modules.core import *


class ProspectsPage(tk.Frame):

  def __init__(self, parent):
    super().__init__(parent, bg=CLR_BG)
    self._build()
    self.refresh()

  def _build(self):
    # En-tête
    hdr = tk.Frame(self, bg=CLR_BG)
    hdr.pack(fill="x", padx=20, pady=(20, 10))

    lbl(hdr, "🎯  Prospects Créés par les Vendeurs (Androway)", 16, True).pack(
        side="left"
    )

    btn_box = tk.Frame(hdr, bg=CLR_BG)
    btn_box.pack(side="right")

    tk.Button(
        btn_box,
        text="🔄 Actualiser",
        command=self.refresh,
        bg=CLR_ACCENT,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

    # Filtre par Statut + Recherche
    sf = tk.Frame(self, bg=CLR_BG)
    sf.pack(fill="x", padx=20, pady=5)

    lbl(sf, "Statut:", color=CLR_MUTED).pack(side="left", padx=(0, 6))
    self.statut_var = tk.StringVar(value="Tous")
    self.statut_cb = ttk.Combobox(
        sf,
        textvariable=self.statut_var,
        state="readonly",
        values=["Tous", "Nouveau", "Converti"],
        width=15,
    )
    self.statut_cb.pack(side="left", padx=(0, 15))
    self.statut_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

    lbl(sf, "Recherche (Nom, Code, Ville):", color=CLR_MUTED).pack(
        side="left", padx=(0, 6)
    )
    self.search_var = tk.StringVar()
    self.search_var.trace_add("write", lambda *a: self.refresh())
    entry(sf, width=30, textvariable=self.search_var).pack(side="left")

    # Tableau des prospects
    cols = [
        "Code",
        "Nom Prospect",
        "Téléphone",
        "Adresse",
        "Wilaya",
        "Statut",
        "Date Création",
    ]
    widths = [100, 200, 120, 180, 120, 90, 140]
    tf, self.tree = make_tree(self, cols, widths)
    tf.pack(fill="both", expand=True, padx=20, pady=10)

    # Boutons d'action
    bf = tk.Frame(self, bg=CLR_BG)
    bf.pack(fill="x", padx=20, pady=(0, 15))

    tk.Button(
        bf,
        text="🗑 Supprimer Prospect",
        command=self.supprimer_prospect,
        bg=CLR_RED,
        fg="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=4)

  def refresh(self):
    conn = get_conn()
    try:
      query = """
                SELECT id, code, nom, tel, adresse, wilaya, statut, date_creation
                FROM prospects_clients
                WHERE 1=1
            """
      params = []

      # Filtre par statut (Nouveau, Converti, Tous)
      if self.statut_var.get() != "Tous":
        query += " AND statut = ?"
        params.append(self.statut_var.get())

      # Recherche texte insensible à la casse
      q = self.search_var.get().strip().lower()
      if q:
        query += """ AND (
                    LOWER(COALESCE(nom, '')) LIKE ? OR 
                    LOWER(COALESCE(code, '')) LIKE ? OR 
                    LOWER(COALESCE(adresse, '')) LIKE ? OR 
                    LOWER(COALESCE(wilaya, '')) LIKE ?
                )"""
        p_term = f"%{q}%"
        params.extend([p_term, p_term, p_term, p_term])

      query += " ORDER BY id DESC"
      rows = conn.execute(query, tuple(params)).fetchall()

      self.tree.delete(*self.tree.get_children())
      for r in rows:
        dt = str(r["date_creation"] or "").replace("T", " ")[:19]
        self.tree.insert(
            "",
            "end",
            iid=str(r["id"]),
            values=(
                r["code"] or "-",
                r["nom"] or "-",
                r["tel"] or "-",
                r["adresse"] or "-",
                r["wilaya"] or "-",
                r["statut"] or "Nouveau",
                dt or "-",
            ),
        )
    except Exception as e:
      print(f"Erreur chargement prospects_clients: {e}")
      messagebox.showerror(
          "Erreur", f"Erreur lors du chargement de la table prospects: {e}"
      )
    finally:
      conn.close()

  def supprimer_prospect(self):
    sel = self.tree.selection()
    if not sel:
      messagebox.showwarning(
          "Sélection", "Veuillez sélectionner un prospect dans la liste."
      )
      return
    prospect_id = int(sel[0])
    if not messagebox.askyesno(
        "Confirmation", "Voulez-vous vraiment supprimer ce prospect ?"
    ):
      return
    conn = get_conn()
    try:
      conn.execute(
          "DELETE FROM prospects_clients WHERE id = ?", (prospect_id,)
      )
      conn.commit()
      self.refresh()
      messagebox.showinfo("Succès", "Prospect supprimé avec succès.")
    except Exception as e:
      messagebox.showerror("Erreur", f"Erreur lors de la suppression : {e}")
    finally:
      conn.close()