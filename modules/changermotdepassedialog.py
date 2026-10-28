"""Dialogue de changement de mot de passe (pour soi-même)."""
from api import rbac
from modules.core import *


class ChangerMotDePasseDialog(tk.Toplevel):
    """
    Changement du mot de passe de l'utilisateur connecté. `obligatoire=True`
    (première connexion, ou après réinitialisation par un administrateur)
    empêche de fermer la fenêtre sans changer le mot de passe.
    """

    def __init__(self, parent, user, *, obligatoire=False):
        super().__init__(parent)
        self.user = user
        self.obligatoire = obligatoire
        self.change = False
        self.title("Changer le mot de passe")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        if obligatoire:
            self.protocol("WM_DELETE_WINDOW", lambda: None)  # ne peut pas être fermée sans agir
        self._build()
        self.update_idletasks()
        center_window(self, 380, self.winfo_reqheight())
        self.grab_set()

    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        lbl(main, "🔑 CHANGER LE MOT DE PASSE", 13, True, color=CLR_ACCENT, bg=CLR_BG).pack(anchor="w")
        if self.obligatoire:
            lbl(main, "Un nouveau mot de passe est requis avant de continuer.",
                9, color=CLR_ORANGE, bg=CLR_BG, wraplength=320, justify="left").pack(anchor="w", pady=(2, 12))
        else:
            lbl(main, f"Compte : {self.user['nom_complet']}", 9, color=CLR_MUTED, bg=CLR_BG).pack(
                anchor="w", pady=(2, 12))

        if not self.obligatoire:
            lbl(main, "Mot de passe actuel", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
            self.actuel_var = tk.StringVar()
            entry(main, width=32, textvariable=self.actuel_var, show="•").pack(fill="x", pady=(2, 10))
        else:
            self.actuel_var = None

        lbl(main, f"Nouveau mot de passe (min. {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères)",
            9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.nouveau_var = tk.StringVar()
        entry(main, width=32, textvariable=self.nouveau_var, show="•").pack(fill="x", pady=(2, 10))

        lbl(main, "Confirmation", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.confirm_var = tk.StringVar()
        c = entry(main, width=32, textvariable=self.confirm_var, show="•")
        c.pack(fill="x", pady=(2, 4))
        c.bind("<Return>", lambda e: self.valider())

        self.erreur_var = tk.StringVar(value="")
        lbl(main, "", 9, bg=CLR_BG, textvariable=self.erreur_var, color=CLR_RED,
            wraplength=320, justify="left").pack(anchor="w", pady=(4, 8))

        bf = tk.Frame(main, bg=CLR_BG)
        bf.pack(fill="x", pady=(8, 0))
        tk.Button(bf, text="✅ Valider", command=self.valider,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=7, cursor="hand2").pack(side="left")
        if not self.obligatoire:
            tk.Button(bf, text="Annuler", command=self.destroy,
                      bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 10),
                      padx=16, pady=7, cursor="hand2").pack(side="right")

    def valider(self):
        nouveau = self.nouveau_var.get()
        confirm = self.confirm_var.get()
        if len(nouveau) < rbac.MOT_DE_PASSE_LONGUEUR_MIN:
            self.erreur_var.set(
                f"Le mot de passe doit contenir au moins {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères.")
            return
        if nouveau != confirm:
            self.erreur_var.set("Les deux mots de passe ne correspondent pas.")
            return

        conn = get_conn()
        try:
            if self.actuel_var is not None:
                if not rbac.authentifier(conn, self.user["username"], self.actuel_var.get()):
                    self.erreur_var.set("Mot de passe actuel incorrect.")
                    return
            rbac.changer_mot_de_passe(conn, self.user["id"], nouveau,
                                      doit_changer_mdp=False, modifie_par=self.user["nom_complet"])
            conn.commit()
        finally:
            conn.close()

        self.user["doit_changer_mdp"] = 0
        self.change = True
        messagebox.showinfo("Succès", "Mot de passe changé avec succès.", parent=self)
        self.destroy()
