"""Fenêtre de détail d'un mouvement de stock (lecture seule)."""
from api import stock_journal as sj
from modules.core import *


class MouvementDetailDialog(tk.Toplevel):
    """Affiche toutes les informations d'une ligne du journal des mouvements."""

    def __init__(self, parent, mvt):
        super().__init__(parent)
        self.mvt = mvt
        self.title(f"Mouvement de stock n°{mvt['id']}")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self._build()
        self.update_idletasks()
        center_window(self, 560, self.winfo_reqheight())
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _build(self):
        m = self.mvt
        q = float(m["quantite"])
        entree = q > 0
        unite = m.get("produit_unite") or ""

        main = tk.Frame(self, bg=CLR_BG, padx=20, pady=18)
        main.pack(fill="both", expand=True)

        lbl(main, f"📋 MOUVEMENT N° {m['id']}", 14, True, color=CLR_ACCENT, bg=CLR_BG).pack(pady=(0, 12))

        card = tk.Frame(main, bg=CLR_CARD, padx=20, pady=12)
        card.pack(fill="both", expand=True)

        def ligne(libelle, valeur, couleur=CLR_TEXT, gras=False):
            r = tk.Frame(card, bg=CLR_CARD)
            r.pack(fill="x", pady=3)
            lbl(r, f"{libelle} :", 10, color=CLR_MUTED, bg=CLR_CARD).pack(side="left")
            lbl(r, str(valeur), 10, gras, color=couleur, bg=CLR_CARD,
                justify="right", wraplength=340).pack(side="right")

        ligne("Date et heure", m["date_mouvement"])
        if m.get("date_document"):
            ligne("Date du document", m["date_document"])
        ligne("Produit", f"{m['produit_code']} — {m['produit_designation']}", gras=True)
        ligne("Type de mouvement", sj.libelle_type(m["type_mouvement"]), CLR_ACCENT, True)
        ligne("Sens", "Entrée en stock" if entree else "Sortie de stock",
              CLR_GREEN if entree else CLR_RED, True)
        ligne("Quantité", f"{q:+.2f} {unite}".strip(), CLR_GREEN if entree else CLR_RED, True)
        ligne("Stock avant → après",
              f"{float(m['stock_avant']):.2f}  →  {float(m['stock_apres']):.2f} {unite}".strip())
        ligne("Coût unitaire appliqué", f"{float(m['cout_unitaire'] or 0):,.2f} DA")
        ligne("Valeur du mouvement", f"{float(m['valeur'] or 0):+,.2f} DA")
        if m.get("pmp_apres") is not None:
            ligne("PMP après mouvement", f"{float(m['pmp_apres']):,.2f} DA")

        if m.get("document_type"):
            doc = sj.libelle_document(m["document_type"])
            if m.get("document_numero"):
                doc += f" n° {m['document_numero']}"
            ligne("Document", doc)
        if m.get("tiers_nom"):
            ligne("Client / Fournisseur", m["tiers_nom"])
        ligne("Motif", m.get("motif") or "—")
        ligne("Enregistré par", m.get("utilisateur") or "—")

        tk.Button(main, text="Fermer", command=self.destroy,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 10),
                  padx=20, pady=6, cursor="hand2").pack(pady=(12, 0))
