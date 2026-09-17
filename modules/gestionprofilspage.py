import sys
import subprocess

from modules.core import *
from modules.profildialog import ProfilDialog
from modules.theme import THEMES, THEME_KEYS, save_theme, get_current_theme_name

class GestionProfilsPage(tk.Frame):
    """Page de gestion des profils entreprise + paramètres d'apparence (thème)"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.theme_var = tk.StringVar(value=get_current_theme_name())
        self.theme_cards = {}
        self._build()
        self.refresh()
    
    def _build(self):
        # En-tête
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "🏢 Gestion des Profils Entreprise", 16, True).pack(side="left")
        
        btn_frame = tk.Frame(hdr, bg=CLR_BG)
        btn_frame.pack(side="right")
        
        tk.Button(btn_frame, text="+ Nouveau Profil", command=self.nouveau_profil,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=14, pady=7, cursor="hand2").pack(side="left", padx=4)
        
        # Configuration des types de documents
        config_frame = tk.LabelFrame(self, text="📄 Association Profil → Document", 
                                     bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        
        self.doc_types = [
            ("Facture", "facture"),
            ("Bon de livraison", "bon_livraison"),
            ("Devis", "devis"),
            ("Situation", "situation"),
        ]
        
        self.doc_vars = {}
        self.doc_combos = {}  # Garder une référence aux combobox
        for i, (label, key) in enumerate(self.doc_types):
            row = tk.Frame(config_frame, bg=CLR_CARD)
            row.pack(fill="x", pady=5)
            lbl(row, f"{label}:", 9, True, CLR_MUTED).pack(side="left", padx=5, ipadx=10)
            
            self.doc_vars[key] = tk.StringVar()
            cb = combo(row, [], width=30, textvariable=self.doc_vars[key])
            cb.pack(side="left", padx=10)
            self.doc_combos[key] = cb  # Stocker la référence
        
        tk.Button(config_frame, text="💾 Enregistrer la configuration", command=self.save_config,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(pady=10)
        
        # ── Apparence / Thème de l'application ──
        self._build_theme_section()
        
        # Tableau des profils
        cols = ["Code", "Nom", "Type", "Téléphone", "Email", "Défaut"]
        widths = [100, 200, 100, 120, 180, 80]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Actions
        action_frame = tk.Frame(self, bg=CLR_BG)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(action_frame, text="✏ Modifier", command=self.edit_profil,
                 bg=CLR_ORANGE, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="⭐ Définir par défaut", command=self.set_default,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(action_frame, text="🗑 Supprimer", command=self.delete_profil,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
    
    # ══════════════════════ APPARENCE / THÈME ══════════════════════
    
    def _build_theme_section(self):
        """Section de sélection du thème de l'application (migrée depuis ProfilPage)"""
        theme_frame = tk.LabelFrame(self, text="🎨 Apparence — Thème de l'application",
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
        theme_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        cards_row = tk.Frame(theme_frame, bg=CLR_CARD)
        cards_row.pack(fill="x", pady=(2, 8))
        
        for key in THEME_KEYS:
            self.theme_cards[key] = self._make_theme_card(cards_row, key)
        
        bottom = tk.Frame(theme_frame, bg=CLR_CARD)
        bottom.pack(fill="x")
        
        self.theme_status = lbl(bottom, "", 9, True, color=CLR_MUTED, bg=CLR_CARD)
        self.theme_status.pack(side="left", padx=5)
        
        tk.Button(bottom, text="💾 Appliquer le thème", command=self.appliquer_theme,
                 bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)
        
        self._refresh_theme_cards()
    
    def _make_theme_card(self, parent, key):
        """Crée une vignette cliquable d'aperçu pour un thème"""
        t = THEMES[key]
        
        card = tk.Frame(parent, bg=t["BG"], highlightthickness=2,
                        highlightbackground=CLR_BORDER, cursor="hand2",
                        padx=10, pady=8)
        card.pack(side="left", padx=6)
        
        titre = tk.Label(card, text=f"{t['emoji']}  {t['name']}",
                         bg=t["BG"], fg=t["TEXT"], font=("Segoe UI", 9, "bold"))
        titre.pack(anchor="w")
        
        # Aperçu des couleurs principales du thème
        swatch_row = tk.Frame(card, bg=t["BG"])
        swatch_row.pack(anchor="w", pady=(6, 0))
        for color_key in ("CARD", "ACCENT", "GREEN", "ORANGE", "RED"):
            tk.Frame(swatch_row, bg=t[color_key], width=18, height=14,
                     highlightthickness=1, highlightbackground=t["BORDER"]).pack(side="left", padx=1)
        
        # Clic sur la carte ou sur n'importe quel enfant
        for w in (card, titre, swatch_row):
            w.bind("<Button-1>", lambda e, k=key: self.selectionner_theme(k))
        
        return card
    
    def selectionner_theme(self, key):
        """Sélectionne (sans appliquer) un thème"""
        self.theme_var.set(key)
        self._refresh_theme_cards()
    
    def _refresh_theme_cards(self):
        """Met en évidence la vignette sélectionnée et met à jour le statut"""
        selected = self.theme_var.get()
        actuel = get_current_theme_name()
        
        for key, card in self.theme_cards.items():
            card.config(highlightbackground=CLR_ACCENT if key == selected else CLR_BORDER,
                        highlightthickness=3 if key == selected else 2)
        
        if hasattr(self, "theme_status"):
            nom_actuel = THEMES.get(actuel, {}).get("name", actuel)
            if selected == actuel:
                self.theme_status.config(text=f"Thème actuel : {nom_actuel}", fg=CLR_MUTED)
            else:
                nom_sel = THEMES.get(selected, {}).get("name", selected)
                self.theme_status.config(
                    text=f"Thème actuel : {nom_actuel}  →  sélectionné : {nom_sel} (non appliqué)",
                    fg=CLR_ORANGE)
    
    def appliquer_theme(self):
        """Enregistre le thème choisi dans config.json et propose le redémarrage"""
        key = self.theme_var.get()
        
        if key not in THEMES:
            messagebox.showwarning("", "Sélectionnez un thème")
            return
        
        if key == get_current_theme_name():
            messagebox.showinfo("Thème", f"Le thème « {THEMES[key]['name']} » est déjà appliqué.")
            return
        
        if not save_theme(key):
            messagebox.showerror("Erreur", "Impossible d'enregistrer le thème dans config.json")
            return
        
        self._refresh_theme_cards()
        
        if messagebox.askyesno(
            "Redémarrage requis",
            f"Thème « {THEMES[key]['name']} » enregistré.\n\n"
            "L'application doit redémarrer pour l'appliquer.\n"
            "Redémarrer maintenant ?"
        ):
            self.redemarrer_application()
        else:
            messagebox.showinfo("Thème", "Le thème sera appliqué au prochain démarrage.")
    
    def redemarrer_application(self):
        """Relance l'application (exe ou script) puis ferme l'instance courante"""
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable] + sys.argv[1:])
            else:
                subprocess.Popen([sys.executable] + sys.argv)
            self.winfo_toplevel().destroy()
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Redémarrage automatique impossible :\n{e}\n\n"
                "Fermez puis relancez l'application manuellement."
            )
    
    # ══════════════════════ PROFILS ══════════════════════
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        profils = conn.execute("SELECT * FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        for p in profils:
            default_mark = "✅" if p["est_defaut"] else ""
            self.tree.insert("", "end", iid=p["id"], values=(
                p["code"], p["nom"], p["type_profil"],
                p["telephone"] or "-", p["email"] or "-", default_mark
            ))
        
        # Charger la configuration
        self.load_config()
        
        # Resynchroniser la sélection de thème avec config.json
        if self.theme_cards:
            self.theme_var.set(get_current_theme_name())
            self._refresh_theme_cards()
    
    def load_config(self):
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        conn = get_conn()
        profils = conn.execute("SELECT id, code, nom FROM profils_entreprise ORDER BY nom").fetchall()
        conn.close()
        
        profil_liste = ["-- Aucun --"] + [f"{p['code']} - {p['nom']}" for p in profils]
        
        # Mettre à jour les valeurs des combobox
        for doc_key, var in self.doc_vars.items():
            var.set(config.get(doc_key, "-- Aucun --"))
            # Mettre à jour les valeurs du combobox via la référence stockée
            if doc_key in self.doc_combos:
                self.doc_combos[doc_key]['values'] = profil_liste
    
    def save_config(self):
        config = {}
        for doc_key, var in self.doc_vars.items():
            val = var.get()
            if val and val != "-- Aucun --":
                config[doc_key] = val
        
        config_file = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "profil_config.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Succès", "Configuration enregistrée")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def nouveau_profil(self):
        d = ProfilDialog(self)
        self.wait_window(d)
        self.refresh()
    
    def edit_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT * FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        
        d = ProfilDialog(self, dict(profil) if profil else None)
        self.wait_window(d)
        self.refresh()
    
    def set_default(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        try:
            conn.execute("UPDATE profils_entreprise SET est_defaut = 0")
            conn.execute("UPDATE profils_entreprise SET est_defaut = 1 WHERE id=?", (sel[0],))
            conn.commit()
            messagebox.showinfo("Succès", "Profil défini par défaut")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
    
    def delete_profil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un profil")
            return
        
        conn = get_conn()
        profil = conn.execute("SELECT nom, est_defaut FROM profils_entreprise WHERE id=?", (sel[0],)).fetchone()
        
        if profil["est_defaut"]:
            messagebox.showwarning("", "Impossible de supprimer le profil par défaut")
            conn.close()
            return
        
        if messagebox.askyesno("Confirmation", f"Supprimer le profil '{profil['nom']}' ?"):
            try:
                conn.execute("DELETE FROM profils_entreprise WHERE id=?", (sel[0],))
                conn.commit()
                messagebox.showinfo("Succès", "Profil supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        conn.close()