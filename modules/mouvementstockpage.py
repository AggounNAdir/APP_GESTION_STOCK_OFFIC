"""
Page « Mouvements de Stock » : journal détaillé de toutes les entrées et sorties.

Chaque vente, achat, retour, annulation, ajustement... laisse une ligne
(voir api/stock_journal.py). Cette page permet de filtrer, consulter le détail,
exporter, corriger le stock (ajustement) et contrôler la cohérence du journal.
"""
from datetime import date, timedelta

from api import stock_journal as sj
from modules.core import *
from modules.dateentry import DateEntry
from modules.ajustementstockdialog import AjustementStockDialog
from modules.coherencestockdialog import CoherenceStockDialog
from modules.mouvementdetaildialog import MouvementDetailDialog

TAILLE_PAGE = 200            # lignes affichées par page
MAX_LIGNES_IMPRESSION = 5000  # au-delà, l'impression est tronquée (le CSV ne l'est pas)

TOUS_PRODUITS = "Tous les produits"
TOUS_TYPES = "Tous les types"
SENS = {
    "Entrées et sorties": None,
    "Entrées seulement": "entree",
    "Sorties seulement": "sortie",
}


class MouvementStockPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._offset = 0
        self._total = 0
        self._lignes = {}             # iid (id du mouvement) -> dict
        self._after_id = None
        self._produit_par_libelle = {}
        self._libelles_produits = []
        self._type_par_libelle = {sj.libelle_type(c): c for c in sj.TYPES_MOUVEMENT}
        self._build()
        self.refresh_produits()
        self.refresh()

    # ══════════════════════════ CONSTRUCTION ══════════════════════════
    def _build(self):
        # ── En-tête ──
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20, 8))
        lbl(hdr, "📋  Mouvements de Stock", 16, True).pack(side="left")
        tk.Button(hdr, text="➕ Ajustement de stock", command=self.ajuster,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=14, pady=7, cursor="hand2").pack(side="right")
        tk.Button(hdr, text="🩺 Contrôle de cohérence", command=self.controler,
                  bg=CLR_PURPLE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=14, pady=7, cursor="hand2").pack(side="right", padx=8)

        # ── Filtres ligne 1 : période + produit ──
        f1 = tk.Frame(self, bg=CLR_BG)
        f1.pack(fill="x", padx=20, pady=3)
        lbl(f1, "Période du", color=CLR_MUTED).pack(side="left")
        self.date_debut_var = tk.StringVar(
            value=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.date_fin_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        DateEntry(f1, self.date_debut_var, width=11).pack(side="left", padx=(6, 8))
        lbl(f1, "au", color=CLR_MUTED).pack(side="left")
        DateEntry(f1, self.date_fin_var, width=11).pack(side="left", padx=(6, 8))
        for texte, jours in (("Aujourd'hui", 0), ("7 j", 7), ("30 j", 30), ("Tout", None)):
            tk.Button(f1, text=texte, command=lambda j=jours: self._periode_rapide(j),
                      bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 8),
                      padx=7, pady=3, cursor="hand2").pack(side="left", padx=2)

        lbl(f1, "Produit:", color=CLR_MUTED).pack(side="left", padx=(18, 4))
        self.produit_var = tk.StringVar(value=TOUS_PRODUITS)
        self.produit_cb = combo(f1, [TOUS_PRODUITS], width=38, textvariable=self.produit_var)
        self.produit_cb.pack(side="left")
        self.produit_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.produit_cb.bind("<KeyRelease>", self._filtrer_liste_produits)
        self.produit_cb.bind("<Return>", self._valider_saisie_produit)

        # ── Filtres ligne 2 : type, sens, recherche ──
        f2 = tk.Frame(self, bg=CLR_BG)
        f2.pack(fill="x", padx=20, pady=3)
        lbl(f2, "Type:", color=CLR_MUTED).pack(side="left")
        self.type_var = tk.StringVar(value=TOUS_TYPES)
        cb_type = combo(f2, [TOUS_TYPES] + list(self._type_par_libelle), width=28,
                        textvariable=self.type_var, state="readonly")
        cb_type.pack(side="left", padx=(6, 12))
        cb_type.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        lbl(f2, "Sens:", color=CLR_MUTED).pack(side="left")
        self.sens_var = tk.StringVar(value="Entrées et sorties")
        cb_sens = combo(f2, list(SENS), width=18, textvariable=self.sens_var, state="readonly")
        cb_sens.pack(side="left", padx=(6, 12))
        cb_sens.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        lbl(f2, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        entry(f2, width=26, textvariable=self.search_var).pack(side="left", padx=(6, 8))
        lbl(f2, "(n° document, client, fournisseur, motif)", 8, color=CLR_MUTED).pack(side="left")
        tk.Button(f2, text="↺ Réinitialiser", command=self.reinitialiser,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 8),
                  padx=8, pady=3, cursor="hand2").pack(side="right")

        # Rafraîchissement automatique (avec délai) quand les dates ou la recherche changent
        for var in (self.date_debut_var, self.date_fin_var, self.search_var):
            var.trace_add("write", lambda *a: self._planifier_refresh())

        # ── Indicateurs ──
        kf = tk.Frame(self, bg=CLR_BG)
        kf.pack(fill="x", padx=20, pady=(10, 4))
        self.kpi_nb, self.kpi_nb_sub = self._kpi(kf, "MOUVEMENTS", CLR_ACCENT)
        self.kpi_ent, self.kpi_ent_sub = self._kpi(kf, "ENTRÉES (unités de base)", CLR_GREEN)
        self.kpi_sor, self.kpi_sor_sub = self._kpi(kf, "SORTIES (unités de base)", CLR_RED)
        self.kpi_net, self.kpi_net_sub = self._kpi(kf, "SOLDE NET", CLR_ORANGE)

        self.info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.info_var, bg=CLR_BG, fg=CLR_TEXT, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(fill="x", padx=22, pady=(2, 0))

        # ── Tableau ──
        cols = ["Date / Heure", "Type", "Code", "Désignation", "Document", "Client / Fournisseur",
                "Entrée", "Sortie", "Stock avant", "Stock après", "Coût unit.", "Valeur",
                "Utilisateur", "Motif"]
        widths = [130, 150, 80, 190, 150, 150, 70, 70, 80, 80, 80, 95, 90, 220]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=8)
        self.tree.tag_configure("entree", foreground=CLR_GREEN)
        self.tree.tag_configure("sortie", foreground=CLR_RED)
        self.tree.tag_configure("ajust", foreground=CLR_ORANGE)
        self.tree.tag_configure("initial", foreground=CLR_ACCENT)
        self.tree.bind("<Double-1>", lambda e: self.voir_detail())
        self.tree.bind("<Return>", lambda e: self.voir_detail())

        # ── Pagination ──
        pf = tk.Frame(self, bg=CLR_BG)
        pf.pack(fill="x", padx=20)
        self.btn_prec = tk.Button(pf, text="◀ Précédent", command=lambda: self._page(-1),
                                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 8),
                                  padx=8, pady=3, cursor="hand2")
        self.btn_prec.pack(side="left")
        self.page_var = tk.StringVar(value="")
        tk.Label(pf, textvariable=self.page_var, bg=CLR_BG, fg=CLR_MUTED,
                 font=("Segoe UI", 9)).pack(side="left", padx=12)
        self.btn_suiv = tk.Button(pf, text="Suivant ▶", command=lambda: self._page(1),
                                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 8),
                                  padx=8, pady=3, cursor="hand2")
        self.btn_suiv.pack(side="left")

        # ── Actions ──
        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(8, 15))
        tk.Button(bf, text="👁 Détail", command=self.voir_detail,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🔄 Rafraîchir", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)
        tk.Button(bf, text="📄 Export CSV", command=self.export_csv,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bf, text="🖨 Imprimer", command=self.imprimer,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)

    def _kpi(self, parent, titre, couleur):
        carte = tk.Frame(parent, bg=CLR_CARD, padx=14, pady=8)
        carte.pack(side="left", padx=(0, 10))
        tk.Label(carte, text=titre, bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        valeur = tk.StringVar(value="—")
        tk.Label(carte, textvariable=valeur, bg=CLR_CARD, fg=couleur,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        detail = tk.StringVar(value="")
        tk.Label(carte, textvariable=detail, bg=CLR_CARD, fg=CLR_MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w")
        return valeur, detail

    # ══════════════════════════ FILTRES ══════════════════════════
    def refresh_produits(self):
        """Recharge la liste des produits du filtre (appelé aussi par l'événement
        <<ProduitsModifies>> de l'application). Conserve la sélection."""
        conn = get_conn()
        try:
            rows = conn.execute(
                """SELECT id, code, designation FROM produits
                   WHERE code <> 'SOLDE_INITIAL'
                     AND (actif = 1 OR EXISTS
                          (SELECT 1 FROM mouvements_stock m WHERE m.produit_id = produits.id))
                   ORDER BY designation"""
            ).fetchall()
        finally:
            conn.close()
        self._produit_par_libelle = {f"{r['code']} — {r['designation']}": r["id"] for r in rows}
        self._libelles_produits = [TOUS_PRODUITS] + list(self._produit_par_libelle)
        self.produit_cb["values"] = self._libelles_produits
        if self.produit_var.get() not in self._libelles_produits:
            self.produit_var.set(TOUS_PRODUITS)

    def _filtrer_liste_produits(self, event=None):
        if event is not None and event.keysym in ("Return", "Up", "Down", "Escape", "Tab"):
            return
        texte = self.produit_var.get().strip().lower()
        self.produit_cb["values"] = (
            [l for l in self._libelles_produits if texte in l.lower()]
            if texte else self._libelles_produits)

    def _valider_saisie_produit(self, event=None):
        """Entrée dans le champ produit : sélectionne le premier produit correspondant."""
        if self.produit_var.get() not in self._libelles_produits:
            valeurs = self.produit_cb["values"]
            if valeurs and len(valeurs) < len(self._libelles_produits):
                self.produit_var.set(valeurs[0])
            else:
                self.produit_var.set(TOUS_PRODUITS)
        self.refresh()

    def _periode_rapide(self, jours):
        if jours is None:                        # toute la période
            self.date_debut_var.set("")
            self.date_fin_var.set("")
        else:
            self.date_debut_var.set((date.today() - timedelta(days=jours)).strftime("%Y-%m-%d"))
            self.date_fin_var.set(date.today().strftime("%Y-%m-%d"))

    def reinitialiser(self):
        self.produit_var.set(TOUS_PRODUITS)
        self.type_var.set(TOUS_TYPES)
        self.sens_var.set("Entrées et sorties")
        self.search_var.set("")
        self._periode_rapide(30)
        self.refresh()

    def filtrer_produit(self, produit_id):
        """Affiche tout l'historique d'un produit (appelé depuis la page Produits)."""
        self.refresh_produits()
        for lib, pid in self._produit_par_libelle.items():
            if pid == int(produit_id):
                self.produit_var.set(lib)
                break
        self.type_var.set(TOUS_TYPES)
        self.sens_var.set("Entrées et sorties")
        self.search_var.set("")
        self._periode_rapide(None)
        self.refresh()

    def _planifier_refresh(self):
        """Regroupe les changements rapides (frappe, sélection de dates) en un seul chargement."""
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(350, self.refresh)

    def _filtres(self):
        debut = self.date_debut_var.get().strip()
        fin = self.date_fin_var.get().strip()
        code_type = self._type_par_libelle.get(self.type_var.get())
        return {
            "date_debut": debut if debut and valider_date(debut) else None,
            "date_fin": fin if fin and valider_date(fin) else None,
            "produit_id": self._produit_par_libelle.get(self.produit_var.get()),
            "types": [code_type] if code_type else None,
            "sens": SENS.get(self.sens_var.get()),
            "texte": self.search_var.get().strip() or None,
        }

    # ══════════════════════════ AFFICHAGE ══════════════════════════
    def refresh(self, conserver_page=False):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if not conserver_page:
            self._offset = 0
        filtres = self._filtres()
        conn = get_conn()
        try:
            totaux = sj.totaliser_mouvements(conn, **filtres)
            lignes = sj.rechercher_mouvements(conn, **filtres, limite=TAILLE_PAGE,
                                              offset=self._offset)
            info = self._info_produit(conn, filtres["produit_id"])
        finally:
            conn.close()

        self._total = totaux["nombre"]
        self._lignes = {str(m["id"]): m for m in lignes}
        self.tree.delete(*self.tree.get_children())
        for m in lignes:
            self.tree.insert("", "end", iid=str(m["id"]), tags=(self._tag(m),),
                             values=self._valeurs_ligne(m))
        self._maj_indicateurs(totaux, filtres["produit_id"])
        self.info_var.set(info)
        self._maj_pagination()

    @staticmethod
    def _tag(m):
        if m["type_mouvement"] in ("AJUSTEMENT", "REGULARISATION"):
            return "ajust"
        if m["type_mouvement"] in ("STOCK_INITIAL", "REPRISE"):
            return "initial"
        return "entree" if m["quantite"] > 0 else "sortie"

    @staticmethod
    def _valeurs_ligne(m):
        q = float(m["quantite"])
        doc = ""
        if m["document_type"]:
            doc = sj.libelle_document(m["document_type"])
            if m["document_numero"]:
                doc += f" {m['document_numero']}"
        return (
            m["date_mouvement"],
            sj.libelle_type(m["type_mouvement"]),
            m["produit_code"],
            m["produit_designation"],
            doc or "—",
            m["tiers_nom"] or "",
            f"{q:.2f}" if q > 0 else "",
            f"{-q:.2f}" if q < 0 else "",
            f"{float(m['stock_avant']):.2f}",
            f"{float(m['stock_apres']):.2f}",
            f"{float(m['cout_unitaire'] or 0):,.2f}",
            f"{float(m['valeur'] or 0):+,.2f}",
            m["utilisateur"] or "",
            m["motif"] or "",
        )

    def _maj_indicateurs(self, t, produit_id):
        net = t["entrees"] - t["sorties"]
        self.kpi_nb.set(f"{t['nombre']:,}".replace(",", " "))
        self.kpi_nb_sub.set("sur la sélection")
        self.kpi_ent.set(f"{t['entrees']:,.2f}")
        self.kpi_ent_sub.set(f"valeur {t['valeur_entrees']:,.2f} DA")
        self.kpi_sor.set(f"{t['sorties']:,.2f}")
        self.kpi_sor_sub.set(f"valeur {t['valeur_sorties']:,.2f} DA")
        self.kpi_net.set(f"{net:+,.2f}")
        self.kpi_net_sub.set(f"valeur {t['valeur_entrees'] - t['valeur_sorties']:+,.2f} DA")
        if not produit_id:
            self.kpi_ent_sub.set(self.kpi_ent_sub.get() + " · unités mélangées")

    @staticmethod
    def _info_produit(conn, produit_id):
        """Ligne d'information quand un produit précis est filtré."""
        if not produit_id:
            return ""
        p = conn.execute(
            "SELECT code, designation, unite, stock_actuel FROM produits WHERE id=?",
            (produit_id,)).fetchone()
        if not p:
            return ""
        ecart = float(p["stock_actuel"] or 0) - sj.stock_selon_journal(conn, produit_id)
        etat = ("✔ journal cohérent" if abs(ecart) <= sj.TOLERANCE
                else f"⚠ écart de {ecart:+.2f} avec le journal (voir « Contrôle de cohérence »)")
        return (f"📦 {p['code']} — {p['designation']}   |   Stock actuel : "
                f"{float(p['stock_actuel'] or 0):.2f} {p['unite'] or ''}   |   {etat}")

    def _maj_pagination(self):
        if self._total == 0:
            self.page_var.set("Aucun mouvement")
        else:
            debut = self._offset + 1
            fin = min(self._offset + TAILLE_PAGE, self._total)
            self.page_var.set(f"Mouvements {debut} à {fin} sur {self._total}")
        self.btn_prec.config(state="normal" if self._offset > 0 else "disabled")
        self.btn_suiv.config(
            state="normal" if self._offset + TAILLE_PAGE < self._total else "disabled")

    def _page(self, sens):
        self._offset = max(0, self._offset + sens * TAILLE_PAGE)
        self.refresh(conserver_page=True)

    # ══════════════════════════ ACTIONS ══════════════════════════
    def voir_detail(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un mouvement")
            return
        m = self._lignes.get(sel[0])
        if m:
            MouvementDetailDialog(self, m)

    def ajuster(self):
        sel = self.tree.selection()
        produit_id = None
        if sel and sel[0] in self._lignes:
            produit_id = self._lignes[sel[0]]["produit_id"]
        elif self._filtres()["produit_id"]:
            produit_id = self._filtres()["produit_id"]
        d = AjustementStockDialog(self, produit_id=produit_id, on_saved=self._apres_modification)
        self.wait_window(d)

    def controler(self):
        d = CoherenceStockDialog(self, on_saved=self._apres_modification)
        self.wait_window(d)
        self.refresh(conserver_page=True)

    def _apres_modification(self):
        """Un ajustement/une régularisation change le stock : prévient les autres pages."""
        self.refresh()
        try:
            self.winfo_toplevel().event_generate("<<ProduitsModifies>>", when="tail")
        except tk.TclError:
            pass

    # ══════════════════════════ EXPORTS ══════════════════════════
    def _toutes_les_lignes(self):
        conn = get_conn()
        try:
            return sj.rechercher_mouvements(conn, **self._filtres(), limite=None)
        finally:
            conn.close()

    def export_csv(self):
        lignes = self._toutes_les_lignes()
        if not lignes:
            messagebox.showinfo("Export", "Aucun mouvement à exporter pour ces filtres.")
            return
        headers = ["Date / Heure", "Type", "Code produit", "Désignation", "Unité", "Document",
                   "N° document", "Client / Fournisseur", "Quantité", "Stock avant",
                   "Stock après", "Coût unitaire", "Valeur", "Utilisateur", "Motif"]
        data = [[
            m["date_mouvement"], sj.libelle_type(m["type_mouvement"]), m["produit_code"],
            m["produit_designation"], m["produit_unite"] or "",
            sj.libelle_document(m["document_type"]) if m["document_type"] else "",
            m["document_numero"] or "", m["tiers_nom"] or "",
            f"{float(m['quantite']):.2f}", f"{float(m['stock_avant']):.2f}",
            f"{float(m['stock_apres']):.2f}", f"{float(m['cout_unitaire'] or 0):.2f}",
            f"{float(m['valeur'] or 0):.2f}", m["utilisateur"] or "", m["motif"] or "",
        ] for m in lignes]
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"mouvements_stock_{date.today():%Y%m%d}.csv")
        if filename and export_to_csv(data, filename, headers):
            messagebox.showinfo("Succès", f"{len(data)} mouvement(s) exporté(s) :\n{filename}")

    def imprimer(self):
        lignes = self._toutes_les_lignes()
        if not lignes:
            messagebox.showinfo("Impression", "Aucun mouvement à imprimer pour ces filtres.")
            return
        tronque = len(lignes) > MAX_LIGNES_IMPRESSION
        lignes = lignes[:MAX_LIGNES_IMPRESSION]
        headers = ["Date / Heure", "Type", "Produit", "Document", "Quantité", "Stock après"]
        data = []
        for m in lignes:
            doc = m["document_numero"] or ""
            data.append([
                m["date_mouvement"], sj.libelle_type(m["type_mouvement"]),
                f"{m['produit_code']} {m['produit_designation']}", doc,
                f"{float(m['quantite']):+.2f}", f"{float(m['stock_apres']):.2f}",
            ])
        note = (f"Impression limitée aux {MAX_LIGNES_IMPRESSION} mouvements les plus récents "
                f"(utilisez l'export CSV pour tout obtenir)." if tronque else None)
        print_preview(data, "JOURNAL DES MOUVEMENTS DE STOCK", headers, footer_text=note)
