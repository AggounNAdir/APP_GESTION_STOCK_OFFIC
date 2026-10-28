from api import rbac
from modules.core import *
from modules.versementpage import VersementPage


class VersementsPage(tk.Frame):
    """Page unifiée avec un sélecteur entre versements clients et fournisseurs."""

    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.pages = {}
        self.boutons = {}
        self.contenu = tk.Frame(self, bg=CLR_BG)

        choix = tk.Frame(self, bg=CLR_BG)
        choix.pack(fill="x", padx=20, pady=(16, 4))
        self.contenu.pack(fill="both", expand=True)

        types_autorises = []
        if rbac.peut_voir_page_courant("vers_clients"):
            types_autorises.append(("client", "Versements Clients"))
        if rbac.peut_voir_page_courant("vers_fourn"):
            types_autorises.append(("fournisseur", "Versements Fournisseurs"))

        for vers_type, titre in types_autorises:
            bouton = tk.Button(
                choix, text=titre,
                command=lambda type_=vers_type: self.afficher(type_),
                relief="flat", font=("Segoe UI", 9, "bold"),
                padx=14, pady=7, cursor="hand2",
            )
            bouton.pack(side="left", padx=(0, 6))
            self.boutons[vers_type] = bouton

        if types_autorises:
            self.afficher(types_autorises[0][0])

    def afficher(self, vers_type):
        for page in self.pages.values():
            page.pack_forget()

        if vers_type not in self.pages:
            mode = "general" if vers_type == "client" else "fournisseur"
            self.pages[vers_type] = VersementPage(self.contenu, mode)
        else:
            self.pages[vers_type].refresh()

        self.pages[vers_type].pack(fill="both", expand=True)

        for type_, bouton in self.boutons.items():
            actif = type_ == vers_type
            bouton.configure(
                bg=CLR_ACCENT if actif else CLR_CARD,
                fg="white" if actif else CLR_MUTED,
            )