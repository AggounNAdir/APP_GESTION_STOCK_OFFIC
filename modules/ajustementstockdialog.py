"""Dialogue d'ajustement manuel du stock (casse, perte, écart d'inventaire...)."""
from modules.core import *

MOTIFS_COURANTS = [
    "Casse / produit endommagé",
    "Perte / vol",
    "Produit périmé / invendable",
    "Écart d'inventaire",
    "Erreur de saisie précédente",
    "Échantillon / don",
    "Autre (précisez)",
]


class AjustementStockDialog(tk.Toplevel):
    """
    Corrige le stock d'un produit : entrée, sortie, ou « fixer à la quantité
    constatée ». L'opération est inscrite dans le journal des mouvements
    (type « Ajustement manuel »), avec son motif, et ne peut pas être effacée.
    """

    def __init__(self, parent, produit_id=None, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self._infos = {}            # id -> dict produit
        self._libelle_vers_id = {}
        self.title("Ajustement de stock")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self._charger_produits()
        self._build()
        if produit_id is not None:
            self.select_produit(produit_id)
        self.update_idletasks()
        center_window(self, 560, self.winfo_reqheight())
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    # ── données ──────────────────────────────────────────────────────
    def _charger_produits(self):
        conn = get_conn()
        try:
            rows = conn.execute(
                """SELECT id, code, designation, unite, facteur_conversion,
                          stock_actuel, prix_moyen_pondere, prix_achat
                   FROM produits WHERE actif = 1 AND code <> 'SOLDE_INITIAL'
                   ORDER BY designation"""
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            lib = f"{r['code']} — {r['designation']}"
            self._infos[r["id"]] = dict(r)
            self._libelle_vers_id[lib] = r["id"]
        self._libelles = list(self._libelle_vers_id.keys())

    # ── interface ────────────────────────────────────────────────────
    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=20, pady=18)
        main.pack(fill="both", expand=True)
        lbl(main, "⚖️ AJUSTEMENT DE STOCK", 14, True, color=CLR_ACCENT, bg=CLR_BG).pack(pady=(0, 10))

        card = tk.Frame(main, bg=CLR_CARD, padx=18, pady=14)
        card.pack(fill="x")

        # Produit
        lbl(card, "Produit :", 10, color=CLR_MUTED, bg=CLR_CARD).pack(anchor="w")
        self.produit_var = tk.StringVar()
        self.produit_cb = combo(card, self._libelles, width=58, textvariable=self.produit_var)
        self.produit_cb.pack(fill="x", pady=(2, 6))
        self.produit_cb.bind("<<ComboboxSelected>>", lambda e: self._maj_infos())
        self.produit_cb.bind("<KeyRelease>", self._filtrer_liste)
        self.produit_cb.bind("<Return>", self._valider_saisie_produit)

        self.info_var = tk.StringVar(value="Sélectionnez un produit.")
        lbl(card, "", 10, bg=CLR_CARD, textvariable=self.info_var, color=CLR_TEXT,
            justify="left").pack(anchor="w", pady=(0, 8))

        # Mode
        lbl(card, "Type d'ajustement :", 10, color=CLR_MUTED, bg=CLR_CARD).pack(anchor="w")
        self.mode_var = tk.StringVar(value="entree")
        for valeur, texte in (
            ("entree", "➕  Entrée : ajouter cette quantité au stock"),
            ("sortie", "➖  Sortie : retirer cette quantité du stock"),
            ("fixer",  "🎯  Fixer : le stock réel constaté est de ..."),
        ):
            tk.Radiobutton(card, text=texte, variable=self.mode_var, value=valeur,
                           command=self._maj_apercu, bg=CLR_CARD, fg=CLR_TEXT,
                           selectcolor=CLR_INPUT, activebackground=CLR_CARD,
                           activeforeground=CLR_TEXT, anchor="w",
                           font=("Segoe UI", 9)).pack(anchor="w")

        # Quantité
        rq = tk.Frame(card, bg=CLR_CARD)
        rq.pack(fill="x", pady=(8, 2))
        self.lbl_qte = lbl(rq, "Quantité :", 10, color=CLR_MUTED, bg=CLR_CARD)
        self.lbl_qte.pack(side="left")
        self.qte_var = tk.StringVar()
        self.qte_var.trace_add("write", lambda *a: self._maj_apercu())
        entry(rq, width=14, textvariable=self.qte_var).pack(side="left", padx=10)
        self.unite_var = tk.StringVar(value="")
        lbl(rq, "", 10, bg=CLR_CARD, textvariable=self.unite_var, color=CLR_MUTED).pack(side="left")

        self.apercu_var = tk.StringVar(value="")
        self.lbl_apercu = lbl(card, "", 10, True, bg=CLR_CARD, textvariable=self.apercu_var,
                              color=CLR_ORANGE)
        self.lbl_apercu.pack(anchor="w", pady=(6, 8))

        # Motif
        lbl(card, "Motif (obligatoire) :", 10, color=CLR_MUTED, bg=CLR_CARD).pack(anchor="w")
        self.motif_var = tk.StringVar()
        combo(card, MOTIFS_COURANTS, width=58, textvariable=self.motif_var).pack(fill="x", pady=(2, 0))

        # Boutons
        bf = tk.Frame(main, bg=CLR_BG)
        bf.pack(fill="x", pady=(14, 0))
        tk.Button(bf, text="✅ Enregistrer l'ajustement", command=self.enregistrer,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=7, cursor="hand2").pack(side="left")
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 10),
                  padx=16, pady=7, cursor="hand2").pack(side="right")

    # ── comportement ─────────────────────────────────────────────────
    def _filtrer_liste(self, event=None):
        if event is not None and event.keysym in ("Return", "Up", "Down", "Escape", "Tab"):
            return
        texte = self.produit_var.get().strip().lower()
        self.produit_cb["values"] = (
            [l for l in self._libelles if texte in l.lower()] if texte else self._libelles
        )

    def _valider_saisie_produit(self, event=None):
        """Entrée dans le champ produit : prend le premier produit correspondant."""
        if self.produit_var.get() not in self._libelle_vers_id:
            valeurs = self.produit_cb["values"]
            if valeurs and len(valeurs) < len(self._libelles):
                self.produit_var.set(valeurs[0])
        self._maj_infos()

    def select_produit(self, produit_id):
        for lib, pid in self._libelle_vers_id.items():
            if pid == int(produit_id):
                self.produit_var.set(lib)
                break
        self._maj_infos()

    def _produit(self):
        pid = self._libelle_vers_id.get(self.produit_var.get())
        return self._infos.get(pid) if pid else None

    def _maj_infos(self):
        p = self._produit()
        if not p:
            self.info_var.set("Sélectionnez un produit.")
            self.unite_var.set("")
            self._maj_apercu()
            return
        stock = float(p["stock_actuel"] or 0)
        unite = p["unite"] or ""
        pmp = float(p["prix_moyen_pondere"] or 0) or float(p["prix_achat"] or 0)
        texte = f"Stock actuel : {stock:.2f} {unite}   |   Coût moyen : {pmp:,.2f} DA"
        facteur = float(p["facteur_conversion"] or 1)
        if facteur > 1:
            texte += f"\n1 carton = {facteur:g} {unite}   (saisir la quantité en {unite})"
        self.info_var.set(texte)
        self.unite_var.set(unite)
        self._maj_apercu()

    def _quantite(self):
        try:
            q = parse_decimal(self.qte_var.get())
        except (ValueError, TypeError):
            return None
        return q if q == q and abs(q) != float("inf") else None   # refuse nan / inf

    def _delta(self):
        """Variation qui sera appliquée, ou None si la saisie est incomplète."""
        p = self._produit()
        q = self._quantite()
        if not p or q is None or self.qte_var.get().strip() == "":
            return None
        stock = float(p["stock_actuel"] or 0)
        mode = self.mode_var.get()
        if mode == "entree":
            return q
        if mode == "sortie":
            return -q
        return q - stock          # fixer

    def _maj_apercu(self):
        self.lbl_qte.config(
            text="Stock constaté :" if self.mode_var.get() == "fixer" else "Quantité :")
        p = self._produit()
        delta = self._delta()
        if not p or delta is None:
            self.apercu_var.set("")
            return
        stock = float(p["stock_actuel"] or 0)
        apres = stock + delta
        self.apercu_var.set(f"Stock après ajustement : {apres:.2f} {p['unite'] or ''}"
                            f"   (variation {delta:+.2f})")
        self.lbl_apercu.config(fg=CLR_RED if apres < 0 else CLR_ORANGE)

    def enregistrer(self):
        p = self._produit()
        if not p:
            messagebox.showerror("Erreur", "Sélectionnez un produit.", parent=self)
            return
        q = self._quantite()
        if q is None or self.qte_var.get().strip() == "":
            messagebox.showerror("Erreur", "Saisissez une quantité valide.", parent=self)
            return
        mode = self.mode_var.get()
        if mode in ("entree", "sortie") and q <= 0:
            messagebox.showerror("Erreur", "La quantité doit être supérieure à 0.", parent=self)
            return
        if mode == "fixer" and q < 0:
            messagebox.showerror("Erreur", "Le stock constaté ne peut pas être négatif.", parent=self)
            return
        motif = self.motif_var.get().strip()
        if not motif or motif == MOTIFS_COURANTS[-1]:
            messagebox.showerror(
                "Motif obligatoire",
                "Indiquez le motif de l'ajustement (il sera conservé dans le journal).",
                parent=self)
            return

        delta = self._delta()
        stock = float(p["stock_actuel"] or 0)
        if abs(delta) < 1e-9:
            messagebox.showinfo("Aucun changement",
                                "Le stock est déjà égal à la quantité indiquée.", parent=self)
            return
        message = (f"Produit : {p['designation']}\n"
                   f"Stock actuel : {stock:.2f}  →  {stock + delta:.2f} {p['unite'] or ''}\n"
                   f"Variation : {delta:+.2f}\nMotif : {motif}\n\n")
        if stock + delta < 0:
            message += "⚠️ Ce stock sera NÉGATIF.\n\n"
        message += "Enregistrer l'ajustement ? (il ne pourra pas être supprimé)"
        if not messagebox.askyesno("Confirmation", message, parent=self):
            return

        conn = get_conn()
        try:
            if mode == "fixer":
                ajuster_stock_manuel(conn, p["id"], motif, nouveau_stock=q)
            else:
                ajuster_stock_manuel(conn, p["id"], motif, delta=delta)
            conn.commit()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Ajustement impossible : {ex}", parent=self)
            return
        finally:
            conn.close()

        messagebox.showinfo("Succès", "Ajustement enregistré dans le journal des mouvements.",
                            parent=self)
        self.destroy()
        if self.on_saved:
            self.on_saved()
