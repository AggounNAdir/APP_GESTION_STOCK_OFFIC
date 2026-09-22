"""Contrôle de cohérence : le stock de chaque produit est-il égal à la somme de son journal ?"""
from api import stock_journal as sj
from modules.core import *


class CoherenceStockDialog(tk.Toplevel):
    """
    Liste les produits dont `stock_actuel` diffère de la somme de leurs
    mouvements (modification du stock hors journal : import, script, ancienne
    version de l'application...). « Régulariser » ajoute au journal un
    mouvement de régularisation égal à l'écart : le STOCK du produit n'est pas
    modifié, seul l'historique est complété (avec trace).
    """

    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Contrôle de cohérence du stock")
        self.configure(bg=CLR_BG)
        self.geometry("820x520")
        self._build()
        self.charger()
        center_window(self, 820, 520)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=20, pady=16)
        main.pack(fill="both", expand=True)
        lbl(main, "🩺 CONTRÔLE DE COHÉRENCE", 14, True, color=CLR_ACCENT, bg=CLR_BG).pack(anchor="w")
        lbl(main,
            "Compare le stock de chaque produit avec la somme de ses mouvements. "
            "Un écart signale une modification du stock qui n'a pas été journalisée.",
            9, color=CLR_MUTED, bg=CLR_BG, wraplength=760, justify="left").pack(anchor="w", pady=(2, 8))

        self.resume_var = tk.StringVar()
        self.lbl_resume = lbl(main, "", 11, True, bg=CLR_BG, textvariable=self.resume_var,
                              color=CLR_ORANGE)
        self.lbl_resume.pack(anchor="w", pady=(0, 6))

        cols = ["Code", "Désignation", "Unité", "Stock du produit", "Stock selon journal", "Écart"]
        widths = [90, 280, 70, 110, 120, 90]
        tf, self.tree = make_tree(main, cols, widths)
        tf.pack(fill="both", expand=True)
        self.tree.configure(selectmode="extended")
        self.tree.tag_configure("ecart", foreground=CLR_RED)

        bf = tk.Frame(main, bg=CLR_BG)
        bf.pack(fill="x", pady=(12, 0))
        self.btn_sel = tk.Button(bf, text="Régulariser la sélection", command=self.regulariser_selection,
                                 bg=CLR_ORANGE, fg="white", relief="flat",
                                 font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2")
        self.btn_sel.pack(side="left", padx=(0, 6))
        self.btn_tout = tk.Button(bf, text="Régulariser tout", command=self.regulariser_tout,
                                  bg=CLR_GREEN, fg="white", relief="flat",
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2")
        self.btn_tout.pack(side="left")
        tk.Button(bf, text="Fermer", command=self.destroy, bg=CLR_CARD, fg=CLR_TEXT,
                  relief="flat", font=("Segoe UI", 9), padx=16, pady=6,
                  cursor="hand2").pack(side="right")

    def charger(self):
        conn = get_conn()
        try:
            self.ecarts = sj.verifier_coherence(conn)
        finally:
            conn.close()
        self.tree.delete(*self.tree.get_children())
        for e in self.ecarts:
            self.tree.insert("", "end", iid=str(e["produit_id"]), tags=("ecart",), values=(
                e["code"], e["designation"], e["unite"] or "",
                f"{e['stock_actuel']:.2f}", f"{e['stock_journal']:.2f}", f"{e['ecart']:+.2f}"))
        if self.ecarts:
            self.resume_var.set(f"⚠️ {len(self.ecarts)} produit(s) en écart")
            self.lbl_resume.config(fg=CLR_ORANGE)
        else:
            self.resume_var.set("✅ Le journal est cohérent avec le stock de tous les produits.")
            self.lbl_resume.config(fg=CLR_GREEN)
        etat = "normal" if self.ecarts else "disabled"
        self.btn_sel.config(state=etat)
        self.btn_tout.config(state=etat)

    def _regulariser(self, produit_ids):
        if not produit_ids:
            messagebox.showwarning("Sélection", "Sélectionnez au moins un produit.", parent=self)
            return
        if not messagebox.askyesno(
                "Confirmation",
                f"Régulariser {len(produit_ids)} produit(s) ?\n\n"
                "Le stock des produits ne sera PAS modifié : un mouvement de "
                "« Régularisation » égal à l'écart sera ajouté au journal.",
                parent=self):
            return
        conn = get_conn()
        try:
            nb = sj.regulariser_ecarts(conn, produit_ids)
            conn.commit()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", f"Régularisation impossible : {ex}", parent=self)
            return
        finally:
            conn.close()
        messagebox.showinfo("Succès", f"{nb} produit(s) régularisé(s).", parent=self)
        self.charger()
        if self.on_saved:
            self.on_saved()

    def regulariser_selection(self):
        self._regulariser([int(i) for i in self.tree.selection()])

    def regulariser_tout(self):
        self._regulariser([e["produit_id"] for e in self.ecarts])
