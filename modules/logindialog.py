"""Fenêtre de connexion, affichée au démarrage de l'application bureau."""
from api import rbac
from modules.core import *


class LoginDialog(tk.Toplevel):
    """
    Modale bloquante : demande identifiant + mot de passe, vérifie via
    api.rbac.authentifier(). En cas de succès, enregistre la connexion
    (dernière connexion + audit) et pose le résultat dans self.utilisateur.
    L'appelant (modules/app.py) doit faire `self.wait_window(dialog)` puis
    lire `dialog.utilisateur` : None si l'utilisateur a fermé sans se connecter.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.utilisateur = None
        self.title("Connexion — Gestion de Stock")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        self._build()
        self.update_idletasks()
        center_window(self, 380, self.winfo_reqheight())
        self.grab_set()
        self.user_entry.focus_set()

    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=28, pady=24)
        main.pack(fill="both", expand=True)

        lbl(main, "📦  GESTION DE STOCK", 15, True, color=CLR_ACCENT, bg=CLR_BG).pack(pady=(0, 2))
        lbl(main, "Connexion", 10, color=CLR_MUTED, bg=CLR_BG).pack(pady=(0, 16))

        lbl(main, "Identifiant", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.user_var = tk.StringVar()
        self.user_entry = entry(main, width=32, textvariable=self.user_var)
        self.user_entry.pack(fill="x", pady=(2, 10))
        self.user_entry.bind("<Return>", lambda e: self.pwd_entry.focus_set())

        lbl(main, "Mot de passe", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.pwd_var = tk.StringVar()
        self.pwd_entry = entry(main, width=32, textvariable=self.pwd_var, show="•")
        self.pwd_entry.pack(fill="x", pady=(2, 4))
        self.pwd_entry.bind("<Return>", lambda e: self.se_connecter())

        self.erreur_var = tk.StringVar(value="")
        lbl(main, "", 9, bg=CLR_BG, textvariable=self.erreur_var, color=CLR_RED,
            wraplength=320, justify="left").pack(anchor="w", pady=(4, 8))

        tk.Button(main, text="Se connecter", command=self.se_connecter,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=8, cursor="hand2").pack(fill="x", pady=(8, 0))

    def se_connecter(self):
        username = self.user_var.get().strip()
        password = self.pwd_var.get()
        if not username or not password:
            self.erreur_var.set("Saisissez l'identifiant et le mot de passe.")
            return

        conn = get_conn()
        try:
            user = rbac.authentifier(conn, username, password)
            if not user:
                rbac.ajouter_audit(conn, "CONNEXION_ECHEC", utilisateur=username,
                                   reussite=False, details="Identifiant ou mot de passe incorrect")
                conn.commit()
                self.erreur_var.set("Identifiant ou mot de passe incorrect.")
                self.pwd_var.set("")
                self.pwd_entry.focus_set()
                return
            rbac.enregistrer_connexion(conn, user["id"])
            rbac.ajouter_audit(conn, "CONNEXION", utilisateur=user["nom_complet"])
            conn.commit()
        finally:
            conn.close()

        self.utilisateur = user
        self.destroy()

    def _fermer(self):
        self.utilisateur = None
        self.destroy()
