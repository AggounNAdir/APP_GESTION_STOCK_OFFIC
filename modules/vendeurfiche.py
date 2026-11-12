"""
Dossier complet du vendeur sélectionné (fenêtre « Vendeurs »).

Un seul panneau à onglets qui regroupe TOUT ce qui concerne le vendeur :
situation, bons de chargement, stock camion, ventes, versements, prospects,
commandes et pointages de tournée. Les requêtes sont dans
api/vendeur_dossier.py ; ici on ne fait que de l'affichage et des actions.
"""
import math
import sqlite3
from datetime import date, datetime

from api import rbac
from api import vendeur_dossier as dossier
from api.chargement_service import (
    annuler_bon_chargement,
    creer_bon_chargement,
    decharger_camion,
    modifier_bon_chargement,
    supprimer_bon_chargement,
)
from api.db import get_conn
from modules import commande_service as cmd_service
from modules.core import *


def fmt_da(valeur) -> str:
    """12345.5 -> '12 345,50 DA'."""
    try:
        v = float(valeur or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}".replace(",", " ").replace(".", ",") + " DA"


def fmt_qte(valeur) -> str:
    try:
        return f"{float(valeur or 0):g}"
    except (TypeError, ValueError):
        return "0"


def _date_courte(valeur) -> str:
    return str(valeur or "").replace("T", " ")[:16]


# ═══════════════════════ Dialogue : nouveau bon de chargement ═══════════════════════

