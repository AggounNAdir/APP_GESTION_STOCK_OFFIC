import math
import sqlite3
from datetime import datetime

from api import rbac
from api.chargement_service import (
    annuler_bon_chargement,
    creer_bon_chargement,
    decharger_camion,
    supprimer_bon_chargement,
)
from api.db import get_conn
from modules.core import *
from modules.vendeurfiche import NouveauChargementDialog


class ChargementPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.vendeurs = {}
        self.produits = {}
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(fill="x", padx=20, pady=(15, 8))
        lbl(header, "🚚 Bons de chargement", 16, True, CLR_ACCENT).pack(side="left")
        tk.Button(
            header, text="🔄 Actualiser", command=self.refresh,
            bg=CLR_ACCENT, fg="white", relief="flat", padx=12, pady=5,
        ).pack(side="right")

        form = tk.LabelFrame(
            self, text="Nouveau chargement — Dépôt vers camion",
            bg=CLR_CARD, fg=CLR_ACCENT, padx=10, pady=8,
        )
        form.pack(fill="x", padx=20, pady=5)

        lbl(form, "Vendeur :", color=CLR_TEXT).grid(row=0, column=0, padx=4, pady=4)
        self.vendeur_var = tk.StringVar()
        self.vendeur_combo = combo(form, [], width=27, textvariable=self.vendeur_var, state="readonly")
        self.vendeur_combo.grid(row=0, column=1, padx=4, pady=4)
        self.vendeur_combo.bind("<<ComboboxSelected>>", self._refresh_stock_camion)

        lbl(form, "Produit :", color=CLR_TEXT).grid(row=0, column=2, padx=(12, 4), pady=4)
        self.produit_var = tk.StringVar()
        self.produit_combo = combo(form, [], width=48, textvariable=self.produit_var, state="readonly")
        self.produit_combo.grid(row=0, column=3, padx=4, pady=4)

        lbl(form, "Colis :", color=CLR_TEXT).grid(row=0, column=4, padx=(12, 4), pady=4)
        self.quantite_entry = entry(form, width=9)
        self.quantite_entry.grid(row=0, column=5, padx=4, pady=4)
        tk.Button(
            form, text="Ajouter", command=self._ajouter_ligne,
            bg=CLR_ACCENT, fg="white", relief="flat", padx=10,
        ).grid(row=0, column=6, padx=6, pady=4)

        lbl(form, "Observations :", color=CLR_TEXT).grid(row=1, column=0, padx=4, pady=4, sticky="w")
        self.observations_entry = entry(form, width=75)
        self.observations_entry.grid(row=1, column=1, columnspan=4, padx=4, pady=4, sticky="w")

        frame, self.draft_tree = make_tree(
            self, ["Produit", "Colis à charger", "Pièces", "Stock dépôt restant"], [280, 130, 110, 150]
        )
        frame.pack(fill="both", expand=True, padx=20, pady=(5, 3))

        actions = tk.Frame(self, bg=CLR_BG)
        actions.pack(fill="x", padx=20, pady=4)
        self.btn_retirer = tk.Button(
            actions, text="Retirer la ligne", command=self._retirer_ligne,
            bg=CLR_MUTED, fg="white", relief="flat", padx=10, pady=5,
        )
        self.btn_retirer.pack(side="left", padx=3)
        self.btn_valider = tk.Button(
            actions, text="✅ Valider le bon et charger le camion",
            command=self._valider_chargement, bg=CLR_GREEN, fg="white",
            relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=6,
        )
        self.btn_valider.pack(side="left", padx=3)
        self.btn_decharger = tk.Button(
            actions, text="↩️ Décharger le camion",
            command=self._decharger, bg=CLR_ORANGE, fg="white",
            relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=6,
        )
        self.btn_decharger.pack(side="left", padx=3)

        lower = tk.Frame(self, bg=CLR_BG)
        lower.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        stock_frame = tk.LabelFrame(
            lower, text="Stock actuel du camion sélectionné",
            bg=CLR_CARD, fg=CLR_ACCENT,
        )
        stock_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        stock_container, self.stock_tree = make_tree(
            stock_frame, ["Produit", "Colis", "Pièces"], [250, 90, 90]
        )
        stock_container.pack(fill="both", expand=True, padx=4, pady=4)

        history_frame = tk.LabelFrame(
            lower, text="Suivi des bons de chargement",
            bg=CLR_CARD, fg=CLR_ACCENT,
        )
        history_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        history_container, self.history_tree = make_tree(
            history_frame, ["N° Bon", "Date", "Vendeur", "Colis", "Statut"], [150, 100, 170, 80, 90]
        )
        history_container.pack(fill="both", expand=True, padx=4, pady=4)
        self.history_tree.bind("<Double-1>", lambda event: self._imprimer_bon())
        self.history_tree.bind("<<TreeviewSelect>>", self._selection_bon)

        history_actions = tk.Frame(history_frame, bg=CLR_CARD)
        history_actions.pack(fill="x", padx=5, pady=(0, 5))
        tk.Button(
            history_actions, text="👁 Détail / Imprimer",
            command=self._imprimer_bon, bg=CLR_ACCENT, fg="white",
            relief="flat", padx=10, pady=5,
        ).pack(side="left")
        self.btn_modifier_bon = tk.Button(
            history_actions, text="✏️ Modifier",
            command=self._modifier_bon, bg=CLR_GREEN, fg="white",
            relief="flat", padx=10, pady=5, state="disabled",
        )
        self.btn_modifier_bon.pack(side="left", padx=4)
        self.btn_annuler_bon = tk.Button(
            history_actions, text="⛔ Annuler le bon",
            command=self._annuler_bon, bg=CLR_RED, fg="white",
            relief="flat", padx=10, pady=5, state="disabled",
        )
        self.btn_annuler_bon.pack(side="left", padx=4)
        self.btn_supprimer_bon = tk.Button(
            history_actions, text="🗑 Supprimer définitivement",
            command=self._supprimer_bon, bg=CLR_RED, fg="white",
            relief="flat", padx=10, pady=5, state="disabled",
        )
        self.btn_supprimer_bon.pack(side="left", padx=4)
        self._appliquer_droits()

    def _appliquer_droits(self):
        autorise = rbac.peut(rbac.role_courant(), "gerer_chargements")
        etat = "normal" if autorise else "disabled"
        for bouton in (self.btn_retirer, self.btn_valider, self.btn_decharger):
            bouton.config(state=etat)
        self._selection_bon()

    def _selection_bon(self, event=None):
        autorise = rbac.peut(rbac.role_courant(), "gerer_chargements")
        selection = self.history_tree.selection()
        statut = self.history_tree.item(selection[0], "values")[4] if selection else None
        peut_modifier_ou_annuler = autorise and statut == "Validé"
        self.btn_modifier_bon.config(
            state="normal" if peut_modifier_ou_annuler else "disabled"
        )
        self.btn_annuler_bon.config(
            state="normal" if peut_modifier_ou_annuler else "disabled"
        )
        self.btn_supprimer_bon.config(
            state="normal" if autorise and statut in ("Validé", "Annulé") else "disabled"
        )

    def refresh(self):
        selection = self.vendeur_var.get()
        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT id, code, nom FROM vendeurs WHERE actif=1 ORDER BY nom"
            ).fetchall()
            self.vendeurs = {f"{r['code']} — {r['nom']}": r["id"] for r in rows}
            valeurs = list(self.vendeurs)
            self.vendeur_combo["values"] = valeurs
            self.vendeur_var.set(selection if selection in self.vendeurs else (valeurs[0] if valeurs else ""))

            produits = conn.execute(
                """SELECT id, code, designation, unite, stock_actuel,
                          COALESCE(facteur_conversion, 1) AS facteur
                   FROM produits WHERE actif=1 ORDER BY designation"""
            ).fetchall()
            self.produits = {str(r["id"]): dict(r) for r in produits}
            self._libelles_produits = {}
            for r in produits:
                libelle = (
                    f"{r['code']} — {r['designation']} "
                    f"(stock dépôt : {float(r['stock_actuel'] or 0):g} pièces)"
                )
                self._libelles_produits[libelle] = r["id"]
            self.produit_combo["values"] = list(self._libelles_produits)

            self.history_tree.delete(*self.history_tree.get_children())
            bons = conn.execute(
                """SELECT b.id, b.numero, b.date_chargement, b.total_colis, b.statut, v.nom
                   FROM bons_chargement b JOIN vendeurs v ON v.id=b.vendeur_id
                   ORDER BY b.id DESC LIMIT 200"""
            ).fetchall()
            for bon in bons:
                self.history_tree.insert(
                    "", "end", iid=str(bon["id"]),
                    values=(bon["numero"], bon["date_chargement"], bon["nom"],
                            f"{float(bon['total_colis'] or 0):g}", bon["statut"]),
                )
        finally:
            conn.close()
        self._refresh_stock_camion()
        self._selection_bon()

    def _modifier_bon(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon validé à modifier.")
            return
        bon_id = int(selection[0])
        conn = get_conn()
        try:
            vendeur = conn.execute(
                """SELECT v.id, v.code, v.nom
                   FROM bons_chargement b JOIN vendeurs v ON v.id=b.vendeur_id
                   WHERE b.id=? AND b.statut='Validé'""",
                (bon_id,),
            ).fetchone()
        finally:
            conn.close()
        if vendeur is None:
            messagebox.showwarning("Bon de chargement", "Seul un bon validé peut être modifié.")
            self.refresh()
            return
        dialog = NouveauChargementDialog(self, vendeur, bon_id=bon_id)
        self.wait_window(dialog)
        self.refresh()

    def _annuler_bon(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon validé à annuler.")
            return
        bon_id = int(selection[0])
        numero = self.history_tree.item(selection[0], "values")[0]
        if not messagebox.askyesno(
            "Annuler le bon de chargement",
            f"Annuler le bon {numero} ?\n"
            "Les quantités seront retournées au dépôt et l'opération restera dans l'historique.",
        ):
            return
        conn = get_conn()
        try:
            annuler_bon_chargement(conn, bon_id)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Annulation impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()
        messagebox.showinfo("Bon annulé", f"Le bon {numero} a été annulé.")

    def _supprimer_bon(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon à supprimer.")
            return
        bon_id = int(selection[0])
        valeurs = self.history_tree.item(selection[0], "values")
        numero, statut = valeurs[0], valeurs[4]
        if statut not in ("Validé", "Annulé"):
            messagebox.showwarning("Suppression impossible", "Le statut du bon ne permet pas sa suppression.")
            return
        confirmation = messagebox.askyesno(
            "Suppression définitive",
            f"Supprimer définitivement le bon {numero}, ses lignes et ses mouvements de stock ?\n"
            + (
                "Les quantités seront réintégrées au dépôt si elles sont encore dans le camion."
                if statut == "Validé"
                else "Le bon est déjà annulé; les stocks ne seront pas modifiés."
            ),
        )
        if not confirmation:
            return
        conn = get_conn()
        try:
            supprimer_bon_chargement(conn, bon_id)
        except (ValueError, RuntimeError, sqlite3.Error) as exc:
            messagebox.showerror("Suppression impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()
        messagebox.showinfo("Bon supprimé", f"Le bon {numero} et son historique de mouvements ont été supprimés.")

    def _refresh_stock_camion(self, event=None):
        self.stock_tree.delete(*self.stock_tree.get_children())
        vendeur_id = self.vendeurs.get(self.vendeur_var.get())
        if not vendeur_id:
            return
        conn = get_conn()
        try:
            rows = conn.execute(
                """SELECT p.designation, sc.quantite_colis, sc.quantite_pieces
                   FROM stock_camion_vendeur sc JOIN produits p ON p.id=sc.produit_id
                   WHERE sc.vendeur_id=? AND (sc.quantite_colis > 0 OR sc.quantite_pieces > 0)
                   ORDER BY p.designation""",
                (vendeur_id,),
            ).fetchall()
            for row in rows:
                self.stock_tree.insert(
                    "", "end",
                    values=(row["designation"], f"{float(row['quantite_colis'] or 0):g}",
                            f"{float(row['quantite_pieces'] or 0):g}"),
                )
        finally:
            conn.close()

    def _ajouter_ligne(self):
        libelle = self.produit_var.get()
        produit_id = self._libelles_produits.get(libelle)
        if produit_id is None:
            messagebox.showwarning("Produit", "Sélectionnez un produit.")
            return
        try:
            quantite = float(self.quantite_entry.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Quantité", "Saisissez un nombre de colis valide.")
            return
        if not math.isfinite(quantite) or quantite <= 0:
            messagebox.showwarning("Quantité", "La quantité doit être supérieure à zéro.")
            return

        produit = self.produits[str(produit_id)]
        facteur = float(produit["facteur"] or 1)
        facteur = facteur if facteur > 0 else 1
        stock = float(produit["stock_actuel"] or 0)
        existing = sum(
            float(self.draft_tree.item(iid, "values")[1])
            for iid in self.draft_tree.get_children()
            if int(iid) == produit_id
        )
        if (existing + quantite) * facteur > stock:
            messagebox.showerror(
                "Stock insuffisant",
                f"Stock dépôt disponible : {stock:g} pièce(s).",
            )
            return

        quantite += existing
        if self.draft_tree.exists(str(produit_id)):
            self.draft_tree.delete(str(produit_id))
        restant = stock - quantite * facteur
        self.draft_tree.insert(
            "", "end", iid=str(produit_id),
            values=(produit["designation"], f"{quantite:g}", f"{quantite * facteur:g}", f"{restant:g}"),
        )
        self.quantite_entry.delete(0, tk.END)

    def _retirer_ligne(self):
        for iid in self.draft_tree.selection():
            self.draft_tree.delete(iid)

    def _valider_chargement(self):
        vendeur_id = self.vendeurs.get(self.vendeur_var.get())
        lignes = [
            (int(iid), float(self.draft_tree.item(iid, "values")[1]))
            for iid in self.draft_tree.get_children()
        ]
        if not vendeur_id:
            messagebox.showwarning("Vendeur", "Aucun vendeur actif n'est sélectionné.")
            return
        if not lignes:
            messagebox.showwarning("Chargement", "Ajoutez au moins un produit.")
            return
        if not messagebox.askyesno(
            "Confirmation",
            "Valider le bon et transférer les quantités du dépôt vers le camion ?",
        ):
            return

        conn = get_conn()
        try:
            bon = creer_bon_chargement(
                conn, vendeur_id, lignes, self.observations_entry.get()
            )
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Chargement impossible", str(exc))
            return
        finally:
            conn.close()

        self.draft_tree.delete(*self.draft_tree.get_children())
        self.observations_entry.delete(0, tk.END)
        self.refresh()
        messagebox.showinfo(
            "Chargement validé",
            f"Bon {bon['numero']} créé.\n"
            f"{bon['total_colis']:g} colis ({bon['total_pieces']:g} pièces) transférés.",
        )

    def _decharger(self):
        vendeur_id = self.vendeurs.get(self.vendeur_var.get())
        if not vendeur_id:
            messagebox.showwarning("Vendeur", "Aucun vendeur actif n'est sélectionné.")
            return
        if not messagebox.askyesno(
            "Déchargement du soir",
            "Réintégrer au dépôt tout le stock restant dans le camion de ce vendeur ?",
        ):
            return
        conn = get_conn()
        try:
            resultat = decharger_camion(conn, vendeur_id)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Déchargement impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()
        if resultat["produits"] == 0:
            messagebox.showinfo("Déchargement", "Le camion est déjà vide.")
        else:
            messagebox.showinfo(
                "Déchargement terminé",
                f"{resultat['total_colis']:g} colis "
                f"({resultat['total_pieces']:g} pièces) réintégrés au dépôt.",
            )

    def _imprimer_bon(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon à afficher ou imprimer.")
            return
        bon_id = int(selected[0])
        conn = get_conn()
        try:
            bon = conn.execute(
                """SELECT b.numero, b.date_chargement, b.total_colis, b.total_pieces,
                          b.observations, v.code, v.nom
                   FROM bons_chargement b JOIN vendeurs v ON v.id=b.vendeur_id
                   WHERE b.id=?""",
                (bon_id,),
            ).fetchone()
            lignes = conn.execute(
                """SELECT p.code, p.designation, p.unite, lc.quantite_colis, lc.quantite_pieces
                   FROM lignes_chargement lc JOIN produits p ON p.id=lc.produit_id
                   WHERE lc.chargement_id=? ORDER BY p.designation""",
                (bon_id,),
            ).fetchall()
        finally:
            conn.close()
        if bon is None:
            messagebox.showerror("Bon de chargement", "Ce bon n'existe plus.")
            return
        data = [
            [r["code"], r["designation"], f"{float(r['quantite_colis']):g}",
             r["unite"] or "", f"{float(r['quantite_pieces']):g}"]
            for r in lignes
        ]
        footer = (
            f"Bon : {bon['numero']}\nDate : {bon['date_chargement']}\n"
            f"Vendeur : {bon['code']} — {bon['nom']}\n"
            f"Total : {float(bon['total_colis'] or 0):g} colis / "
            f"{float(bon['total_pieces'] or 0):g} pièces\n"
            f"Observations : {bon['observations'] or '—'}\n"
            f"Imprimé le : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        print_preview(
            data, f"BON DE CHARGEMENT — {bon['numero']}",
            ["Code", "Produit", "Colis", "Unité", "Pièces"],
            footer_text=footer,
        )
