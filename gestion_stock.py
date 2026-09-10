"""
╔════════════════════════════════════════════════════════════════════════════════╗
║        APPLICATION DE GESTION DE STOCK — GESTION_STOCK (CLASSE D'ENTITÉ)        ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ Ce fichier était un monolithe de plus de 14 000 lignes. Il est désormais une    ║
║ CLASSE D'ENTITÉ (GestionStock) appuyée sur le package `modules/` :             ║
║                                                                                 ║
║   • modules/core.py            → constantes, styles, utilitaires, BDD, PMP      ║
║   • modules/stock_service.py   → logique métier (validation ventes, PMP, ...)   ║
║   • modules/app.py             → fenêtre principale (App)                       ║
║   • modules/*page*.py          → pages de l'interface                           ║
║   • modules/*dialog*.py        → dialogues de l'interface                       ║
║                                                                                 ║
║ Ce fichier ré-exporte l'API historique (rétro-compatibilité avec les scripts    ║
║ existants : `from gestion_stock import get_conn, get_profil_by_type, ...`) et   ║
║ définit l'entité GestionStock qui orchestre l'application.                      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys

# Garde le dossier du script dans le path (nécessaire pour les imports modules.*)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════ SERVICES & UTILITAIRES (modules/core.py) ══════════════════════
from modules.core import *  # noqa: F401,F403  ré-export global pour rétro-compatibilité
from modules.core import (  # noqa: F401  liste explicite (clarté / IDE)
    safe_float,
    setup_logging,
    get_db_path,
    center_window,
    _darken,
    format_montant,
    style_btn,
    lbl,
    entry,
    combo,
    make_tree,
    valider_date,
    parse_decimal,
    normalize_barcode_input,
    next_numero,
    next_numero_tiers,
    generer_code_sequentiel,
    generer_code_aleatoire,
    generer_code_unique,
    export_to_csv,
    export_to_html,
    print_preview,
    get_profil_by_type,
    get_active_profil,
    get_bon_type,
    init_db,
    get_conn,
    calculer_pmp,
    recalculer_cout_stock_apres_sortie,
    entree_stock_annulation_vente,
    recalculer_pmp_apres_sortie_complete,
    inverser_stock_achat,
    DB_PATH,
    LOG_FILE,
    CLR_BG,
    CLR_SIDEBAR,
    CLR_CARD,
    CLR_ACCENT,
    CLR_GREEN,
    CLR_RED,
    CLR_ORANGE,
    CLR_TEXT,
    CLR_MUTED,
    CLR_INPUT,
    CLR_BORDER,
    CLR_PURPLE,
)

# Dépendances ré-exportées (utilisées par certains scripts externes)
import html_renderer as hr  # noqa: F401
import prix_niveaux  # noqa: F401

# ══════════════════════ CLASSES D'INTERFACE (package modules/) ══════════════════════
from modules.app import App  # noqa: F401
from modules.analyseproduitspage import AnalyseProduitsPage
from modules.bonachatpage import BonAchatPage
from modules.bondetaildialog import BonDetailDialog
from modules.bondialog import BonDialog
from modules.boneditdialog import BonEditDialog
from modules.bonventepage import BonVentePage
from modules.dashboardpage import DashboardPage
from modules.dateentry import DateEntry
from modules.datepicker import DatePicker
from modules.detailventeclientdialog import DetailVenteClientDialog
from modules.facturedetaildialog import FactureDetailDialog
from modules.facturedialog import FactureDialog
from modules.factureeditdialog import FactureEditDialog
from modules.facturepage import FacturePage
from modules.gestionprofilspage import GestionProfilsPage
from modules.prixspeciauxclientdialog import PrixSpeciauxClientDialog
from modules.produitdialog import ProduitDialog
from modules.produitpage import ProduitPage
from modules.profildialog import ProfilDialog
from modules.retourdetaildialog import RetourDetailDialog
from modules.retourdialog import RetourDialog
from modules.retoureditdialog import RetourEditDialog
from modules.retourpage import RetourPage
from modules.situationpage import SituationPage
from modules.statistiquesachatspage import StatistiquesAchatsPage
from modules.statistiquesventespage import StatistiquesVentesPage
from modules.tiersdialog import TiersDialog
from modules.tierspage import TiersPage
from modules.ventecomptoirdialog import VenteComptoirDialog
from modules.versementdetaildialog import VersementDetailDialog
from modules.versementdialog import VersementDialog
from modules.versementeditdialog import VersementEditDialog
from modules.versementpage import VersementPage

__version__ = "1.0.0"


# ══════════════════════ CLASSE D'ENTITÉ ══════════════════════


class GestionStock:
    """
    Classe d'entité de l'application Gestion de Stock.

    Elle orchestre l'application en déléguant aux modules du package
    `modules/` (interface graphique, services métier, accès aux données)
    au lieu de tout contenir dans ce fichier.

    Exemple :
        gs = GestionStock()
        gs.initialiser()               # initialise la base de données
        stats = gs.statistiques()      # compteurs principaux
        produits = gs.liste_produits() # entités produits
        gs.lancer()                    # démarre l'interface graphique
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.version = __version__
        self._app = None

    # ─── Accès aux données (délégation à modules.core) ──────────────────────────
    @classmethod
    def connexion(cls):
        """Ouvre une connexion SQLite configurée (modules.core.get_conn)."""
        return get_conn()

    def initialiser(self):
        """
        Initialise les tables de la base de données (idempotent).
        Délègue à modules.core.init_db.
        """
        return init_db()

    # ─── Interface graphique (délégation à modules.app.App) ─────────────────────
    def creer_application(self):
        """Crée la fenêtre principale via modules.app.App (sans la lancer)."""
        if self._app is None:
            self._app = App()
        return self._app

    def lancer(self, avec_mainloop=True):
        """Crée et affiche l'application complète. Retourne l'instance App."""
        app = self.creer_application()
        if avec_mainloop:
            app.mainloop()
        return app

    # ─── Lecture des statistiques ───────────────────────────────────────────────
    def statistiques(self):
        """Retourne les compteurs principaux (produits, tiers, documents...)."""
        conn = get_conn()
        try:
            def compte(table):
                try:
                    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except Exception:
                    return 0

            return {
                "produits": compte("produits"),
                "clients": compte("clients"),
                "fournisseurs": compte("fournisseurs"),
                "bons_vente": compte("bons_vente"),
                "bons_achat": compte("bons_achat"),
                "factures": compte("factures"),
                "retours": compte("retours"),
                "versements": compte("versements_clients") + compte("versements_fournisseurs"),
            }
        finally:
            conn.close()

    # ─── Lecture des entités ────────────────────────────────────────────────────
    def liste_produits(self, actif=True):
        """Retourne la liste des produits (dict) triée par désignation."""
        conn = get_conn()
        try:
            if actif is None:
                rows = conn.execute(
                    "SELECT * FROM produits ORDER BY designation"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM produits WHERE actif=? ORDER BY designation",
                    (1 if actif else 0,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def liste_clients(self):
        """Retourne la liste des clients (dict) triée par nom."""
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def liste_fournisseurs(self):
        """Retourne la liste des fournisseurs (dict) triée par nom."""
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM fournisseurs ORDER BY nom").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ─── Opérations métier (délégation aux modules) ─────────────────────────────
    @staticmethod
    def calculer_pmp(conn, produit_id, nouvelle_quantite, nouveau_prix_achat, **options):
        """
        Calcule le nouveau PMP et coût de stock.
        Délègue à modules.core.calculer_pmp.
        """
        return calculer_pmp(
            conn, produit_id, nouvelle_quantite, nouveau_prix_achat, **options
        )

    @staticmethod
    def valider_vente(client_id, total, lignes_panier, montant_recu=0):
        """
        Valide une vente complète : contrôle des stocks, création du bon de
        vente, des lignes et mise à jour du solde client.
        Délègue à modules.stock_service.valider_transaction_vente.
        Retourne (True, numero) ou (False, message_erreur).
        """
        from modules.stock_service import valider_transaction_vente
        return valider_transaction_vente(client_id, total, lignes_panier, montant_recu)

    @staticmethod
    def profil(type_document):
        """Retourne le profil d'impression pour un type de document."""
        return get_profil_by_type(type_document)

    def __repr__(self):
        return f"<GestionStock version={self.version} db={self.db_path!r}>"


# ══════════════════════ POINT D'ENTRÉE ══════════════════════
if __name__ == "__main__":
    gestion = GestionStock()
    gestion.initialiser()
    gestion.lancer()