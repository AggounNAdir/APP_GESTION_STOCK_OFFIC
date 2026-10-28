"""
Page « Journal d'audit » : lecture seule des connexions, échecs de connexion,
et de toute action touchant aux comptes utilisateurs (api/rbac.py, table
journal_audit — en ajout seul, comme mouvements_stock).
"""
from datetime import date, timedelta

from api import rbac
from modules.core import *
from modules.dateentry import DateEntry

TAILLE_PAGE = 200
TOUS = "Tous"

LIBELLES_ACTION = {
    "CONNEXION": "Connexion réussie",
    "CONNEXION_ECHEC": "Échec de connexion",
    "CREATION_UTILISATEUR": "Création d'un utilisateur",
    "MODIFICATION_UTILISATEUR": "Modification d'un utilisateur",
    "ACTIVATION_UTILISATEUR": "Activation d'un compte",
    "DESACTIVATION_UTILISATEUR": "Désactivation d'un compte",
    "CHANGEMENT_MOT_DE_PASSE": "Changement de mot de passe",
}


def _libelle_action(code):
    return LIBELLES_ACTION.get(code, code)


class JournalAuditPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._offset = 0
        self._total = 0
        self._after_id = None
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20, 8))
        lbl(hdr, "🗂️  Journal d'audit", 16, True).pack(side="left")

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

        lbl(f1, "Action:", color=CLR_MUTED).pack(side="left", padx=(18, 4))
        self.action_var = tk.StringVar(value=TOUS)
        cb = combo(f1, [TOUS] + list(LIBELLES_ACTION.values()), width=24,
                  textvariable=self.action_var, state="readonly")
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        f2 = tk.Frame(self, bg=CLR_BG)
        f2.pack(fill="x", padx=20, pady=3)
        lbl(f2, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        entry(f2, width=30, textvariable=self.search_var).pack(side="left", padx=(6, 8))
        lbl(f2, "(utilisateur, détails)", 8, color=CLR_MUTED).pack(side="left")
        for var in (self.date_debut_var, self.date_fin_var, self.search_var):
            var.trace_add("write", lambda *a: self._planifier_refresh())

        cols = ["Date / Heure", "Utilisateur", "Action", "Résultat", "Cible", "Détails"]
        widths = [140, 170, 190, 90, 140, 320]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=8)
        self.tree.tag_configure("echec", foreground=CLR_RED)

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

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(8, 15))
        tk.Button(bf, text="🔄 Rafraîchir", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)
        tk.Button(bf, text="📄 Export CSV", command=self.export_csv,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)

    def _periode_rapide(self, jours):
        if jours is None:
            self.date_debut_var.set("")
            self.date_fin_var.set("")
        else:
            self.date_debut_var.set((date.today() - timedelta(days=jours)).strftime("%Y-%m-%d"))
            self.date_fin_var.set(date.today().strftime("%Y-%m-%d"))

    def _planifier_refresh(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(350, self.refresh)

    def _code_action(self):
        libelle = self.action_var.get()
        if libelle == TOUS:
            return None
        for code, lib in LIBELLES_ACTION.items():
            if lib == libelle:
                return code
        return None

    def _filtres(self):
        debut = self.date_debut_var.get().strip()
        fin = self.date_fin_var.get().strip()
        return {
            "date_debut": debut if debut and valider_date(debut) else None,
            "date_fin": fin if fin and valider_date(fin) else None,
            "action": self._code_action(),
            "texte": self.search_var.get().strip() or None,
        }

    def refresh(self, conserver_page=False):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if not conserver_page:
            self._offset = 0
        filtres = self._filtres()
        conn = get_conn()
        try:
            lignes = rbac.rechercher_audit(conn, **filtres, limite=TAILLE_PAGE, offset=self._offset)
            self._total = len(rbac.rechercher_audit(conn, **filtres, limite=None))
        finally:
            conn.close()

        self.tree.delete(*self.tree.get_children())
        for a in lignes:
            cible = f"{a['cible_type']} #{a['cible_id']}" if a["cible_type"] else ""
            tags = ("echec",) if not a["reussite"] else ()
            self.tree.insert("", "end", iid=str(a["id"]), tags=tags, values=(
                a["date_action"], a["utilisateur"] or "", _libelle_action(a["action"]),
                "OK" if a["reussite"] else "Échec", cible, a["details"] or "",
            ))
        self._maj_pagination()

    def _maj_pagination(self):
        if self._total == 0:
            self.page_var.set("Aucune entrée")
        else:
            debut = self._offset + 1
            fin = min(self._offset + TAILLE_PAGE, self._total)
            self.page_var.set(f"Entrées {debut} à {fin} sur {self._total}")
        self.btn_prec.config(state="normal" if self._offset > 0 else "disabled")
        self.btn_suiv.config(
            state="normal" if self._offset + TAILLE_PAGE < self._total else "disabled")

    def _page(self, sens):
        self._offset = max(0, self._offset + sens * TAILLE_PAGE)
        self.refresh(conserver_page=True)

    def export_csv(self):
        conn = get_conn()
        try:
            lignes = rbac.rechercher_audit(conn, **self._filtres(), limite=None)
        finally:
            conn.close()
        if not lignes:
            messagebox.showinfo("Export", "Aucune entrée à exporter pour ces filtres.")
            return
        headers = ["Date / Heure", "Utilisateur", "Action", "Résultat", "Type cible",
                   "ID cible", "Détails"]
        data = [[
            a["date_action"], a["utilisateur"] or "", _libelle_action(a["action"]),
            "OK" if a["reussite"] else "Échec", a["cible_type"] or "", a["cible_id"] or "",
            a["details"] or "",
        ] for a in lignes]
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"journal_audit_{date.today():%Y%m%d}.csv")
        if filename and export_to_csv(data, filename, headers):
            messagebox.showinfo("Succès", f"{len(data)} entrée(s) exportée(s) :\n{filename}")
