import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class DefinirMotDePasseVendeurDialog(tk.Toplevel):
    """Définit/réinitialise le mot de passe d'accès vendeur (tournée Androway)."""

    def __init__(self, parent, vendeur_id, code_vendeur, nom_vendeur):
        super().__init__(parent)
        self.vendeur_id = vendeur_id
        self.title(f"Mot de passe vendeur — {code_vendeur}")
        self.resizable(False, False)
        self.grab_set()

        f = tk.Frame(self, padx=20, pady=15)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="🔑 Nouveau mot de passe vendeur", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(f, text=f"Vendeur : {code_vendeur} — {nom_vendeur}", fg="#666").pack(anchor="w", pady=(0, 12))

        tk.Label(f, text="Mot de passe (min. 6 caractères)").pack(anchor="w")
        self.pwd_var = tk.StringVar()
        tk.Entry(f, width=30, textvariable=self.pwd_var, show="•").pack(anchor="w", pady=(2, 10))

        tk.Label(f, text="Confirmation").pack(anchor="w")
        self.pwd2_var = tk.StringVar()
        tk.Entry(f, width=30, textvariable=self.pwd2_var, show="•").pack(anchor="w", pady=(2, 15))

        btns = tk.Frame(f)
        btns.pack(fill="x")
        tk.Button(btns, text="💾 Enregistrer", command=self.save,
                  bg="#22c55e", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=16, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="❌ Annuler", command=self.destroy,
                  bg="#ef4444", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=16, pady=6, cursor="hand2").pack(side="left", padx=4)

    def save(self):
        pwd = self.pwd_var.get()
        pwd2 = self.pwd2_var.get()
        if len(pwd) < 6:
            messagebox.showerror("Erreur", "Le mot de passe doit contenir au moins 6 caractères.")
            return
        if pwd != pwd2:
            messagebox.showerror("Erreur", "Les deux mots de passe ne correspondent pas.")
            return

        try:
            import bcrypt
        except ImportError:
            messagebox.showerror(
                "Dépendance manquante",
                "Le module 'bcrypt' est requis.\nInstallez-le avec : pip install bcrypt"
            )
            return

        password_hash = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        conn = get_conn()
        try:
            conn.execute(
                "UPDATE vendeurs SET password_hash=?, actif=1 WHERE id=?",
                (password_hash, self.vendeur_id),
            )
            conn.commit()
            messagebox.showinfo("Succès", "Mot de passe vendeur défini et accès activé.")
            self.destroy()
        except Exception as ex:
            conn.rollback()
            messagebox.showerror("Erreur", str(ex))
        finally:
            conn.close()


class VendeurPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.selected_id = None

        # Titre
        tk.Label(self, text="👔 Gestion des Vendeurs", font=("Arial", 16, "bold")).pack(pady=10)

        # Formulaire
        form_frame = tk.LabelFrame(self, text="Nouveau / Modification")
        form_frame.pack(fill="x", pady=5, padx=10)

        tk.Label(form_frame, text="Code:").grid(row=0, column=0, padx=5, pady=5)
        self.ent_code = tk.Entry(form_frame)
        self.ent_code.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Nom:").grid(row=0, column=2, padx=5, pady=5)
        self.ent_nom = tk.Entry(form_frame)
        self.ent_nom.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(form_frame, text="Téléphone:").grid(row=0, column=4, padx=5, pady=5)
        self.ent_tel = tk.Entry(form_frame)
        self.ent_tel.grid(row=0, column=5, padx=5, pady=5)

        tk.Button(form_frame, text="💾 Enregistrer", command=self.save_vendeur).grid(row=0, column=6, padx=10)
        tk.Button(form_frame, text="🆕 Nouveau", command=self.clear_form).grid(row=0, column=7, padx=5)

        # Actions sur le vendeur sélectionné
        actions_frame = tk.Frame(self)
        actions_frame.pack(fill="x", padx=10, pady=(0, 5))
        tk.Button(actions_frame, text="🔑 Définir mot de passe portail", command=self.definir_mot_de_passe,
                  bg="#3b82f6", fg="white", relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=4)
        self.btn_toggle_actif = tk.Button(actions_frame, text="🔒 Désactiver l'accès",
                                           command=self.toggle_actif,
                                           bg="#f59e0b", fg="white", relief="flat",
                                           padx=10, pady=5, cursor="hand2")
        self.btn_toggle_actif.pack(side="left", padx=4)

        # Liste — colonnes explicites (⚠️ ne JAMAIS faire SELECT * ici : la
        # table vendeurs a une colonne password_hash en plus depuis la mise
        # en place du portail vendeur, qui ne doit ni s'afficher ni décaler
        # les colonnes du tableau).
        cols = ("id", "code", "nom", "tel", "actif", "portail")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, label, w in [
            ("id", "ID", 50), ("code", "Code", 100), ("nom", "Nom", 200),
            ("tel", "Téléphone", 120), ("actif", "Actif", 70), ("portail", "Mot de passe", 110),
        ]:
            self.tree.heading(c, text=label)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=10, padx=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh_list()

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_conn()
        try:
            for row in conn.execute(
                "SELECT id, code, nom, tel, actif, password_hash FROM vendeurs ORDER BY nom"
            ).fetchall():
                self.tree.insert("", "end", iid=row["id"], values=(
                    row["id"], row["code"], row["nom"], row["tel"] or "",
                    "✅" if row["actif"] else "❌",
                    "🔑 Défini" if row["password_hash"] else "— Aucun",
                ))
        finally:
            conn.close()

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.selected_id = None
            return
        self.selected_id = int(sel[0])
        vals = self.tree.item(sel[0], "values")
        self.ent_code.delete(0, tk.END); self.ent_code.insert(0, vals[1])
        self.ent_nom.delete(0, tk.END); self.ent_nom.insert(0, vals[2])
        self.ent_tel.delete(0, tk.END); self.ent_tel.insert(0, vals[3])
        self.btn_toggle_actif.config(
            text="🔒 Désactiver l'accès" if vals[4] == "✅" else "🔓 Réactiver l'accès",
            bg="#f59e0b" if vals[4] == "✅" else "#22c55e",
        )

    def clear_form(self):
        self.selected_id = None
        self.ent_code.delete(0, tk.END)
        self.ent_nom.delete(0, tk.END)
        self.ent_tel.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def save_vendeur(self):
        code = self.ent_code.get().strip()
        nom = self.ent_nom.get().strip()
        tel = self.ent_tel.get().strip()

        if not code or not nom:
            messagebox.showwarning("Erreur", "Code et Nom obligatoires")
            return

        conn = get_conn()
        try:
            if self.selected_id:
                conn.execute(
                    "UPDATE vendeurs SET code=?, nom=?, tel=? WHERE id=?",
                    (code, nom, tel, self.selected_id),
                )
            else:
                conn.execute(
                    "INSERT INTO vendeurs (code, nom, tel) VALUES (?, ?, ?)",
                    (code, nom, tel),
                )
            conn.commit()
            self.refresh_list()
            self.clear_form()
            messagebox.showinfo("Succès", "Vendeur enregistré")
        except sqlite3.IntegrityError:
            conn.rollback()
            messagebox.showerror("Erreur", "Le code vendeur existe déjà")
        finally:
            conn.close()

    def definir_mot_de_passe(self):
        if not self.selected_id:
            messagebox.showwarning("Sélection", "Sélectionnez un vendeur dans la liste.")
            return
        d = DefinirMotDePasseVendeurDialog(self, self.selected_id, self.ent_code.get(), self.ent_nom.get())
        self.wait_window(d)
        self.refresh_list()

    def toggle_actif(self):
        if not self.selected_id:
            messagebox.showwarning("Sélection", "Sélectionnez un vendeur dans la liste.")
            return
        conn = get_conn()
        try:
            row = conn.execute("SELECT actif FROM vendeurs WHERE id=?", (self.selected_id,)).fetchone()
            if row is None:
                return
            nouveau = 0 if row["actif"] else 1
            conn.execute("UPDATE vendeurs SET actif=? WHERE id=?", (nouveau, self.selected_id))
            conn.commit()
            self.refresh_list()
        finally:
            conn.close()