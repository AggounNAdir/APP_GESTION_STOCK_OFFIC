from modules.dashboardpage import DashboardPage
from modules.produitpage import ProduitPage
from modules.tierspage import TiersPage
from modules.bonachatpage import BonAchatPage
from modules.bonventepage import BonVentePage
from modules.facturepage import FacturePage
from modules.versementpage import VersementPage
from modules.retourpage import RetourPage
from modules.situationpage import SituationPage
from modules.statistiquesachatspage import StatistiquesAchatsPage
from modules.statistiquesventespage import StatistiquesVentesPage
from modules.analyseproduitspage import AnalyseProduitsPage
from modules.gestionprofilspage import GestionProfilsPage

from modules.core import *

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
        self._pages = {}
        self._build()
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
        lbl(logo_frame, "📦", 28).pack()
        lbl(logo_frame, "Gestion Stock", 12, True).pack()

        ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=5)

        self.nav_btns = {}
        nav_items = [
            ("🏠", "Tableau de Bord", "dashboard"),
            ("📦", "Produits", "produits"),
            ("💲", "Grille des Prix", "grille_prix"),
            ("👥", "Clients", "clients"),
            ("🏭", "Fournisseurs", "fournisseurs"),
            None,
            ("🧾", "Factures", "factures"),
            ("🛒", "Bons d'Achat", "bons_achat"),
            ("🏷️", "Bons de Vente", "bons_vente"),
            None,
            ("💳", "Versements Clients", "vers_clients"),
            ("💳", "Versements Fournis.", "vers_fourn"),
            None,
            ("↩️", "Retours Vente", "retours_vente"),
            ("↩️", "Retours Achat", "retours_achat"),
            None,
            ("📊", "Situation Clients", "sit_clients"),
            ("📊", "Situation Fournis.", "sit_fourn"),
            ("📊", "Stats Achats", "stats_achats"),
            ("📊", "Stats Ventes", "stats_ventes"),
            ("📊", "Analyse Produits", "analyse_produits"),  # NOUVEAU
            None,
            ("🏢", "Profils Entreprise", "profils")
        ]

        for item in nav_items:
            if item is None:
                ttk.Separator(sidebar_inner, orient="horizontal").pack(fill="x", padx=15, pady=3)
                continue
            icon, label, key = item
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

        # ✅ Ajouter un espace en bas pour le scroll
        tk.Frame(sidebar_inner, bg=CLR_SIDEBAR, height=20).pack()

        self._active = None
        self.main = tk.Frame(self, bg=CLR_BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.show_page("dashboard")

    def show_page(self, key):
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
            elif key == "vers_clients":
                self._pages[key] = VersementPage(self.main, "client")
            elif key == "vers_fourn":
                self._pages[key] = VersementPage(self.main, "fournisseur")
            elif key == "retours_vente":
                self._pages[key] = RetourPage(self.main, "vente")
            elif key == "retours_achat":
                self._pages[key] = RetourPage(self.main, "achat")
            elif key == "sit_clients":
                self._pages[key] = SituationPage(self.main, "client")
            elif key == "sit_fourn":
                self._pages[key] = SituationPage(self.main, "fournisseur")
            elif key == "profils":
                self._pages[key] = GestionProfilsPage(self.main)
            elif key == "stats_ventes":
                self._pages[key] = StatistiquesVentesPage(self.main)    
            elif key == "stats_achats":  # <-- NOUVEAU
                self._pages[key] = StatistiquesAchatsPage(self.main)
            elif key == "analyse_produits":
                self._pages[key] = AnalyseProduitsPage(self.main)    
        page = self._pages[key]
        page.pack(fill="both", expand=True)
        if hasattr(page, "refresh"):
            page.refresh()


