from modules.core import *
from api import princing


class PaliersDialog(tk.Toplevel):
    """
    Saisie des paliers de quantité d'un produit
    (« à partir de N unités, le niveau X paie Y DA l'unité »).

    Travaille sur une COPIE de la liste : rien n'est écrit dans la base ici.
    Quand l'utilisateur clique « Valider », `on_valider(liste)` est appelé ;
    ProduitDialog garde la liste et l'enregistre avec la fiche produit
    (voir princing.enregistrer_paliers).

    Paramètres
      designation     : nom du produit (affichage)
      paliers         : liste de {"niveau", "qte_min", "prix"}
      on_valider      : callback(liste_de_paliers)
      facteur_fn      : () -> facteur de conversion courant (pour « ≈ cartons »)
      prix_niveau_fn  : (niveau) -> prix normal saisi pour ce niveau (contrôle)
      cout_fn         : () -> prix d'achat saisi (contrôle « sous le coût »)
    """

    NIVEAUX = [
        ("super_gros", "Super Gros"),
        ("gros", "Gros"),
        ("detail", "Détail"),
        ("special", "Spécial"),
    ]

    def __init__(self, parent, designation, paliers, on_valider,
                 facteur_fn=None, prix_niveau_fn=None, cout_fn=None):
        super().__init__(parent)
        self.title("📦 Paliers de quantité")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.transient(parent)

        self.designation = designation or ""
        self.paliers = princing.normaliser_paliers(paliers or [])
        self.on_valider = on_valider
        self.facteur_fn = facteur_fn
        self.prix_niveau_fn = prix_niveau_fn
        self.cout_fn = cout_fn
        self._libelle_vers_code = {lib: code for code, lib in self.NIVEAUX}
        self._code_vers_libelle = dict(self.NIVEAUX)

        self._build()
        self._refresh()
        self.update_idletasks()
        center_window(self, self.winfo_width(), self.winfo_height())
        self.grab_set()

    # ── Construction ────────────────────────────────────────────────────────

    def _build(self):
        f = tk.Frame(self, bg=CLR_BG, padx=20, pady=15)
        f.pack(fill="both", expand=True)

        lbl(f, f"Produit : {self.designation}", 11, True, color=CLR_ACCENT).pack(anchor="w")
        lbl(f,
            "Un palier baisse le prix quand la quantité atteint un seuil.\n"
            "Quantités en UNITÉS de vente (la même unité que le prix) ; prix par unité.",
            8, color=CLR_MUTED, justify="left").pack(anchor="w", pady=(2, 8))

        # ── Formulaire ──
        form = tk.LabelFrame(f, text="Ajouter / modifier un palier", bg=CLR_CARD,
                             fg=CLR_ACCENT, font=("Segoe UI", 9, "bold"),
                             padx=12, pady=8)
        form.pack(fill="x")

        lbl(form, "Niveau", color=CLR_MUTED, bg=CLR_CARD).grid(row=0, column=0, sticky="w")
        self.niveau_var = tk.StringVar(value=self._code_vers_libelle["gros"])
        combo(form, [lib for _, lib in self.NIVEAUX], width=14,
              textvariable=self.niveau_var, state="readonly").grid(
            row=1, column=0, padx=(0, 12), pady=2)

        lbl(form, "À partir de (unités)", color=CLR_MUTED, bg=CLR_CARD).grid(
            row=0, column=1, sticky="w")
        self.qte_var = tk.StringVar()
        entry(form, width=12, textvariable=self.qte_var).grid(
            row=1, column=1, padx=(0, 12), pady=2)

        lbl(form, "Prix par unité (DA)", color=CLR_MUTED, bg=CLR_CARD).grid(
            row=0, column=2, sticky="w")
        self.prix_var = tk.StringVar()
        entry(form, width=12, textvariable=self.prix_var).grid(
            row=1, column=2, padx=(0, 12), pady=2)

        tk.Button(form, text="➕ Ajouter / Modifier", command=self.ajouter,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=4,
                  cursor="hand2").grid(row=1, column=3, pady=2)

        self.equiv_var = tk.StringVar(value="")
        tk.Label(form, textvariable=self.equiv_var, bg=CLR_CARD, fg=CLR_ORANGE,
                 font=("Segoe UI", 8, "bold")).grid(row=2, column=1, sticky="w")
        self.qte_var.trace_add("write", self._maj_equivalent)

        # ── Liste ──
        cols = ("Niveau", "À partir de", "≈ Cartons", "Prix palier", "Prix normal du niveau")
        frame, self.tree = make_tree(f, cols, [110, 110, 100, 110, 160])
        self.tree.configure(height=7)
        frame.pack(fill="both", expand=True, pady=(10, 4))
        self.tree.bind("<<TreeviewSelect>>", self._charger_selection)

        # ── Boutons ──
        bf = tk.Frame(f, bg=CLR_BG)
        bf.pack(fill="x", pady=(8, 0))
        tk.Button(bf, text="🗑 Supprimer la ligne", command=self.supprimer,
                  bg=CLR_RED, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                  font=("Segoe UI", 9), padx=14, pady=6,
                  cursor="hand2").pack(side="right", padx=(6, 0))
        tk.Button(bf, text="✅ Valider", command=self.valider,
                  bg=CLR_GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14, pady=6,
                  cursor="hand2").pack(side="right")

        lbl(f, "Les paliers sont enregistrés avec la fiche produit (bouton « Enregistrer »).",
            8, italic=True, color=CLR_MUTED).pack(anchor="w", pady=(8, 0))

    # ── Outils ──────────────────────────────────────────────────────────────

    def _facteur(self):
        try:
            fc = float(self.facteur_fn()) if self.facteur_fn else 1.0
        except Exception:
            fc = 1.0
        return fc if fc > 0 else 1.0

    def _prix_niveau(self, niveau):
        try:
            return float(self.prix_niveau_fn(niveau) or 0) if self.prix_niveau_fn else 0.0
        except Exception:
            return 0.0

    def _cout(self):
        try:
            return float(self.cout_fn() or 0) if self.cout_fn else 0.0
        except Exception:
            return 0.0

    def _maj_equivalent(self, *_):
        try:
            q = parse_decimal(self.qte_var.get())
        except (ValueError, TypeError):
            self.equiv_var.set("")
            return
        fc = self._facteur()
        self.equiv_var.set(f"≈ {q / fc:,.2f} carton(s) de {fc:g}" if fc > 1 else "")

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        fc = self._facteur()
        for i, p in enumerate(self.paliers):
            pn = self._prix_niveau(p["niveau"])
            self.tree.insert("", "end", iid=str(i), values=(
                self._code_vers_libelle.get(p["niveau"], p["niveau"]),
                f"{p['qte_min']:g}",
                f"{p['qte_min'] / fc:,.2f}",
                f"{p['prix']:,.2f} DA",
                f"{pn:,.2f} DA" if pn > 0 else "—",
            ))

    def _charger_selection(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        p = self.paliers[int(sel[0])]
        self.niveau_var.set(self._code_vers_libelle.get(p["niveau"], p["niveau"]))
        self.qte_var.set(f"{p['qte_min']:g}")
        self.prix_var.set(f"{p['prix']:.2f}")

    # ── Actions ─────────────────────────────────────────────────────────────

    def ajouter(self):
        niveau = self._libelle_vers_code.get(self.niveau_var.get(), "gros")
        try:
            qte = parse_decimal(self.qte_var.get())
            prix = parse_decimal(self.prix_var.get())
        except (ValueError, TypeError):
            messagebox.showerror("Erreur", "Quantité ou prix invalide.", parent=self)
            return

        erreur, avert = princing.valider_palier(
            niveau, qte, prix,
            prix_niveau=self._prix_niveau(niveau), cout=self._cout())
        if erreur:
            messagebox.showerror("Erreur", erreur, parent=self)
            return
        if avert and not messagebox.askyesno(
                "Vérifier ce palier",
                "\n\n".join(avert) + "\n\nEnregistrer quand même ?", parent=self):
            return

        # Même (niveau, quantité) → remplacé ; sinon ajouté
        self.paliers = princing.normaliser_paliers(
            self.paliers + [{"niveau": niveau, "qte_min": qte, "prix": prix}])
        self.qte_var.set("")
        self.prix_var.set("")
        self._refresh()

    def supprimer(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez une ligne à supprimer.", parent=self)
            return
        del self.paliers[int(sel[0])]
        self._refresh()

    def valider(self):
        avert = princing.verifier_coherence_paliers(self.paliers)
        if avert and not messagebox.askyesno(
                "Paliers incohérents",
                "\n\n".join(avert) + "\n\nValider quand même ?", parent=self):
            return
        self.on_valider(list(self.paliers))
        self.destroy()
