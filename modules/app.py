from modules.commandesclientpage import CommandesClientsPage

from modules.dashboardpage import DashboardPage
from modules.portailsuivipage import PortailSuiviPage
from modules.produitpage import ProduitPage
from modules.prospectspage import ProspectsPage
from modules.tierspage import TiersPage
from modules.bonachatpage import BonAchatPage
from modules.bonventepage import BonVentePage
from modules.facturepage import FacturePage
from modules.versementpage import VersementPage
from modules.versementsunifiespage import VersementsPage
from modules.retourpage import RetourPage, RetoursPage
from modules.situationpage import SituationPage, SituationsPage
from modules.statistiquesachatspage import StatistiquesAchatsPage
from modules.statistiquesventespage import StatistiquesVentesPage
from modules.statistiquespage import StatistiquesPage
from modules.analyseproduitspage import AnalyseProduitsPage
from modules.gestionprofilspage import GestionProfilsPage
from modules.vendeurpage import VendeurPage
from modules.mouvementstockpage import MouvementStockPage
from modules.utilisateurspage import UtilisateursPage
from modules.journalauditpage import JournalAuditPage
from modules.logindialog import LoginDialog
from modules.changermotdepassedialog import ChangerMotDePasseDialog

from modules.core import *
from api import rbac

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📦 Gestion de Stock — v1.0")
        self.configure(bg=CLR_BG)
        
        # Plein écran par défaut
        # self.attributes('-fullscreen', True)
        self.state('zoomed')  # Pour Windows
        # Liaison de la touche F11 pour basculer le plein écran
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.quit_fullscreen)
        self.bind("<<ProduitsModifies>>", self.on_produits_modifies)
        init_db()
        self.session_ouverte = False
        self.se_reconnecter = False
        self.withdraw()
        if not self._connecter():
            self.destroy()
            return
        self.deiconify()
        self.session_ouverte = True
        self._pages = {}
        self._build()

    def _connecter(self):
        """Écran de connexion bloquant. Retourne True si une session a été
        ouverte (et gère le changement de mot de passe obligatoire, création
        du compte / réinitialisation), False si la fenêtre a été fermée."""
        d = LoginDialog(self)
        self.wait_window(d)
        if d.utilisateur is None:
            return False
        if d.utilisateur.get("doit_changer_mdp"):
            cd = ChangerMotDePasseDialog(self, d.utilisateur, obligatoire=True)
            self.wait_window(cd)
        rbac.set_utilisateur_connecte(d.utilisateur)
        return True

    def se_deconnecter(self):
        if not messagebox.askyesno("Déconnexion", "Se déconnecter ?\n"
                                    "L'application va se fermer et redemander la connexion."):
            return
        conn = get_conn()
        try:
            session = rbac.get_utilisateur_connecte()
            rbac.ajouter_audit(conn, "DECONNEXION",
                               utilisateur=session["nom_complet"] if session else None)
            conn.commit()
        finally:
            conn.close()
        rbac.set_utilisateur_connecte(None)
        self.se_reconnecter = True
        self.destroy()

    def changer_mon_mot_de_passe(self):
        session = rbac.get_utilisateur_connecte()
        if not session:
            return
        d = ChangerMotDePasseDialog(self, session, obligatoire=False)
        self.wait_window(d)
    def on_produits_modifies(self, event):
        """✅ Relayé l'événement à toutes les fenêtres Toplevel ouvertes"""
        print("📢 Événement ProduitsModifies reçu dans App !")  # Pour debug
        
        # Notifier toutes les pages ouvertes
        for page in self._pages.values():
            if hasattr(page, 'refresh_produits'):
                try:
                    page.refresh_produits()
                except Exception as e:
                    print(f"Erreur refresh page: {e}")
        
        # Notifier toutes les fenêtres Toplevel ouvertes (BonDialog, BonEditDialog, etc.)
        for fenetre in self.winfo_children():
            if isinstance(fenetre, tk.Toplevel):
                if hasattr(fenetre, 'refresh_produits'):
                    try:
                        fenetre.refresh_produits()
                    except Exception as e:
                        print(f"Erreur refresh Toplevel: {e}")
                else:
                    # Chercher récursivement dans les enfants de la Toplevel
                    self._chercher_refresh_dans_enfants(fenetre)
    
    def _chercher_refresh_dans_enfants(self, widget):
        """Recherche récursivement un widget avec refresh_produits"""
        if hasattr(widget, 'refresh_produits'):
            try:
                widget.refresh_produits()
            except Exception as e:
                print(f"Erreur refresh enfant: {e}")
            return True
        
        if hasattr(widget, 'winfo_children'):
            for enfant in widget.winfo_children():
                if self._chercher_refresh_dans_enfants(enfant):
                    return True
        return False
    def toggle_fullscreen(self, event=None):
        """Basculer entre plein écran et mode fenêtré"""
        self.attributes('-fullscreen', not self.attributes('-fullscreen'))
        if not self.attributes('-fullscreen'):
            self.geometry("1200x720")
            center_window(self, 1200, 720)
    
    def quit_fullscreen(self, event=None):
        """Quitter le plein écran (touche Echap)"""
        if self.attributes('-fullscreen'):
            self.attributes('-fullscreen', False)
            self.geometry("1200x720")
            center_window(self, 1200, 720)

    def _build(self):
        # ✅ SIDEBAR AVEC SCROLL
        self.sidebar = tk.Frame(self, bg=CLR_SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # ✅ CANVAS + SCROLLBAR POUR LA SIDEBAR
        sidebar_canvas = tk.Canvas(self.sidebar, bg=CLR_SIDEBAR, highlightthickness=0, width=220)
        sidebar_scrollbar = tk.Scrollbar(self.sidebar, orient="vertical", command=sidebar_canvas.yview)
        sidebar_inner = tk.Frame(sidebar_canvas, bg=CLR_SIDEBAR)
        
        sidebar_inner.bind(
            "<Configure>",
            lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        )
        sidebar_canvas.create_window((0, 0), window=sidebar_inner, anchor="nw", width=218)
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scrollbar.pack(side="right", fill="y")
        
        # ✅ Raccourci pour la molette de souris dans la sidebar
        def _on_mousewheel_sidebar(event):
            sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        sidebar_canvas.bind("<MouseWheel>", _on_mousewheel_sidebar)
        sidebar_inner.bind("<MouseWheel>", _on_mousewheel_sidebar)
        
        # ✅ Utiliser sidebar_inner au lieu de sidebar pour le contenu
        logo_frame = tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, pady=20)
        logo_frame.pack(fill="x")
       
        ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=5)

        self.nav_btns = {}
        nav_items = [
            ("🏠", "Tableau de Bord", "dashboard"),
            ("📦", "Produits", "produits"),
            ("📋", "Mouvements Stock", "mouvements_stock"),
            ("💲", "Grille des Prix", "grille_prix"),
            ("👥", "Clients", "clients"),
            ("🎯", "Prospects Vendeurs", "prospects_vendeurs"),
            ("🏭", "Fournisseurs", "fournisseurs"),
            None,
            ("🧾", "Factures", "factures"),
            ("🛒", "Bons d'Achat", "bons_achat"),
            ("🏷️", "Bons de Vente", "bons_vente"),
            None,
            ("💳", "Versements", "versements"),
            None,
            ("↩️", "Retours", "retours"),
            None,
            ("📊", "Situations", "situations"),
            ("📩", "Commandes Portail", "cmd_portail"),

            ("📊", "Statistiques", "statistiques"),
            None,
            ("👔", "Vendeurs", "vendeurs"),
            ("🌐", "Suivi Portail Client", "portail_suivi"),
            ("🏢", "Profils Entreprise", "profils"),
            None,
            ("🔐", "Utilisateurs", "utilisateurs"),
            ("🗂️", "Journal d'audit", "journal_audit"),
        ]

        for item in nav_items:
            if item is None:
                ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=3)
                continue
            icon, label, key = item
            if not rbac.peut_voir_page_courant(key):
                continue
            btn = tk.Button(sidebar_inner, text=f"  {icon}  {label}",
                anchor="w", bg=CLR_SIDEBAR, fg=CLR_MUTED,
                relief="flat", font=("Segoe UI", 8),
                padx=8, pady=4,
                cursor="hand2",
                command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=6, pady=1)
            btn.bind("<Enter>", lambda e,b=btn: b.config(bg=CLR_CARD, fg=CLR_TEXT) if self._active != b else None)
            btn.bind("<Leave>", lambda e,b=btn: b.config(bg=CLR_SIDEBAR, fg=CLR_MUTED) if self._active != b else None)
            self.nav_btns[key] = btn

        # ✅ Compte connecté : rôle, changement de mot de passe, déconnexion
        ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=6)
        session = rbac.get_utilisateur_connecte()
        if session:
            uf = tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, padx=10, pady=6)
            uf.pack(fill="x")
            tk.Label(uf, text=f"👤 {session['nom_complet']}", bg=CLR_SIDEBAR, fg="white",
                     font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(uf, text=rbac.libelle_role(session["role"]), bg=CLR_SIDEBAR, fg=CLR_MUTED,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x")
            tk.Button(uf, text="🔑 Mon mot de passe", command=self.changer_mon_mot_de_passe,
                      bg=CLR_SIDEBAR, fg=CLR_MUTED, relief="flat", font=("Segoe UI", 8),
                      anchor="w", cursor="hand2").pack(fill="x", pady=(4, 0))
            tk.Button(uf, text="🚪 Déconnexion", command=self.se_deconnecter,
                      bg=CLR_SIDEBAR, fg=CLR_RED, relief="flat", font=("Segoe UI", 8, "bold"),
                      anchor="w", cursor="hand2").pack(fill="x", pady=(2, 0))

        # ✅ Ajouter un espace en bas pour le scroll
        tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, height=20).pack()

        self._active = None
        self.main = tk.Frame(self, bg=CLR_BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.show_page("dashboard")

    def show_page(self, key):
        if not rbac.peut_voir_page_courant(key):
            messagebox.showwarning(
                "Accès refusé", "Vous n'avez pas accès à cette section.\nContactez un administrateur.")
            return
        if self._active:
            self._active.config(bg=CLR_SIDEBAR, fg=CLR_MUTED)
        btn = self.nav_btns.get(key)
        if btn:
            btn.config(bg=CLR_ACCENT, fg="white")
            self._active = btn

        for w in self.main.winfo_children():
            w.pack_forget()

        if key not in self._pages:
            if key == "dashboard":
                self._pages[key] = DashboardPage(self.main)
            elif key == "produits":
                self._pages[key] = ProduitPage(self.main)
            elif key == "mouvements_stock":
                self._pages[key] = MouvementStockPage(self.main)
            elif key == "grille_prix":  # AJOUTER CE BLOC
                self._pages[key] = prix_niveaux.GrillePrixPage(self.main)
            elif key == "clients":
                self._pages[key] = TiersPage(self.main, "client")
            elif key == "fournisseurs":
                self._pages[key] = TiersPage(self.main, "fournisseur")
            elif key == "bons_achat":
                self._pages[key] = BonAchatPage(self.main)
            elif key == "bons_vente":
                self._pages[key] = BonVentePage(self.main)
            elif key == "factures":
                self._pages[key] = FacturePage(self.main)
            elif key == "versements":
                self._pages[key] = VersementsPage(self.main)
            elif key == "vers_clients":
                self._pages[key] = VersementPage(self.main, "general")
            elif key == "vers_fourn":
                self._pages[key] = VersementPage(self.main, "fournisseur")
            elif key == "retours":
                self._pages[key] = RetoursPage(self.main)
            elif key == "retours_vente":
                self._pages[key] = RetourPage(self.main, "vente")
            elif key == "retours_achat":
                self._pages[key] = RetourPage(self.main, "achat")
            elif key == "sit_clients":
                self._pages[key] = SituationPage(self.main, "client")
            elif key == "sit_fourn":
                self._pages[key] = SituationPage(self.main, "fournisseur")
            elif key == "situations":
                self._pages[key] = SituationsPage(self.main)
            elif key == "profils":
                self._pages[key] = GestionProfilsPage(self.main)
            elif key == "vendeurs":
                self._pages[key] = VendeurPage(self.main)
            elif key == "portail_suivi":
                self._pages[key] = PortailSuiviPage(self.main)    
            elif key == "cmd_portail":
                self._pages[key] = CommandesClientsPage(self.main)

            elif key == "stats_ventes":
                self._pages[key] = StatistiquesVentesPage(self.main)    
            elif key == "stats_achats":  # <-- NOUVEAU
                self._pages[key] = StatistiquesAchatsPage(self.main)
            elif key == "statistiques":
                self._pages[key] = StatistiquesPage(self.main)
            elif key == "analyse_produits":
                self._pages[key] = AnalyseProduitsPage(self.main)    
            elif key == "prospects_vendeurs":                   
                self._pages[key] = ProspectsPage(self.main)    
            elif key == "utilisateurs":
                self._pages[key] = UtilisateursPage(self.main)
            elif key == "journal_audit":
                self._pages[key] = JournalAuditPage(self.main)
        page = self._pages[key]
        page.pack(fill="both", expand=True)
        if hasattr(page, "refresh"):
            page.refresh()

    def ouvrir_mouvements_produit(self, produit_id):
        """Affiche le journal des mouvements de stock filtré sur un produit
        (raccourci utilisé par la page Produits)."""
        if not rbac.peut_voir_page_courant("mouvements_stock"):
            messagebox.showwarning(
                "Accès refusé", "Vous n'avez pas accès aux mouvements de stock.")
            return
        self.show_page("mouvements_stock")
        self._pages["mouvements_stock"].filtrer_produit(produit_id)