class NouveauChargementDialog(tk.Toplevel):
    """Crée ou modifie un bon en conservant les stocks et le journal synchronisés."""

    def __init__(self, parent, vendeur, bon_id=None):
        super().__init__(parent)
        self.vendeur = vendeur
        self.bon_id = bon_id
        self.resultat = None
        self.produits = {}
        self._libelles = {}
        self._original_pieces = {}
        self.title(
            f"{'Modifier le bon' if bon_id else 'Nouveau chargement'} — "
            f"{vendeur['code']} {vendeur['nom']}"
        )
        self.configure(bg=CLR_BG)
        self.grab_set()
        center_window(self, 760, 520)
        self._build()
        self._charger_produits()

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=16, pady=12)
        f.pack(fill="both", expand=True)
        lbl(f, f"🚚 Chargement du camion de {self.vendeur['nom']}", 12, True, CLR_ACCENT).pack(anchor="w")

        ligne = tk.Frame(f, bg=CLR_BG)
        ligne.pack(fill="x", pady=(10, 4))
        lbl(ligne, "Produit :").pack(side="left")
        self.produit_var = tk.StringVar()
        self.produit_combo = combo(ligne, [], width=50, textvariable=self.produit_var, state="readonly")
        self.produit_combo.pack(side="left", padx=6)
        lbl(ligne, "Colis :").pack(side="left", padx=(8, 0))
        self.qte_entry = entry(ligne, width=8)
        self.qte_entry.pack(side="left", padx=6)
        self.qte_entry.bind("<Return>", lambda e: self._ajouter())
        tk.Button(ligne, text="Ajouter", command=self._ajouter, bg=CLR_ACCENT, fg="white",
                  relief="flat", padx=10).pack(side="left")

        tf, self.tree = make_tree(
            f, ["Produit", "Colis", "Pièces", "Stock dépôt restant"], [300, 90, 90, 150])
        tf.pack(fill="both", expand=True, pady=6)

        obs = tk.Frame(f, bg=CLR_BG)
        obs.pack(fill="x")
        lbl(obs, "Observations :").pack(side="left")
        self.obs_entry = entry(obs, width=70)
        self.obs_entry.pack(side="left", padx=6)

        btns = tk.Frame(f, bg=CLR_BG)
        btns.pack(fill="x", pady=(10, 0))
        tk.Button(
            btns,
            text="💾 Enregistrer les modifications" if self.bon_id else "✅ Valider et charger le camion",
            command=self._valider,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=14, pady=6).pack(side="left", padx=3)
        tk.Button(btns, text="Retirer la ligne", command=self._retirer, bg=CLR_MUTED, fg="white",
                  relief="flat", padx=10, pady=6).pack(side="left", padx=3)
        tk.Button(btns, text="Annuler", command=self.destroy, bg=CLR_RED, fg="white",
                  relief="flat", padx=14, pady=6).pack(side="right", padx=3)

    def _charger_produits(self):
        conn = get_conn()
        try:
            if self.bon_id:
                bon = conn.execute(
                    "SELECT observations, statut FROM bons_chargement WHERE id=?",
                    (self.bon_id,),
                ).fetchone()
                if bon is None or bon["statut"] != "Validé":
                    messagebox.showerror(
                        "Modification impossible",
                        "Le bon n'existe plus ou n'est plus validé.",
                        parent=self,
                    )
                    self.destroy()
                    return
                self.obs_entry.insert(0, bon["observations"] or "")
            rows = conn.execute(
                """SELECT id, code, designation, stock_actuel,
                          COALESCE(facteur_conversion, 1) AS facteur
                   FROM produits
                   WHERE actif=1 OR id IN (
                       SELECT produit_id FROM lignes_chargement WHERE chargement_id=?
                   )
                   ORDER BY designation""",
                (self.bon_id,),
            ).fetchall()
            anciennes = conn.execute(
                """SELECT lc.produit_id, SUM(lc.quantite_colis) AS colis,
                          SUM(lc.quantite_pieces) AS pieces
                   FROM lignes_chargement lc
                   WHERE lc.chargement_id=?
                   GROUP BY lc.produit_id""",
                (self.bon_id,),
            ).fetchall() if self.bon_id else []
        finally:
            conn.close()
        for r in rows:
            self.produits[r["id"]] = dict(r)
            lib = f"{r['code']} — {r['designation']} (dépôt : {fmt_qte(r['stock_actuel'])} pièces)"
            self._libelles[lib] = r["id"]
        self.produit_combo["values"] = list(self._libelles)
        for ligne in anciennes:
            produit_id = ligne["produit_id"]
            self._original_pieces[produit_id] = float(ligne["pieces"] or 0)
            produit = self.produits[produit_id]
            stock = float(produit["stock_actuel"] or 0)
            self.tree.insert(
                "", "end", iid=str(produit_id),
                values=(
                    produit["designation"],
                    fmt_qte(ligne["colis"]),
                    fmt_qte(ligne["pieces"]),
                    fmt_qte(stock),
                ),
            )

    def _ajouter(self):
        pid = self._libelles.get(self.produit_var.get())
        if pid is None:
            messagebox.showwarning("Produit", "Sélectionnez un produit.", parent=self)
            return
        try:
            qte = float(self.qte_entry.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Quantité", "Saisissez un nombre de colis valide.", parent=self)
            return
        if not math.isfinite(qte) or qte <= 0:
            messagebox.showwarning("Quantité", "La quantité doit être supérieure à zéro.", parent=self)
            return
        p = self.produits[pid]
        facteur = float(p["facteur"] or 1)
        facteur = facteur if facteur > 0 else 1
        stock = float(p["stock_actuel"] or 0)
        deja = 0.0
        if self.tree.exists(str(pid)):
            deja = float(self.tree.item(str(pid), "values")[1])
            self.tree.delete(str(pid))
        total = deja + qte
        pieces_nouvelles = total * facteur
        pieces_originales = self._original_pieces.get(pid, 0.0)
        if pieces_nouvelles - pieces_originales > stock + 1e-9:
            messagebox.showerror("Stock insuffisant",
                                 f"Stock dépôt disponible : {fmt_qte(stock)} pièce(s).", parent=self)
            if deja:  # restaure la ligne supprimée
                self.tree.insert("", "end", iid=str(pid), values=(
                    p["designation"], fmt_qte(deja), fmt_qte(deja * facteur),
                    fmt_qte(stock - deja * facteur)))
            return
        self.tree.insert("", "end", iid=str(pid), values=(
            p["designation"], fmt_qte(total), fmt_qte(pieces_nouvelles),
            fmt_qte(stock - (pieces_nouvelles - pieces_originales))))
        self.qte_entry.delete(0, tk.END)

    def _retirer(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)

    def _valider(self):
        lignes = [(int(i), float(self.tree.item(i, "values")[1])) for i in self.tree.get_children()]
        if not lignes:
            messagebox.showwarning("Chargement", "Ajoutez au moins un produit.", parent=self)
            return
        titre = "Confirmer la modification" if self.bon_id else "Confirmation"
        question = (
            "Enregistrer les nouvelles lignes et ajuster les stocks dépôt/camion ?"
            if self.bon_id
            else "Valider le bon et transférer les quantités du dépôt vers le camion ?"
        )
        if not messagebox.askyesno(titre, question, parent=self):
            return
        conn = get_conn()
        try:
            if self.bon_id:
                self.resultat = modifier_bon_chargement(
                    conn, self.bon_id, lignes, self.obs_entry.get())
            else:
                self.resultat = creer_bon_chargement(
                    conn, self.vendeur["id"], lignes, self.obs_entry.get())
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Chargement impossible", str(exc), parent=self)
            return
        finally:
            conn.close()
        messagebox.showinfo(
            "Bon modifié" if self.bon_id else "Chargement validé",
            f"Bon {self.resultat['numero']} "
            f"{'modifié' if self.bon_id else 'créé'}.\n"
            f"{fmt_qte(self.resultat['total_colis'])} colis "
            f"({fmt_qte(self.resultat['total_pieces'])} pièces).", parent=self)
        self.destroy()


# ═══════════════════════════ Panneau dossier vendeur ═══════════════════════════

# ═══════════════════════ Dialogue : versement vendeur → administration ═══════════════════════

class VersementVendeurDialog(tk.Toplevel):
    """Le vendeur remet en espèces à l'administration l'argent encaissé."""

    def __init__(self, parent, vendeur, reste_a_verser):
        super().__init__(parent)
        self.vendeur = vendeur
        self.reste = float(reste_a_verser or 0)
        self.resultat = None
        self.title(f"Versement vendeur — {vendeur['code']} {vendeur['nom']}")
        self.configure(bg=CLR_BG)
        self.grab_set()
        center_window(self, 460, 380)
        self._build()

    def _build(self):
        cadre = tk.Frame(self, bg=CLR_BG, padx=20, pady=16)
        cadre.pack(fill="both", expand=True)
        lbl(cadre, "💵 VERSEMENT À L'ADMINISTRATION", 13, True, CLR_ACCENT).pack(pady=(0, 10))
        carte = tk.Frame(cadre, bg=CLR_CARD, padx=16, pady=12)
        carte.pack(fill="x")

        def ligne(libelle):
            r = tk.Frame(carte, bg=CLR_CARD)
            r.pack(fill="x", pady=4)
            lbl(r, libelle, 9, False, CLR_MUTED).pack(side="left")
            return r

        r = ligne("Vendeur :")
        lbl(r, f"{self.vendeur['code']} — {self.vendeur['nom']}", 9, True, CLR_TEXT).pack(side="right")
        r = ligne("Reste à verser :")
        tk.Label(r, text=fmt_da(self.reste), bg=CLR_CARD, fg=CLR_ORANGE,
                 font=("Segoe UI", 10, "bold")).pack(side="right")

        r = ligne("Date (AAAA-MM-JJ) :")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        entry(r, width=14, textvariable=self.date_var).pack(side="right")
        r = ligne("Montant reçu (DA) :")
        self.montant_var = tk.StringVar(value=f"{self.reste:.2f}" if self.reste > 0 else "")
        self.montant_entry = entry(r, width=14, textvariable=self.montant_var)
        self.montant_entry.pack(side="right")
        r = ligne("Référence :")
        self.ref_var = tk.StringVar()
        entry(r, width=22, textvariable=self.ref_var).pack(side="right")
        r = ligne("Observations :")
        self.obs_var = tk.StringVar()
        entry(r, width=22, textvariable=self.obs_var).pack(side="right")

        lbl(cadre, "Mode : espèces. Le reste à verser est recalculé automatiquement.",
            8, False, CLR_MUTED).pack(anchor="w", pady=(8, 0))
        btns = tk.Frame(cadre, bg=CLR_BG)
        btns.pack(fill="x", pady=(12, 0))
        tk.Button(btns, text="✅ Enregistrer", command=self._valider, bg=CLR_GREEN, fg="white",
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="right", padx=4)
        tk.Button(btns, text="Annuler", command=self.destroy, bg=CLR_MUTED, fg="white",
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="right", padx=4)
        self.montant_entry.focus_set()
        self.bind("<Return>", lambda e: self._valider())

    def _valider(self):
        try:
            montant = float(self.montant_var.get().replace(" ", "").replace(",", "."))
        except ValueError:
            messagebox.showwarning("Montant", "Montant invalide.", parent=self)
            return
        depassement = montant > self.reste + 0.005
        if depassement and not messagebox.askyesno(
            "Montant supérieur au reste à verser",
            f"Le montant saisi ({fmt_da(montant)}) dépasse le reste à verser "
            f"({fmt_da(max(self.reste, 0))}).\nEnregistrer quand même ?",
            parent=self,
        ):
            return
        session = rbac.get_utilisateur_connecte()
        conn = get_conn()
        try:
            self.resultat = dossier.creer_versement_admin(
                conn, self.vendeur["id"], montant,
                date_vers=self.date_var.get().strip(),
                reference=self.ref_var.get().strip(),
                observations=self.obs_var.get().strip(),
                cree_par=session["nom_complet"] if session else None,
                autoriser_depassement=depassement,
            )
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Versement impossible", str(exc), parent=self)
            return
        finally:
            conn.close()
        self.destroy()


class VendeurFichePanel(tk.Frame):
    """Dossier complet d'un vendeur. Appeler set_vendeur(id) à chaque sélection."""

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.vendeur_id = None
        self.vendeur = None
        self.date_debut = None
        self.date_fin = None
        self._build()
        self._afficher_vide()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._maj_legere())
        self.bind("<Map>", lambda e: self._maj_legere())
        self.after(10000, self._auto_maj)

    # ───────────── mise à jour légère (cartes de situation) ─────────────

    def _maj_legere(self):
        """Recalcule uniquement les cartes de situation et le solde de caisse.

        N'efface ni la sélection ni les listes : on peut donc l'appeler souvent
        (ventes/versements faits depuis le portail pendant que la fenêtre est ouverte).
        """
        if not self.vendeur_id or not self.winfo_exists():
            return
        conn = get_conn()
        try:
            sit = dossier.situation_vendeur(conn, self.vendeur_id, self.date_debut, self.date_fin)
            caisse = dossier.caisse_vendeur(conn, self.vendeur_id, self.date_debut, self.date_fin)
        except sqlite3.Error:
            return
        finally:
            conn.close()
        sit["verse_admin"] = caisse["periode_verse_admin"]
        sit["reste_a_verser"] = caisse["reste_a_verser"]
        sit["credit_accorde"] = caisse["creances_clients"]
        self._remplir_situation(sit)
        self._situation = sit
        self._reste_a_verser = caisse["reste_a_verser"]
        self.remise_solde.config(
            text=f"Reste à verser (cumul) : {fmt_da(caisse['reste_a_verser'])}   —   "
                 f"espèces encaissées : {fmt_da(caisse['cumul_encaisse_especes'])}   —   "
                 f"déjà versé : {fmt_da(caisse['cumul_verse_admin'])}")

    def _auto_maj(self):
        try:
            if self.winfo_exists():
                if self.winfo_ismapped():
                    self._maj_legere()
                self.after(10000, self._auto_maj)
        except tk.TclError:
            pass

    # ───────────── construction ─────────────

    def _build(self):
        # En-tête : nom du vendeur + période
        top = tk.Frame(self, bg=CLR_BG)
        top.pack(fill="x", padx=4, pady=(4, 2))
        self.titre_lbl = lbl(top, "", 12, True, CLR_ACCENT)
        self.titre_lbl.pack(side="left")

        tk.Button(top, text="🔄", command=self.refresh, bg=CLR_ACCENT, fg="white",
                  relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)
        for texte, cmd in (("Ce mois", self._periode_mois), ("Aujourd'hui", self._periode_jour),
                           ("Tout", self._periode_tout)):
            tk.Button(top, text=texte, command=cmd, bg=CLR_MUTED, fg="white",
                      relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)
        tk.Button(top, text="Appliquer", command=self._appliquer_periode, bg=CLR_GREEN, fg="white",
                  relief="flat", padx=8, cursor="hand2").pack(side="right", padx=(8, 2))
        self.fin_entry = entry(top, width=11)
        self.fin_entry.pack(side="right", padx=2)
        lbl(top, "au").pack(side="right")
        self.debut_entry = entry(top, width=11)
        self.debut_entry.pack(side="right", padx=2)
        lbl(top, "Période du (AAAA-MM-JJ) :", color=CLR_MUTED).pack(side="right", padx=(0, 4))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=2, pady=2)

        self._build_onglet_situation()
        self._build_onglet_chargements()
        self._build_onglet_camion()
        self._build_onglet_ventes()
        self._build_onglet_versements()
        self._build_onglet_remises()
        self._build_onglet_prospects()
        self._build_onglet_commandes()
        self._build_onglet_tournee()

    def _tab(self, titre):
        f = tk.Frame(self.nb, bg=CLR_BG)
        self.nb.add(f, text=titre)
        return f

    def _arbre(self, parent, colonnes, largeurs, hauteur=None, **pack):
        tf, tree = make_tree(parent, colonnes, largeurs)
        if hauteur:
            tree.configure(height=hauteur)
        tf.pack(fill=pack.pop("fill", "both"), expand=pack.pop("expand", True),
                padx=6, pady=pack.pop("pady", 4))
        return tree

    def _total_lbl(self, parent):
        l = lbl(parent, "", 9, True, CLR_TEXT)
        l.pack(anchor="e", padx=10, pady=(0, 4))
        return l

    # — Situation —
    def _build_onglet_situation(self):
        self.tab_sit = self._tab("📊 Situation")
        self.cartes = {}
        grille = tk.Frame(self.tab_sit, bg=CLR_BG)
        grille.pack(fill="x", padx=8, pady=8)
        defs = [
            ("ca", "Chiffre d'affaires", CLR_ACCENT),
            ("encaisse_total", "Encaissé (versements)", CLR_GREEN),
            ("encaisse_especes", "dont Espèces encaissées", CLR_GREEN),
            ("verse_admin", "Versé à l'administration", CLR_ACCENT),
            ("reste_a_verser", "RESTE À VERSER (cumul)", CLR_RED),
            ("credit_accorde", "Crédit en cours (reste dû)", CLR_ORANGE),
            ("nb_ventes", "Nombre de ventes", CLR_TEXT),
            ("nb_versements", "Nombre de versements", CLR_TEXT),
            ("nb_chargements", "Bons de chargement", CLR_TEXT),
            ("colis_charges", "Colis chargés", CLR_TEXT),
            ("camion_valeur", "Valeur du camion (actuel)", CLR_PURPLE),
            ("camion_colis", "Colis dans le camion", CLR_PURPLE),
            ("nb_prospects", "Prospects créés", CLR_TEXT),
            ("prospects_convertis", "Prospects convertis", CLR_TEXT),
            ("commandes_en_attente", "Commandes en attente", CLR_ORANGE),
            ("nb_pointages", "Pointages de tournée", CLR_TEXT),
        ]
        for i, (cle, titre, couleur) in enumerate(defs):
            carte = tk.Frame(grille, bg=CLR_CARD, padx=12, pady=8,
                             highlightthickness=1, highlightbackground=CLR_BORDER)
            carte.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="nsew")
            grille.grid_columnconfigure(i % 4, weight=1, uniform="cartes")
            tk.Label(carte, text=titre, bg=CLR_CARD, fg=CLR_MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w")
            v = tk.Label(carte, text="—", bg=CLR_CARD, fg=couleur, font=("Segoe UI", 13, "bold"))
            v.pack(anchor="w")
            self.cartes[cle] = v
        tk.Button(self.tab_sit, text="🖨 Imprimer la situation", command=self._imprimer_situation,
                  bg=CLR_ACCENT, fg="white", relief="flat", padx=12, pady=6,
                  cursor="hand2").pack(anchor="w", padx=12, pady=4)
        self.note_sit = lbl(
            self.tab_sit,
            "L'encaissement = somme des versements du vendeur (clients + prospects). "
            "Reste à verser = espèces encaissées (tout l'historique) − remises à l'administration. "
            "Crédit en cours = ce que les clients doivent encore (cumul, indépendant de la période). "
            "Les ventes annulées sont exclues.", 8, color=CLR_MUTED)
        self.note_sit.pack(anchor="w", padx=12)

    # — Chargements —
    def _build_onglet_chargements(self):
        t = self._tab("🚚 Chargements")
        barre = tk.Frame(t, bg=CLR_BG)
        barre.pack(fill="x", padx=6, pady=(6, 0))
        self.btn_charger = tk.Button(
            barre, text="➕ Nouveau chargement", command=self._nouveau_chargement,
            bg=CLR_GREEN, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_charger.pack(side="left", padx=2)
        self.btn_decharger = tk.Button(
            barre, text="↩️ Décharger le camion", command=self._decharger,
            bg=CLR_ORANGE, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_decharger.pack(side="left", padx=2)
        self.btn_modifier_chargement = tk.Button(
            barre, text="✏️ Modifier le bon", command=self._modifier_chargement,
            bg=CLR_GREEN, fg="white", relief="flat", padx=10, pady=5,
            cursor="hand2", state="disabled")
        self.btn_modifier_chargement.pack(side="left", padx=2)
        self.btn_annuler_chargement = tk.Button(
            barre, text="⛔ Annuler le bon", command=self._annuler_chargement,
            bg=CLR_RED, fg="white", relief="flat", padx=10, pady=5,
            cursor="hand2", state="disabled")
        self.btn_annuler_chargement.pack(side="left", padx=2)
        self.btn_supprimer_chargement = tk.Button(
            barre, text="🗑 Supprimer définitivement", command=self._supprimer_chargement,
            bg=CLR_RED, fg="white", relief="flat", padx=10, pady=5,
            cursor="hand2", state="disabled")
        self.btn_supprimer_chargement.pack(side="left", padx=2)
        tk.Button(barre, text="🖨 Imprimer le bon", command=self._imprimer_bon,
                  bg=CLR_ACCENT, fg="white", relief="flat", padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=2)
        self.chg_tree = self._arbre(
            t, ["N° bon", "Date", "Statut", "Colis", "Pièces", "Observations"],
            [150, 110, 90, 80, 80, 300], hauteur=6, pady=4)
        self.chg_tree.bind("<<TreeviewSelect>>", self._on_chargement_select)
        lbl(t, "Lignes du bon sélectionné :", 9, True, CLR_MUTED).pack(anchor="w", padx=8)
        self.chg_lignes = self._arbre(
            t, ["Code", "Produit", "Colis", "Unité", "Pièces"], [100, 300, 80, 80, 80],
            hauteur=6, pady=4)

    # — Camion —
    def _build_onglet_camion(self):
        t = self._tab("🛻 Stock camion")
        self.camion_tree = self._arbre(
            t, ["Code", "Produit", "Colis", "Pièces", "Prix vente", "Valeur", "Maj"],
            [90, 260, 70, 80, 100, 120, 130])
        self.camion_total = self._total_lbl(t)

    # — Ventes —
    def _build_onglet_ventes(self):
        t = self._tab("🧾 Ventes")
        self.ventes_tree = self._arbre(
            t, ["N° bon", "Date", "Client", "Total", "Versé", "Reste", "Statut"],
            [160, 100, 200, 110, 110, 110, 90])
        self.ventes_total = self._total_lbl(t)

    # — Versements —
    def _build_onglet_versements(self):
        t = self._tab("💰 Versements")
        self.vers_tree = self._arbre(
            t, ["N°", "Date", "Type", "Tiers", "Montant", "Mode", "Référence"],
            [150, 100, 80, 200, 110, 100, 150])
        self.vers_total = self._total_lbl(t)

    # — Versements à l'administration (remises de caisse) —
    def _build_onglet_remises(self):
        t = self._tab("🏦 Versements admin")
        barre = tk.Frame(t, bg=CLR_BG)
        barre.pack(fill="x", padx=6, pady=(6, 0))
        self.btn_remise = tk.Button(
            barre, text="➕ Nouveau versement vendeur", command=self._nouvelle_remise,
            bg=CLR_GREEN, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_remise.pack(side="left", padx=2)
        self.btn_annuler_remise = tk.Button(
            barre, text="⛔ Annuler le versement", command=self._annuler_remise,
            bg=CLR_RED, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_annuler_remise.pack(side="left", padx=2)
        self.remise_solde = lbl(t, "", 11, True, CLR_RED)
        self.remise_solde.pack(anchor="w", padx=10, pady=(6, 0))
        self.remise_tree = self._arbre(
            t, ["N°", "Date", "Montant", "Mode", "Référence", "Observations", "Statut", "Saisi par"],
            [140, 100, 120, 80, 130, 220, 80, 140])
        self.remise_total = self._total_lbl(t)

    # — Prospects —
    def _build_onglet_prospects(self):
        t = self._tab("🎯 Prospects")
        barre = tk.Frame(t, bg=CLR_BG)
        barre.pack(fill="x", padx=6, pady=(6, 0))
        tk.Button(barre, text="➕ Convertir en client officiel", command=self._convertir_prospect,
                  bg=CLR_ACCENT, fg="white", relief="flat", padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=2)
        self.prospects_tree = self._arbre(
            t, ["Code", "Nom", "Téléphone", "Adresse", "Wilaya", "Statut", "Solde", "Créé le"],
            [90, 180, 110, 180, 100, 80, 110, 130])
        self.prospects_total = self._total_lbl(t)

    # — Commandes —
    def _build_onglet_commandes(self):
        t = self._tab("📦 Commandes")
        barre = tk.Frame(t, bg=CLR_BG)
        barre.pack(fill="x", padx=6, pady=(6, 0))
        tk.Button(barre, text="🔍 Détail", command=self._detail_commande,
                  bg=CLR_ACCENT, fg="white", relief="flat", padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=2)
        self.btn_cmd_valider = tk.Button(
            barre, text="✅ Valider", command=lambda: self._valider_commande(True),
            bg=CLR_GREEN, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_cmd_valider.pack(side="left", padx=2)
        self.btn_cmd_ajuste = tk.Button(
            barre, text="✅ Valider ajusté (stock réel)", command=lambda: self._valider_commande(False),
            bg=CLR_ORANGE, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_cmd_ajuste.pack(side="left", padx=2)
        self.btn_cmd_refuser = tk.Button(
            barre, text="❌ Refuser", command=self._refuser_commande,
            bg=CLR_RED, fg="white", relief="flat", padx=10, pady=5, cursor="hand2")
        self.btn_cmd_refuser.pack(side="left", padx=2)
        self.cmd_tree = self._arbre(
            t, ["N°", "Date", "Type", "Tiers", "Statut", "Montant"],
            [150, 100, 80, 220, 100, 120])
        self.cmd_tree.tag_configure("attente", background="#fff4d6", foreground="#000000")
        self.cmd_total = self._total_lbl(t)

    # — Tournée —
    def _build_onglet_tournee(self):
        t = self._tab("📍 Tournée")
        self.pt_tree = self._arbre(
            t, ["Date", "Code client", "Client", "Latitude", "Longitude", "Observations"],
            [140, 100, 200, 100, 100, 260])

    # ───────────── période ─────────────

    def _set_periode(self, debut, fin):
        self.debut_entry.delete(0, tk.END)
        self.fin_entry.delete(0, tk.END)
        if debut:
            self.debut_entry.insert(0, debut)
        if fin:
            self.fin_entry.insert(0, fin)
        self._appliquer_periode()

    def _periode_jour(self):
        j = date.today().isoformat()
        self._set_periode(j, j)

    def _periode_mois(self):
        j = date.today()
        self._set_periode(j.replace(day=1).isoformat(), j.isoformat())

    def _periode_tout(self):
        self._set_periode("", "")

    def _appliquer_periode(self):
        d, f = self.debut_entry.get().strip(), self.fin_entry.get().strip()
        for valeur in (d, f):
            if valeur and not valider_date(valeur):
                messagebox.showwarning("Période", "Format de date attendu : AAAA-MM-JJ.")
                return
        if d and f and d > f:
            messagebox.showwarning("Période", "La date de début doit précéder la date de fin.")
            return
        self.date_debut, self.date_fin = d or None, f or None
        self.refresh()

    # ───────────── données ─────────────

    def _afficher_vide(self):
        self.titre_lbl.config(text="Sélectionnez un vendeur dans la liste")
        for tree in (self.chg_tree, self.chg_lignes, self.camion_tree, self.ventes_tree,
                     self.vers_tree, self.remise_tree, self.prospects_tree, self.cmd_tree,
                     self.pt_tree):
            tree.delete(*tree.get_children())
        for v in self.cartes.values():
            v.config(text="—")
        for t in (self.camion_total, self.ventes_total, self.vers_total,
                  self.remise_total, self.remise_solde, self.prospects_total, self.cmd_total):
            t.config(text="")
        for b in (self.btn_charger, self.btn_decharger, self.btn_cmd_valider,
                  self.btn_cmd_ajuste, self.btn_cmd_refuser,
                  self.btn_modifier_chargement, self.btn_annuler_chargement,
                  self.btn_supprimer_chargement, self.btn_remise, self.btn_annuler_remise):
            b.config(state="disabled")

    def set_vendeur(self, vendeur_id):
        self.vendeur_id = vendeur_id
        self.refresh()

    def refresh(self):
        if not self.vendeur_id:
            self._afficher_vide()
            return
        d, f = self.date_debut, self.date_fin
        conn = get_conn()
        try:
            self.vendeur = dossier.get_vendeur(conn, self.vendeur_id)
            if self.vendeur is None:
                self.vendeur_id = None
                self._afficher_vide()
                return
            sit = dossier.situation_vendeur(conn, self.vendeur_id, d, f)
            chargements = dossier.chargements_vendeur(conn, self.vendeur_id, d, f)
            camion = dossier.stock_camion(conn, self.vendeur_id)
            ventes = dossier.ventes_vendeur(conn, self.vendeur_id, d, f)
            versements = dossier.versements_vendeur(conn, self.vendeur_id, d, f)
            caisse = dossier.caisse_vendeur(conn, self.vendeur_id, d, f)
            remises = dossier.versements_admin_vendeur(conn, self.vendeur_id, d, f)
            sit["verse_admin"] = caisse["periode_verse_admin"]
            sit["reste_a_verser"] = caisse["reste_a_verser"]
            # « Crédit » = ce que les clients doivent ENCORE (soldes réels, cumul) :
            # il monte à chaque vente à crédit et baisse à chaque versement.
            sit["credit_accorde"] = caisse["creances_clients"]
            prospects = dossier.prospects_vendeur(conn, self.vendeur_id)
            commandes = dossier.commandes_vendeur(conn, self.vendeur_id, d, f)
            pointages = dossier.pointages_vendeur(conn, self.vendeur_id, d, f)
        except sqlite3.Error as exc:
            messagebox.showerror("Erreur", f"Chargement du dossier vendeur impossible :\n{exc}")
            return
        finally:
            conn.close()

        v = self.vendeur
        statut = "" if v["actif"] else "  (accès désactivé)"
        periode = ""
        if d or f:
            periode = f"  —  du {d or '…'} au {f or '…'}"
        self.titre_lbl.config(text=f"👔 {v['code']} — {v['nom']}{statut}{periode}")

        self._remplir_situation(sit)
        self._remplir_chargements(chargements)
        self._maj_actions_chargement()
        self._remplir_camion(camion)
        self._remplir_ventes(ventes)
        self._remplir_versements(versements)
        self._remplir_remises(remises, caisse)
        self._remplir_prospects(prospects)
        self._remplir_commandes(commandes)
        self._remplir_pointages(pointages)
        self._appliquer_droits()
        self._situation = sit

    def _remplir_situation(self, s):
        fm = {"ca", "encaisse_total", "encaisse_especes", "credit_accorde", "camion_valeur",
              "verse_admin", "reste_a_verser"}
        for cle, widget in self.cartes.items():
            widget.config(text=fmt_da(s[cle]) if cle in fm else fmt_qte(s[cle]))

    def _remplir_chargements(self, rows):
        self.chg_tree.delete(*self.chg_tree.get_children())
        self.chg_lignes.delete(*self.chg_lignes.get_children())
        for r in rows:
            self.chg_tree.insert("", "end", iid=str(r["id"]), values=(
                r["numero"], r["date_chargement"], r["statut"], fmt_qte(r["total_colis"]),
                fmt_qte(r["total_pieces"]), r["observations"] or ""))

    def _remplir_camion(self, rows):
        self.camion_tree.delete(*self.camion_tree.get_children())
        total_colis = total_val = 0.0
        for r in rows:
            total_colis += float(r["quantite_colis"] or 0)
            total_val += float(r["valeur"] or 0)
            self.camion_tree.insert("", "end", values=(
                r["code"], r["designation"], fmt_qte(r["quantite_colis"]),
                fmt_qte(r["quantite_pieces"]), fmt_da(r["prix_vente"]), fmt_da(r["valeur"]),
                _date_courte(r["date_maj"])))
        self.camion_total.config(
            text=f"{len(rows)} produit(s) — {fmt_qte(total_colis)} colis — valeur : {fmt_da(total_val)}")

    def _remplir_ventes(self, rows):
        self.ventes_tree.delete(*self.ventes_tree.get_children())
        total = verse = reste = 0.0
        for r in rows:
            annule = r["statut"] == dossier.STATUT_ANNULE
            if not annule:
                total += float(r["total"] or 0)
                verse += float(r["montant_verse"] or 0)
                reste += float(r["reste_payer"] or 0)
            self.ventes_tree.insert("", "end", values=(
                r["numero"], r["date_bon"], r["client"] or "—", fmt_da(r["total"]),
                fmt_da(r["montant_verse"]), fmt_da(r["reste_payer"]), r["statut"]))
        self.ventes_total.config(
            text=f"Hors annulés — Total : {fmt_da(total)}   Versé à la vente : {fmt_da(verse)}   "
                 f"Crédit : {fmt_da(reste)}")

    def _remplir_versements(self, rows):
        self.vers_tree.delete(*self.vers_tree.get_children())
        total = especes = 0.0
        for r in rows:
            total += float(r["montant"] or 0)
            if r["mode"] == "Espèces":
                especes += float(r["montant"] or 0)
            self.vers_tree.insert("", "end", values=(
                r["numero"], r["date_vers"], r["type"], r["tiers"] or "—",
                fmt_da(r["montant"]), r["mode"] or "", r["reference"] or ""))
        self.vers_total.config(
            text=f"{len(rows)} versement(s) — Total : {fmt_da(total)}   dont Espèces : {fmt_da(especes)}")

    def _remplir_remises(self, rows, caisse):
        self.remise_tree.delete(*self.remise_tree.get_children())
        total = 0.0
        for r in rows:
            annule = r["statut"] == "Annulé"
            if not annule:
                total += float(r["montant"] or 0)
            self.remise_tree.insert("", "end", iid=str(r["id"]),
                                    tags=("annule",) if annule else (), values=(
                r["numero"], r["date_vers"], fmt_da(r["montant"]), r["mode"] or "",
                r["reference"] or "", r["observations"] or "", r["statut"], r["cree_par"] or ""))
        self.remise_tree.tag_configure("annule", foreground="#9ca3af")
        self.remise_solde.config(
            text=f"Reste à verser (cumul) : {fmt_da(caisse['reste_a_verser'])}   —   "
                 f"espèces encaissées : {fmt_da(caisse['cumul_encaisse_especes'])}   —   "
                 f"déjà versé : {fmt_da(caisse['cumul_verse_admin'])}")
        self.remise_total.config(
            text=f"{len(rows)} ligne(s) sur la période — Versé (hors annulés) : {fmt_da(total)}")
        self._reste_a_verser = caisse["reste_a_verser"]

    def _remplir_prospects(self, rows):
        self.prospects_tree.delete(*self.prospects_tree.get_children())
        solde = 0.0
        convertis = 0
        for r in rows:
            solde += float(r["solde"] or 0)
            convertis += r["statut"] == "Converti"
            self.prospects_tree.insert("", "end", iid=str(r["id"]), values=(
                r["code"], r["nom"], r["tel"] or "", r["adresse"] or "", r["wilaya"] or "",
                r["statut"], fmt_da(r["solde"]), _date_courte(r["date_creation"])))
        self.prospects_total.config(
            text=f"{len(rows)} prospect(s) (toutes périodes) — {convertis} converti(s) — "
                 f"soldes dus : {fmt_da(solde)}")

    def _remplir_commandes(self, rows):
        self.cmd_tree.delete(*self.cmd_tree.get_children())
        total = 0.0
        for r in rows:
            total += float(r["montant"] or 0)
            self.cmd_tree.insert(
                "", "end", iid=f"{r['type']}:{r['id']}",
                tags=("attente",) if r["statut"] == cmd_service.STATUT_ATTENTE else (),
                values=(r["numero"], r["date_commande"], r["type"], r["tiers"] or "—",
                        r["statut"], fmt_da(r["montant"])))
        attente = sum(1 for r in rows if r["statut"] == cmd_service.STATUT_ATTENTE)
        self.cmd_total.config(
            text=f"{len(rows)} commande(s) dont {attente} en attente (en jaune) — "
                 f"Total : {fmt_da(total)}")

    def _remplir_pointages(self, rows):
        self.pt_tree.delete(*self.pt_tree.get_children())
        for r in rows:
            self.pt_tree.insert("", "end", values=(
                _date_courte(r["date_pointage"]), r["code_client"] or "", r["nom_client"] or "",
                "" if r["latitude"] is None else f"{r['latitude']:.5f}",
                "" if r["longitude"] is None else f"{r['longitude']:.5f}",
                r["observations"] or ""))

    def _appliquer_droits(self):
        autorise = rbac.peut(rbac.role_courant(), "gerer_chargements")
        actif = autorise and bool(self.vendeur and self.vendeur["actif"])
        self.btn_charger.config(state="normal" if actif else "disabled")
        self.btn_decharger.config(state="normal" if actif else "disabled")
        self._maj_actions_chargement()
        peut_remise = rbac.peut(rbac.role_courant(), "encaisser_versement_vendeur")
        self.btn_remise.config(
            state="normal" if peut_remise and self.vendeur and self.vendeur["actif"] else "disabled")
        self.btn_annuler_remise.config(state="normal" if peut_remise else "disabled")
        peut_valider = rbac.peut(rbac.role_courant(), "valider_commandes")
        for b in (self.btn_cmd_valider, self.btn_cmd_ajuste, self.btn_cmd_refuser):
            b.config(state="normal" if peut_valider else "disabled")

    # ───────────── actions ─────────────

    def _nouvelle_remise(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "encaisser_versement_vendeur"):
            return
        dlg = VersementVendeurDialog(self, self.vendeur, getattr(self, "_reste_a_verser", 0))
        self.wait_window(dlg)
        if dlg.resultat:
            self.refresh()
            messagebox.showinfo(
                "Versement enregistré",
                f"{dlg.resultat['numero']} : {fmt_da(dlg.resultat['montant'])}\n"
                f"Reste à verser : {fmt_da(dlg.resultat['reste_a_verser'])}", parent=self)

    def _annuler_remise(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "encaisser_versement_vendeur"):
            return
        sel = self.remise_tree.selection()
        if not sel:
            messagebox.showwarning("Versement", "Sélectionnez un versement à annuler.", parent=self)
            return
        numero = self.remise_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno(
            "Annuler le versement",
            f"Annuler le versement {numero} ?\nLe montant sera de nouveau à verser par le vendeur "
            "et la ligne restera dans l'historique.", parent=self):
            return
        session = rbac.get_utilisateur_connecte()
        conn = get_conn()
        try:
            dossier.annuler_versement_admin(
                conn, int(sel[0]), session["nom_complet"] if session else None)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Annulation impossible", str(exc), parent=self)
            return
        finally:
            conn.close()
        self.refresh()

    def _maj_actions_chargement(self):
        autorise = (
            rbac.peut(rbac.role_courant(), "gerer_chargements")
            and bool(self.vendeur and self.vendeur["actif"])
        )
        selection = self.chg_tree.selection() if hasattr(self, "chg_tree") else ()
        statut = self.chg_tree.item(selection[0], "values")[2] if selection else None
        etat = "normal" if autorise and statut == "Validé" else "disabled"
        self.btn_modifier_chargement.config(state=etat)
        self.btn_annuler_chargement.config(state=etat)
        self.btn_supprimer_chargement.config(
            state="normal" if autorise and statut in ("Validé", "Annulé") else "disabled"
        )

    def _on_chargement_select(self, event=None):
        self.chg_lignes.delete(*self.chg_lignes.get_children())
        self._maj_actions_chargement()
        sel = self.chg_tree.selection()
        if not sel:
            return
        conn = get_conn()
        try:
            for r in dossier.lignes_chargement(conn, int(sel[0])):
                self.chg_lignes.insert("", "end", values=(
                    r["code"], r["designation"], fmt_qte(r["quantite_colis"]),
                    r["unite"] or "", fmt_qte(r["quantite_pieces"])))
        finally:
            conn.close()

    def _nouveau_chargement(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "gerer_chargements"):
            return
        d = NouveauChargementDialog(self, self.vendeur)
        self.wait_window(d)
        self.refresh()

    def _modifier_chargement(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "gerer_chargements"):
            return
        sel = self.chg_tree.selection()
        if not sel:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon validé à modifier.")
            return
        dialog = NouveauChargementDialog(self, self.vendeur, bon_id=int(sel[0]))
        self.wait_window(dialog)
        self.refresh()

    def _annuler_chargement(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "gerer_chargements"):
            return
        sel = self.chg_tree.selection()
        if not sel:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon validé à annuler.")
            return
        bon_id = int(sel[0])
        numero = self.chg_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno(
            "Annuler le bon de chargement",
            f"Annuler le bon {numero} ?\n"
            "Les quantités seront retournées au dépôt et l'opération restera dans l'historique.",
            parent=self,
        ):
            return
        conn = get_conn()
        try:
            annuler_bon_chargement(conn, bon_id)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Annulation impossible", str(exc), parent=self)
            return
        finally:
            conn.close()
        self.refresh()
        messagebox.showinfo("Bon annulé", f"Le bon {numero} a été annulé.", parent=self)

    def _supprimer_chargement(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "gerer_chargements"):
            return
        sel = self.chg_tree.selection()
        if not sel:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon à supprimer.", parent=self)
            return
        bon_id = int(sel[0])
        valeurs = self.chg_tree.item(sel[0], "values")
        numero, statut = valeurs[0], valeurs[2]
        if statut not in ("Validé", "Annulé"):
            messagebox.showwarning(
                "Suppression impossible",
                "Le statut du bon ne permet pas sa suppression.",
                parent=self,
            )
            return
        confirmation = messagebox.askyesno(
            "Suppression définitive",
            f"Supprimer définitivement le bon {numero}, ses lignes et ses mouvements de stock ?\n"
            + (
                "Les quantités seront réintégrées au dépôt si elles sont encore dans le camion."
                if statut == "Validé"
                else "Le bon est déjà annulé; les stocks ne seront pas modifiés."
            ),
            parent=self,
        )
        if not confirmation:
            return
        conn = get_conn()
        try:
            supprimer_bon_chargement(conn, bon_id)
        except (ValueError, RuntimeError, sqlite3.Error) as exc:
            messagebox.showerror("Suppression impossible", str(exc), parent=self)
            return
        finally:
            conn.close()
        self.refresh()
        messagebox.showinfo(
            "Bon supprimé",
            f"Le bon {numero} et son historique de mouvements ont été supprimés.",
            parent=self,
        )

    def _decharger(self):
        if not self.vendeur or not rbac.peut(rbac.role_courant(), "gerer_chargements"):
            return
        if not messagebox.askyesno(
                "Déchargement du soir",
                f"Réintégrer au dépôt tout le stock restant dans le camion de {self.vendeur['nom']} ?"):
            return
        conn = get_conn()
        try:
            res = decharger_camion(conn, self.vendeur_id)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Déchargement impossible", str(exc))
            return
        finally:
            conn.close()
        self.refresh()
        if res["produits"] == 0:
            messagebox.showinfo("Déchargement", "Le camion est déjà vide.")
        else:
            messagebox.showinfo(
                "Déchargement terminé",
                f"{fmt_qte(res['total_colis'])} colis ({fmt_qte(res['total_pieces'])} pièces) "
                "réintégrés au dépôt.")

    def _imprimer_bon(self):
        sel = self.chg_tree.selection()
        if not sel:
            messagebox.showwarning("Bon de chargement", "Sélectionnez un bon dans la liste.")
            return
        bon_id = int(sel[0])
        conn = get_conn()
        try:
            bon = conn.execute(
                """SELECT numero, date_chargement, total_colis, total_pieces, observations
                   FROM bons_chargement WHERE id=?""", (bon_id,)).fetchone()
            lignes = dossier.lignes_chargement(conn, bon_id)
        finally:
            conn.close()
        if bon is None:
            messagebox.showerror("Bon de chargement", "Ce bon n'existe plus.")
            return
        data = [[r["code"], r["designation"], fmt_qte(r["quantite_colis"]),
                 r["unite"] or "", fmt_qte(r["quantite_pieces"])] for r in lignes]
        footer = (
            f"Bon : {bon['numero']}\nDate : {bon['date_chargement']}\n"
            f"Vendeur : {self.vendeur['code']} — {self.vendeur['nom']}\n"
            f"Total : {fmt_qte(bon['total_colis'])} colis / {fmt_qte(bon['total_pieces'])} pièces\n"
            f"Observations : {bon['observations'] or '—'}\n"
            f"Imprimé le : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print_preview(data, f"BON DE CHARGEMENT — {bon['numero']}",
                      ["Code", "Produit", "Colis", "Unité", "Pièces"], footer_text=footer)

    def _imprimer_situation(self):
        if not self.vendeur:
            messagebox.showwarning("Situation", "Sélectionnez un vendeur.")
            return
        s = getattr(self, "_situation", None)
        if not s:
            return
        data = [
            ["Chiffre d'affaires", fmt_da(s["ca"])],
            ["Encaissé (versements clients + prospects)", fmt_da(s["encaisse_total"])],
            ["dont Espèces à remettre", fmt_da(s["encaisse_especes"])],
            ["Crédit en cours (reste dû)", fmt_da(s["credit_accorde"])],
            ["Nombre de ventes", fmt_qte(s["nb_ventes"])],
            ["Nombre de versements", fmt_qte(s["nb_versements"])],
            ["Bons de chargement / colis chargés",
             f"{fmt_qte(s['nb_chargements'])} / {fmt_qte(s['colis_charges'])}"],
            ["Camion actuel : colis / valeur",
             f"{fmt_qte(s['camion_colis'])} / {fmt_da(s['camion_valeur'])}"],
            ["Prospects créés / convertis",
             f"{fmt_qte(s['nb_prospects'])} / {fmt_qte(s['prospects_convertis'])}"],
            ["Commandes en attente", fmt_qte(s["commandes_en_attente"])],
        ]
        periode = f"du {self.date_debut or '…'} au {self.date_fin or '…'}"
        print_preview(
            data, f"SITUATION VENDEUR — {self.vendeur['code']} {self.vendeur['nom']}",
            ["Rubrique", "Valeur"],
            footer_text=f"Période : {periode}\n"
                        f"Imprimé le : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    def _convertir_prospect(self):
        sel = self.prospects_tree.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez un prospect dans la liste.")
            return
        nom = self.prospects_tree.item(sel[0], "values")[1]
        if not messagebox.askyesno(
                "Confirmation",
                f"Convertir le prospect « {nom} » en client officiel ?\n\n"
                "Un nouveau compte client (CLT-xxxx) sera créé."):
            return
        conn = get_conn()
        try:
            res = dossier.convertir_prospect_en_client(conn, int(sel[0]))
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Conversion impossible", str(exc))
            return
        finally:
            conn.close()
        messagebox.showinfo("Succès", f"Prospect converti.\nNouveau code client : {res['code']}")
        self.refresh()

    # — Commandes : détail / validation / refus —

    def _commande_selectionnee(self):
        sel = self.cmd_tree.selection()
        if not sel:
            messagebox.showwarning("Commande", "Sélectionnez une commande dans la liste.")
            return None
        type_, cmd_id = sel[0].split(":")
        return type_, int(cmd_id)

    def _detail_commande(self):
        choix = self._commande_selectionnee()
        if not choix:
            return
        type_, cmd_id = choix
        conn = get_conn()
        try:
            cmd = cmd_service.get_commande(conn, type_, cmd_id)
            lignes = cmd_service.lignes_commande(conn, type_, cmd_id)
        finally:
            conn.close()
        if cmd is None:
            messagebox.showerror("Commande", "Cette commande n'existe plus.")
            return
        win = tk.Toplevel(self)
        win.title(f"Commande {cmd['numero']}")
        win.configure(bg=CLR_BG)
        center_window(win, 820, 420)
        lbl(win, f"{cmd['numero']} — {type_} — {cmd['statut']} — {cmd['date_commande']}",
            11, True, CLR_ACCENT).pack(anchor="w", padx=12, pady=(10, 2))
        if cmd.get("observations"):
            lbl(win, cmd["observations"], 9, color=CLR_MUTED).pack(anchor="w", padx=12)
        tf, tree = make_tree(
            win, ["Produit", "Colis", "Pièces", "Prix/pièce", "Total", "Stock dépôt (pièces)"],
            [260, 70, 80, 100, 110, 140])
        tf.pack(fill="both", expand=True, padx=12, pady=8)
        for l in lignes:
            pieces = float(l["quantite"] or 0) * l["facteur"]
            manque = pieces > float(l["stock_pieces"] or 0)
            tree.insert("", "end", tags=("manque",) if manque else (), values=(
                l["designation"], fmt_qte(l["quantite"]), fmt_qte(pieces),
                fmt_da(l["prix_unitaire"]), fmt_da(pieces * float(l["prix_unitaire"] or 0)),
                fmt_qte(l["stock_pieces"])))
        tree.tag_configure("manque", background="#fde2e2", foreground="#000000")
        lbl(win, "Lignes en rouge : stock du dépôt insuffisant pour la quantité demandée.",
            8, color=CLR_MUTED).pack(anchor="w", padx=12, pady=(0, 8))

    def _valider_commande(self, complete):
        if not rbac.peut(rbac.role_courant(), "valider_commandes"):
            return
        choix = self._commande_selectionnee()
        if not choix:
            return
        type_, cmd_id = choix
        mode = "totalement" if complete else "avec ajustement au stock réel"
        num = self.cmd_tree.item(f"{type_}:{cmd_id}", "values")[0]
        if not messagebox.askyesno(
                "Valider la commande",
                f"Valider {mode} la commande {num} ?\n\n"
                "Un bon de vente sera créé, le stock du dépôt sera déduit et "
                "le solde du client sera mis à jour."):
            return
        conn = get_conn()
        try:
            try:
                res = cmd_service.valider_commande(conn, type_, cmd_id, complete=complete)
            except cmd_service.ConversionProspectRequise as exc:
                if not messagebox.askyesno(
                        "Prospect non converti",
                        f"{exc}\n\nLe convertir automatiquement en client officiel "
                        "pour générer le bon de vente ?"):
                    return
                res = cmd_service.valider_commande(
                    conn, type_, cmd_id, complete=complete, convertir_prospect=True)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Validation impossible", str(exc))
            return
        finally:
            conn.close()
        note = "\n(quantités ajustées au stock disponible)" if res["ajuste"] else ""
        messagebox.showinfo(
            "Commande validée",
            f"Bon de vente {res['numero']} créé — total {fmt_da(res['total'])}.{note}")
        self.refresh()

    def _refuser_commande(self):
        if not rbac.peut(rbac.role_courant(), "valider_commandes"):
            return
        choix = self._commande_selectionnee()
        if not choix:
            return
        type_, cmd_id = choix
        motif = simpledialog.askstring(
            "Refuser la commande", "Motif du refus (visible dans les observations) :", parent=self)
        if motif is None:
            return
        conn = get_conn()
        try:
            cmd_service.rejeter_commande(conn, type_, cmd_id, motif)
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Refus impossible", str(exc))
            return
        finally:
            conn.close()
        messagebox.showinfo("Commande refusée", "La commande a été marquée « Rejetée ».")
        self.refresh()