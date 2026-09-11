from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    code_client: str = Field(..., description="Code client (ex: CLT-0001)")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Client ----------
class ClientProfile(BaseModel):
    id: int
    code: str
    nom: str
    adresse: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    solde: float
    niveau_prix: Optional[str] = None


# ---------- Produits ----------
class ProduitCatalogue(BaseModel):
    id: int
    code: str
    designation: str
    unite: str
    prix_unitaire: float  # prix déjà résolu pour CE client
    stock_actuel: float
    tva: float


# ---------- Ventes / Factures / Versements (historique) ----------
class LigneVente(BaseModel):
    produit_id: int
    designation: str
    quantite: float
    prix_unitaire: float
    total: float


class BonVente(BaseModel):
    id: int
    numero: str
    date_bon: str
    total: float
    statut: str
    lignes: list[LigneVente] = []


class Facture(BaseModel):
    id: int
    numero: str
    date_facture: str
    total_ht: float
    tva: float
    total_ttc: float
    statut: str
    date_echeance: Optional[str] = None


class Versement(BaseModel):
    id: int
    numero: str
    date_vers: str
    montant: float
    mode: str
    reference: Optional[str] = None


# ---------- Commandes (portail -> validation par le personnel) ----------
class LigneCommandeIn(BaseModel):
    produit_id: int
    quantite: float = Field(..., gt=0)


class CommandeIn(BaseModel):
    lignes: list[LigneCommandeIn] = Field(..., min_length=1)
    observations: Optional[str] = None


class LigneCommandeOut(BaseModel):
    produit_id: int
    designation: str
    quantite: float
    prix_unitaire_estime: float
    total_estime: float


class CommandeOut(BaseModel):
    id: int
    numero: str
    date_commande: str
    statut: str
    total_estime: float
    observations: Optional[str] = None
    bon_vente_id: Optional[int] = None
    lignes: list[LigneCommandeOut] = []