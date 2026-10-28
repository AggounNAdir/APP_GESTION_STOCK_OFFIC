from api import rbac
from modules.core import *
from modules.analyseproduitspage import AnalyseProduitsPage
from modules.statistiquesachatspage import StatistiquesAchatsPage
from modules.statistiquesventespage import StatistiquesVentesPage


class StatistiquesPage(tk.Frame):
    """Page unifiée des statistiques et de l'analyse des produits."""

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.pages = {}
        self.boutons = {}
        self.contenu = tk.Frame(self, bg=CLR_BG)

        choix = tk.Frame(self, bg=CLR_BG)
        choix.pack(fill="x", padx=20, pady=(16, 4))
        self.contenu.pack(fill="both", expand=True)

        types_autorises = []
        if rbac.peut_voir_page_courant("stats_achats"):
            types_autorises.append(("achats", "Stats Achats"))
        if rbac.peut_voir_page_courant("stats_ventes"):
            types_autorises.append(("ventes", "Stats Ventes"))
        if rbac.peut_voir_page_courant("analyse_produits"):
            types_autorises.append(("analyse", "Analyse Produits"))

        for stats_type, titre in types_autorises:
            bouton = tk.Button(
                choix, text=titre,
                command=lambda type_=stats_type: self.afficher(type_),
                relief="flat", font=("Segoe UI", 9, "bold"),
                padx=14, pady=7, cursor="hand2",
            )
            bouton.pack(side="left", padx=(0, 6))
            self.boutons[stats_type] = bouton

        if types_autorises:
            self.afficher(types_autorises[0][0])

    def afficher(self, stats_type):
        for page in self.pages.values():
            page.pack_forget()

        if stats_type not in self.pages:
            page_classes = {
                "achats": StatistiquesAchatsPage,
                "ventes": StatistiquesVentesPage,
                "analyse": AnalyseProduitsPage,
            }
            page_class = page_classes[stats_type]
            self.pages[stats_type] = page_class(self.contenu)
        elif hasattr(self.pages[stats_type], "refresh"):
            self.pages[stats_type].refresh()

        self.pages[stats_type].pack(fill="both", expand=True)

        for type_, bouton in self.boutons.items():
            actif = type_ == stats_type
            bouton.configure(
                bg=CLR_ACCENT if actif else CLR_CARD,
                fg="white" if actif else CLR_MUTED,
            )