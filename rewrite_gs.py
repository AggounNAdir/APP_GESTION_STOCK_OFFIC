import os
import glob

# 1. Importer tout depuis core
from modules.core import *

# 2. Importer toutes les classes de fenêtres/pages depuis les modules
from modules.prixspeciauxclientdialog import PrixSpeciauxClientDialog
from modules.datepicker import DatePicker
from modules.dateentry import DateEntry
from modules.statistiquesachatspage import StatistiquesAchatsPage
from modules.statistiquesventespage import StatistiquesVentesPage
from modules.detailventeclientdialog import DetailVenteClientDialog
from modules.facturepage import FacturePage
from modules.facturedialog import FactureDialog
from modules.factureeditdialog import FactureEditDialog
from modules.facturedetaildialog import FactureDetailDialog
from modules.produitpage import ProduitPage
from modules.produitdialog import ProduitDialog
from modules.dashboardpage import DashboardPage
from modules.tierspage import TiersPage
from modules.tiersdialog import TiersDialog
from modules.bonachatpage import BonAchatPage
from modules.bonventepage import BonVentePage
from modules.ventecomptoirdialog import VenteComptoirDialog
from modules.bondialog import BonDialog
from modules.boneditdialog import BonEditDialog
from modules.bondetaildialog import BonDetailDialog
from modules.app import App
from modules.versementpage import VersementPage
from modules.versementdialog import VersementDialog
from modules.versementeditdialog import VersementEditDialog
from modules.versementdetaildialog import VersementDetailDialog
from modules.retourpage import RetourPage
from modules.retourdialog import RetourDialog
from modules.retourdetaildialog import RetourDetailDialog
from modules.retoureditdialog import RetourEditDialog
from modules.situationpage import SituationPage
from modules.gestionprofilspage import GestionProfilsPage
from modules.profildialog import ProfilDialog
from modules.analyseproduitspage import AnalyseProduitsPage

if __name__ == "__main__":
    app = App()
    app.mainloop()
