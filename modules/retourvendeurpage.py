"""Page d'administration « Retours vendeurs » : confirmer les retours et décider du sort de chaque produit."""
import sqlite3
from tkinter import simpledialog

from api import rbac
from api import retour_vendeur_service as rtv
from api.db import get_conn
from modules.core import *


class RetourVendeurPage(tk.Frame):
    INTERVALLE_AUTO_MS = 30000

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()
        self.after(self.INTERVALLE_AUTO_MS, self._auto_maj)

    # ─────────────────────────── construction ───────────────────────────
    def _build(self):
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(fill="x", padx=20, pady=(15, 6))
        lbl(header, "↩️ Retours des vendeurs", 16, True, CLR_ACCENT).pack(side="left")
        tk.Button(header, text="🔄 Actualiser", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat", padx=12, pady=5).pack(side="right")
        self.badge = tk.Label(header, text="", bg=CLR_ORANGE, fg="white",
                              font=("Segoe UI", 9, "bold"), padx=10, pady=4)

        # Situation du dépôt : où est la marchandise ?
        self.cartes = {}
        bandeau = tk.LabelFrame(self, text="Situation du dépôt (valeurs au prix d'achat)", bg=CLR_CARD, fg=CLR_ACCENT)
        bandeau.pack(fill="x", padx=20, pady=(0, 6))
        grille = tk.Frame(bandeau, bg=CLR_CARD)
        grille.pack(fill="x", padx=6, pady=6)
        defs = [
            ("stock_vendable_valeur", "Stock vendable", CLR_GREEN),
            ("retours_a_traiter_valeur", "Retours à traiter", CLR_ORANGE),
            ("stock_camions_valeur", "Chez les vendeurs (camions)", CLR_ACCENT),
            ("casse_mois_vendeur_valeur", "Casse du mois — vendeurs", CLR_RED),
            ("casse_mois_entreprise_valeur", "Casse du mois — entreprise", CLR_RED),
            ("a_retourner_fournisseur_valeur", "À retourner au fournisseur", CLR_PURPLE),
        ]
        for i, (cle, titre, couleur) in enumerate(defs):
            carte = tk.Frame(grille, bg=CLR_BG, padx=10, pady=6)
            carte.grid(row=0, column=i, sticky="nsew", padx=3)
            grille.columnconfigure(i, weight=1)
            tk.Label(carte, text=titre, bg=CLR_BG, fg=CLR_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            v = tk.Label(carte, text="—", bg=CLR_BG, fg=couleur, font=("Segoe UI", 12, "bold"))
            v.pack(anchor="w")
            self.cartes[cle] = v

        # 1) demandes à confirmer
        demandes = tk.LabelFrame(self, text="1. Demandes de retour des vendeurs", bg=CLR_CARD, fg=CLR_ACCENT)
        demandes.pack(fill="x", padx=20, pady=(0, 6))
        cont, self.tree_demandes = make_tree(
            demandes,
            ["N° Retour", "Date", "Vendeur", "Retourné par", "Produits", "Colis", "Statut", "À décider"],
            [140, 130, 150, 150, 80, 80, 100, 90],
        )
        cont.pack(fill="x", expand=True, padx=4, pady=4)
        self.tree_demandes.configure(height=5)
        self.tree_demandes.bind("<Double-1>", lambda e: self._detail())
        self.tree_demandes.bind("<<TreeviewSelect>>", lambda e: self._maj_boutons())
        actions = tk.Frame(demandes, bg=CLR_CARD)
        actions.pack(fill="x", padx=5, pady=(0, 5))
        tk.Button(actions, text="👁 Détail", command=self._detail, bg=CLR_ACCENT, fg="white",
                  relief="flat", padx=10, pady=5).pack(side="left")
        self.btn_confirmer = tk.Button(actions, text="✅ Confirmer le retour", command=self._confirmer,
                                       bg=CLR_GREEN, fg="white", relief="flat", padx=10, pady=5, state="disabled")
        self.btn_confirmer.pack(side="left", padx=4)
        self.btn_rejeter = tk.Button(actions, text="❌ Rejeter", command=self._rejeter,
                                     bg=CLR_RED, fg="white", relief="flat", padx=10, pady=5, state="disabled")
        self.btn_rejeter.pack(side="left", padx=4)
        tk.Label(actions, text="Confirmer = le camion du vendeur baisse et les produits entrent en « retours à traiter ».",
                 bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 8)).pack(side="left", padx=10)

        # 2) produits retournés à décider
        traiter = tk.LabelFrame(self, text="2. Produits retournés à traiter (zone « retours » du dépôt)",
                                bg=CLR_CARD, fg=CLR_ACCENT)
        traiter.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        cont2, self.tree_lignes = make_tree(
            traiter,
            ["N° Retour", "Vendeur", "Retourné par", "Produit", "Colis", "Pièces", "Motif", "Commentaire", "Confirmé le"],
            [130, 130, 130, 200, 60, 70, 150, 160, 120],
        )
        cont2.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree_lignes.bind("<<TreeviewSelect>>", lambda e: self._maj_boutons())
        actions2 = tk.Frame(traiter, bg=CLR_CARD)
        actions2.pack(fill="x", padx=5, pady=(0, 5))
        self.boutons_decision = []
        for texte, couleur, decision, imputation in [
            ("♻ Remettre en stock vendable", CLR_GREEN, "VENDABLE", None),
            ("💥 Casse — imputer au vendeur", CLR_RED, "CASSE", "VENDEUR"),
            ("💥 Casse — perte entreprise", CLR_ORANGE, "CASSE", "ENTREPRISE"),
            ("🏭 À retourner au fournisseur", CLR_PURPLE, "FOURNISSEUR", None),
        ]:
            b = tk.Button(actions2, text=texte, bg=couleur, fg="white", relief="flat", padx=10, pady=5,
                          state="disabled", command=lambda d=decision, i=imputation: self._decider(d, i))
            b.pack(side="left", padx=(0, 4))
            self.boutons_decision.append(b)

    # ─────────────────────────── données ───────────────────────────
    def _utilisateur(self):
        return (rbac.get_utilisateur_connecte() or {}).get("nom_complet") or ""

    def _autorise(self):
        return rbac.peut(rbac.role_courant(), "gerer_chargements")

    def refresh(self):
        conn = get_conn()
        try:
            demandes = rtv.lister_retours(conn, limite=60)
            lignes = rtv.lignes_a_traiter(conn)
            sit = rtv.situation_depot(conn)
        finally:
            conn.close()

        gardees = set(self.tree_demandes.selection())
        self.tree_demandes.delete(*self.tree_demandes.get_children())
        demandes.sort(key=lambda d: (d["statut"] != rtv.STATUT_ATTENTE, -d["id"]))
        for d in demandes:
            self.tree_demandes.insert(
                "", "end", iid=str(d["id"]),
                tags=(("attente",) if d["statut"] == rtv.STATUT_ATTENTE else ()),
                values=(d["numero"], str(d["date_demande"])[:16].replace("T", " "), d["vendeur_nom"],
                        d["retourne_par"] or "", d["nb_lignes"], f"{d['total_colis']:g}", d["statut"],
                        d["lignes_a_decider"] if d["statut"] == rtv.STATUT_CONFIRME else ""),
            )
        self.tree_demandes.tag_configure("attente", background="#fff3cd")
        restantes = [i for i in gardees if self.tree_demandes.exists(i)]
        if restantes:
            self.tree_demandes.selection_set(restantes)

        gardees = set(self.tree_lignes.selection())
        self.tree_lignes.delete(*self.tree_lignes.get_children())
        for l in lignes:
            self.tree_lignes.insert(
                "", "end", iid=str(l["id"]),
                values=(l["numero"], l["vendeur_nom"], l["retourne_par"] or "", l["designation"],
                        f"{l['colis']:g}", f"{l['quantite_pieces']:g}", l["motif_libelle"],
                        l["commentaire"] or "", str(l["date_confirmation"] or "")[:16].replace("T", " ")),
            )
        restantes = [i for i in gardees if self.tree_lignes.exists(i)]
        if restantes:
            self.tree_lignes.selection_set(restantes)

        for cle, widget in self.cartes.items():
            widget.config(text=f"{sit[cle]:,.2f}")
        self._maj_badge(sit["demandes_en_attente"] + sit["lignes_a_decider"], sit)
        self._maj_boutons()

    def _auto_maj(self):
        """Rafraîchissement automatique (garde les sélections) ; s'arrête avec la page."""
        if not self.winfo_exists():
            return
        try:
            self.refresh()
        except sqlite3.Error:
            pass
        self.after(self.INTERVALLE_AUTO_MS, self._auto_maj)

    def _maj_badge(self, n, sit):
        if n > 0:
            self.badge.config(text=f"⚠ {sit['demandes_en_attente']} demande(s) à confirmer · "
                                   f"{sit['lignes_a_decider']} produit(s) à décider")
            if not self.badge.winfo_ismapped():
                self.badge.pack(side="right", padx=10)
        else:
            self.badge.pack_forget()
        racine = self.winfo_toplevel()
        if hasattr(racine, "_maj_badge_retours_vendeur"):
            racine._maj_badge_retours_vendeur()

    def _maj_boutons(self):
        autorise = self._autorise()
        sel = self.tree_demandes.selection()
        attente = bool(sel) and self.tree_demandes.item(sel[0], "values")[6] == rtv.STATUT_ATTENTE
        etat = "normal" if autorise and attente else "disabled"
        self.btn_confirmer.config(state=etat)
        self.btn_rejeter.config(state=etat)
        etat_dec = "normal" if autorise and self.tree_lignes.selection() else "disabled"
        for b in self.boutons_decision:
            b.config(state=etat_dec)

    # ─────────────────────────── actions ───────────────────────────
    def _retour_selectionne(self):
        sel = self.tree_demandes.selection()
        if not sel:
            messagebox.showwarning("Retour vendeur", "Sélectionnez un retour dans la liste.")
            return None
        return int(sel[0])

    def _detail(self):
        retour_id = self._retour_selectionne()
        if retour_id is None:
            return
        conn = get_conn()
        try:
            r = rtv.detail_retour(conn, retour_id)
        finally:
            conn.close()
        lignes = []
        for l in r["lignes"]:
            t = f"• {l['designation']} : {l['colis']:g} colis ({l['quantite_pieces']:g} pcs) — {l['motif_libelle']}"
            if l["commentaire"]:
                t += f" ({l['commentaire']})"
            if l["decision_libelle"]:
                t += f"\n    → {l['decision_libelle']}"
                if l["imputation"]:
                    t += f" — {rtv.IMPUTATIONS[l['imputation']]} ({l['valeur_perte']:,.2f})"
            lignes.append(t)
        texte = (f"Retour {r['numero']} — {r['vendeur_nom']} — {r['statut']}\n"
                 f"Rapporté par : {r['retourne_par'] or '—'}\n\n" + "\n".join(lignes))
        if r["observations"]:
            texte += f"\n\nObservations : {r['observations']}"
        if r["motif_rejet"]:
            texte += f"\nMotif du rejet : {r['motif_rejet']}"
        messagebox.showinfo("Retour du vendeur", texte)

    def _confirmer(self):
        if not self._autorise():
            return
        retour_id = self._retour_selectionne()
        if retour_id is None:
            return
        if not messagebox.askyesno(
            "Confirmer le retour",
            "Le stock du camion du vendeur va baisser de la quantité retournée, la situation du vendeur "
            "sera ajustée et les produits entreront en « retours à traiter ».\n\nConfirmer ?",
        ):
            return
        conn = get_conn()
        try:
            r = rtv.confirmer_retour(conn, retour_id, self._utilisateur())
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Confirmation impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()
        messagebox.showinfo("Retour confirmé",
                            f"Retour {r['numero']} confirmé.\nDécidez maintenant du sort des produits dans la liste 2.")

    def _rejeter(self):
        if not self._autorise():
            return
        retour_id = self._retour_selectionne()
        if retour_id is None:
            return
        motif = simpledialog.askstring("Rejeter le retour", "Motif du rejet (obligatoire) :", parent=self)
        if motif is None:
            return
        conn = get_conn()
        try:
            rtv.rejeter_retour(conn, retour_id, self._utilisateur(), motif)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Rejet impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()

    def _decider(self, decision, imputation):
        if not self._autorise():
            return
        ids = [int(i) for i in self.tree_lignes.selection()]
        if not ids:
            messagebox.showwarning("Retour vendeur", "Sélectionnez un ou plusieurs produits à traiter.")
            return
        libelle = rtv.DECISIONS[decision] + (f" — {rtv.IMPUTATIONS[imputation]}" if imputation else "")
        if not messagebox.askyesno("Décision", f"{len(ids)} produit(s) : « {libelle} ».\nCette décision est définitive. Continuer ?"):
            return
        conn = get_conn()
        erreurs = []
        try:
            for ligne_id in ids:
                try:
                    rtv.decider_ligne(conn, ligne_id, decision, self._utilisateur(), imputation)
                except (ValueError, sqlite3.Error) as exc:
                    erreurs.append(str(exc))
        finally:
            conn.close()
        self.refresh()
        if erreurs:
            messagebox.showerror("Décision partielle", "\n".join(sorted(set(erreurs))))
