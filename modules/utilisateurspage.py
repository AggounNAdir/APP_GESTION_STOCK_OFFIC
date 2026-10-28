"""
Page « Utilisateurs » : gestion des comptes de connexion à l'application bureau.

Réservée au rôle Administrateur (catégorie de droits « utilisateurs », voir
api/rbac.py). Permet de créer un compte, modifier son nom/rôle, l'activer ou
le désactiver, et réinitialiser son mot de passe (l'utilisateur devra le
changer à sa prochaine connexion).
"""
from datetime import datetime

from api import rbac
from modules.core import *


class UtilisateurDialog(tk.Toplevel):
    """Création ou modification d'un compte (le mot de passe se gère à part,
    via « Réinitialiser le mot de passe », pour rester simple et explicite)."""

    def __init__(self, parent, utilisateur=None):
        super().__init__(parent)
        self.utilisateur = utilisateur     # None = création
        self.resultat = False
        self.title("Nouvel utilisateur" if utilisateur is None else "Modifier l'utilisateur")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self._build()
        self.update_idletasks()
        center_window(self, 420, self.winfo_reqheight())
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=22, pady=18)
        main.pack(fill="both", expand=True)
        titre = "👤 NOUVEL UTILISATEUR" if self.utilisateur is None else "👤 MODIFIER L'UTILISATEUR"
        lbl(main, titre, 13, True, color=CLR_ACCENT, bg=CLR_BG).pack(anchor="w", pady=(0, 12))

        lbl(main, "Identifiant de connexion", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.username_var = tk.StringVar(value=self.utilisateur["username"] if self.utilisateur else "")
        e_user = entry(main, width=38, textvariable=self.username_var,
                       state="disabled" if self.utilisateur else "normal")
        e_user.pack(fill="x", pady=(2, 10))
        if self.utilisateur:
            lbl(main, "(l'identifiant ne peut pas être changé)", 8, color=CLR_MUTED, bg=CLR_BG).pack(
                anchor="w", pady=(0, 8))

        lbl(main, "Nom complet", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.nom_var = tk.StringVar(value=self.utilisateur["nom_complet"] if self.utilisateur else "")
        entry(main, width=38, textvariable=self.nom_var).pack(fill="x", pady=(2, 10))

        lbl(main, "Rôle", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.role_var = tk.StringVar(
            value=rbac.libelle_role(self.utilisateur["role"]) if self.utilisateur else
            rbac.libelle_role("lecture_seule"))
        self._roles_par_libelle = {v: k for k, v in rbac.ROLES.items()}
        combo(main, list(rbac.ROLES.values()), width=35, textvariable=self.role_var,
              state="readonly").pack(fill="x", pady=(2, 4))
        self.desc_role_var = tk.StringVar()
        lbl(main, "", 8, bg=CLR_BG, textvariable=self.desc_role_var, color=CLR_MUTED,
            wraplength=360, justify="left").pack(anchor="w", pady=(0, 10))
        self.role_var.trace_add("write", lambda *a: self._maj_description_role())
        self._maj_description_role()

        if self.utilisateur is None:
            lbl(main, f"Mot de passe initial (min. {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères)",
                9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
            self.pwd_var = tk.StringVar()
            entry(main, width=38, textvariable=self.pwd_var, show="•").pack(fill="x", pady=(2, 4))
            lbl(main, "L'utilisateur devra le changer à sa première connexion.",
                8, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w", pady=(0, 10))
        else:
            self.pwd_var = None

        self.erreur_var = tk.StringVar(value="")
        lbl(main, "", 9, bg=CLR_BG, textvariable=self.erreur_var, color=CLR_RED,
            wraplength=360, justify="left").pack(anchor="w", pady=(2, 8))

        bf = tk.Frame(main, bg=CLR_BG)
        bf.pack(fill="x", pady=(6, 0))
        tk.Button(bf, text="💾 Enregistrer", command=self.enregistrer,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=7, cursor="hand2").pack(side="left")
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 10),
                  padx=16, pady=7, cursor="hand2").pack(side="right")

    def _maj_description_role(self):
        role = self._roles_par_libelle.get(self.role_var.get())
        cats = sorted(rbac.libelle_categorie(c) for c in rbac.categories_du_role(role or ""))
        self.desc_role_var.set("Accès : " + (", ".join(cats) if cats else "aucune section"))

    def enregistrer(self):
        role = self._roles_par_libelle.get(self.role_var.get())
        nom = self.nom_var.get().strip()
        if not role:
            self.erreur_var.set("Sélectionnez un rôle.")
            return
        if not nom:
            self.erreur_var.set("Le nom complet est obligatoire.")
            return

        conn = get_conn()
        try:
            if self.utilisateur is None:
                username = self.username_var.get().strip()
                if not username:
                    self.erreur_var.set("L'identifiant est obligatoire.")
                    return
                if len(self.pwd_var.get()) < rbac.MOT_DE_PASSE_LONGUEUR_MIN:
                    self.erreur_var.set(
                        f"Le mot de passe doit contenir au moins {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères.")
                    return
                session = rbac.get_utilisateur_connecte()
                rbac.creer_utilisateur(
                    conn, username, nom, self.pwd_var.get(), role,
                    cree_par=session["nom_complet"] if session else None)
            else:
                session = rbac.get_utilisateur_connecte()
                rbac.modifier_utilisateur(
                    conn, self.utilisateur["id"], nom_complet=nom, role=role,
                    modifie_par=session["nom_complet"] if session else None)
                if self.utilisateur["id"] == (session["id"] if session else None) and \
                        role != self.utilisateur["role"]:
                    # On modifie son propre compte : recharge le rôle en session pour
                    # que le menu reflète immédiatement le nouveau rôle.
                    rbac.set_utilisateur_connecte({**session, "role": role})
            conn.commit()
        except ValueError as ex:
            conn.rollback()
            self.erreur_var.set(str(ex))
            return
        finally:
            conn.close()

        self.resultat = True
        self.destroy()


class ReinitialiserMotDePasseDialog(tk.Toplevel):
    """Réinitialisation du mot de passe D'UN AUTRE utilisateur par un
    administrateur : pas besoin de connaître l'ancien mot de passe, et le
    nouveau mot de passe devra être changé à la prochaine connexion."""

    def __init__(self, parent, utilisateur):
        super().__init__(parent)
        self.utilisateur = utilisateur
        self.resultat = False
        self.title("Réinitialiser le mot de passe")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self._build()
        self.update_idletasks()
        center_window(self, 380, self.winfo_reqheight())
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _build(self):
        main = tk.Frame(self, bg=CLR_BG, padx=22, pady=18)
        main.pack(fill="both", expand=True)
        lbl(main, "🔑 RÉINITIALISER LE MOT DE PASSE", 12, True, color=CLR_ACCENT, bg=CLR_BG).pack(
            anchor="w")
        lbl(main, f"Compte : {self.utilisateur['nom_complet']} ({self.utilisateur['username']})",
            9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w", pady=(2, 12))

        lbl(main, f"Nouveau mot de passe (min. {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères)",
            9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.nouveau_var = tk.StringVar()
        entry(main, width=34, textvariable=self.nouveau_var, show="•").pack(fill="x", pady=(2, 10))

        lbl(main, "Confirmation", 9, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w")
        self.confirm_var = tk.StringVar()
        entry(main, width=34, textvariable=self.confirm_var, show="•").pack(fill="x", pady=(2, 4))

        lbl(main, "L'utilisateur devra le changer à sa prochaine connexion.",
            8, color=CLR_MUTED, bg=CLR_BG).pack(anchor="w", pady=(2, 8))

        self.erreur_var = tk.StringVar(value="")
        lbl(main, "", 9, bg=CLR_BG, textvariable=self.erreur_var, color=CLR_RED,
            wraplength=330, justify="left").pack(anchor="w", pady=(2, 8))

        bf = tk.Frame(main, bg=CLR_BG)
        bf.pack(fill="x", pady=(6, 0))
        tk.Button(bf, text="✅ Réinitialiser", command=self.valider,
                  bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=7, cursor="hand2").pack(side="left")
        tk.Button(bf, text="Annuler", command=self.destroy,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 10),
                  padx=16, pady=7, cursor="hand2").pack(side="right")

    def valider(self):
        nouveau, confirm = self.nouveau_var.get(), self.confirm_var.get()
        if len(nouveau) < rbac.MOT_DE_PASSE_LONGUEUR_MIN:
            self.erreur_var.set(
                f"Le mot de passe doit contenir au moins {rbac.MOT_DE_PASSE_LONGUEUR_MIN} caractères.")
            return
        if nouveau != confirm:
            self.erreur_var.set("Les deux mots de passe ne correspondent pas.")
            return
        conn = get_conn()
        try:
            session = rbac.get_utilisateur_connecte()
            rbac.changer_mot_de_passe(
                conn, self.utilisateur["id"], nouveau, doit_changer_mdp=True,
                modifie_par=session["nom_complet"] if session else None)
            conn.commit()
        finally:
            conn.close()
        self.resultat = True
        messagebox.showinfo("Succès", "Mot de passe réinitialisé.", parent=self)
        self.destroy()


class UtilisateursPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._lignes = {}
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20, 10))
        lbl(hdr, "🔐  Utilisateurs", 16, True).pack(side="left")
        tk.Button(hdr, text="+ Nouvel utilisateur", command=self.nouveau,
                  bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=14, pady=7, cursor="hand2").pack(side="right")

        cols = ["Identifiant", "Nom complet", "Rôle", "Statut", "Doit changer mdp",
                "Créé le", "Dernière connexion"]
        widths = [110, 200, 130, 90, 120, 130, 150]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree.tag_configure("inactif", foreground=CLR_MUTED)
        self.tree.tag_configure("mdp_attendu", foreground=CLR_ORANGE)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0, 15))
        tk.Button(bf, text="✏ Modifier", command=self.modifier,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        self.btn_statut = tk.Button(bf, text="⏻ Activer / Désactiver", command=self.basculer_statut,
                                    bg=CLR_ORANGE, fg="white", relief="flat",
                                    font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2")
        self.btn_statut.pack(side="left", padx=4)
        tk.Button(bf, text="🔑 Réinitialiser le mot de passe", command=self.reinitialiser_mdp,
                  bg=CLR_PURPLE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🔄 Rafraîchir", command=self.refresh,
                  bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)

    def refresh(self):
        conn = get_conn()
        try:
            utilisateurs = rbac.lister_utilisateurs(conn)
        finally:
            conn.close()
        self._lignes = {str(u["id"]): u for u in utilisateurs}
        self.tree.delete(*self.tree.get_children())
        for u in utilisateurs:
            tags = []
            if not u["actif"]:
                tags.append("inactif")
            elif u["doit_changer_mdp"]:
                tags.append("mdp_attendu")
            self.tree.insert("", "end", iid=str(u["id"]), tags=tuple(tags), values=(
                u["username"], u["nom_complet"], rbac.libelle_role(u["role"]),
                "Actif" if u["actif"] else "Désactivé",
                "Oui" if u["doit_changer_mdp"] else "Non",
                (u["date_creation"] or "")[:10],
                u["derniere_connexion"] or "Jamais",
            ))

    def _selection(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un utilisateur")
            return None
        return self._lignes.get(sel[0])

    def nouveau(self):
        if not verifier_action("gerer_utilisateurs"):
            return
        d = UtilisateurDialog(self)
        self.wait_window(d)
        if d.resultat:
            self.refresh()

    def modifier(self):
        if not verifier_action("gerer_utilisateurs"):
            return
        u = self._selection()
        if not u:
            return
        d = UtilisateurDialog(self, u)
        self.wait_window(d)
        if d.resultat:
            self.refresh()

    def basculer_statut(self):
        if not verifier_action("gerer_utilisateurs"):
            return
        u = self._selection()
        if not u:
            return
        nouveau_statut = not u["actif"]
        verbe = "activer" if nouveau_statut else "désactiver"
        if not messagebox.askyesno(
                "Confirmation",
                f"Voulez-vous {verbe} le compte « {u['nom_complet']} » ({u['username']}) ?"):
            return
        conn = get_conn()
        try:
            session = rbac.get_utilisateur_connecte()
            rbac.activer_utilisateur(conn, u["id"], nouveau_statut,
                                     modifie_par=session["nom_complet"] if session else None)
            conn.commit()
        except ValueError as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex))
            return
        finally:
            conn.close()
        self.refresh()

    def reinitialiser_mdp(self):
        if not verifier_action("gerer_utilisateurs"):
            return
        u = self._selection()
        if not u:
            return
        d = ReinitialiserMotDePasseDialog(self, u)
        self.wait_window(d)
        if d.resultat:
            self.refresh()
