from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    code_client: str = Field(..., description="Code client (ex: CLT-0001)")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VendeurLoginRequest(BaseModel):
    code_vendeur: str = Field(..., description="Code vendeur (ex: VND-0001)")
    password: str


class VendeurProfile(BaseModel):
    id: int
    code: str
    nom: str
    tel: Optional[str] = None


class VendeurTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    vendeur: VendeurProfile


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
    facteur_conversion: Optional[float] = 1.0
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
    nom_client: Optional[str] = None      # 👈 AJOUTER CETTE LIGNE
    code_client: Optional[str] = None     # 👈 AJOUTER CETTE LIGNE
    prospect_id: Optional[int] = None     # 👈 AJOUTER CETTE LIGNE


# ---------- Commandes (portail -> validation par le personnel) ----------
class LigneCommandeIn(BaseModel):
    produit_id: int
    quantite: float = Field(..., gt=0)


class CommandeIn(BaseModel):
    lignes: list[LigneCommandeIn] = Field(..., min_length=1)
    observations: Optional[str] = None
    client_id: Optional[int] = None
    vendeur_id: Optional[int] = None

class VersementIn(BaseModel):
  model_config = ConfigDict(
      extra="allow"
  )  # 👈 TRÈS IMPORTANT : autorise tous les champs sans les effacer !

  client_id: Optional[int] = None
  prospect_id: Optional[int] = None
  nom_client: Optional[str] = None
  code_client: Optional[str] = None
  is_prospect: Optional[bool] = False
  montant: float
  mode: Optional[str] = "Espèces"
  reference: Optional[str] = None
  vendeur_id: Optional[int] = None

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


# ---------- Tournée terrain Silwane Androway ----------
class PointageGpsIn(BaseModel):
    """
    Payload tolérant : le portail appelle cet endpoint depuis deux points
    différents (gpsTourneeService.pointerPresenceVisite en snake_case,
    androwaySyncService via la file offline en camelCase), avec des noms de
    champs différents. On accepte les deux variantes et on les réconcilie
    côté serveur plutôt que de faire échouer la requête sur un 422.
    """
    client_id: Optional[int] = None
    clientId: Optional[int] = None
    code_client: Optional[str] = None
    codeClient: Optional[str] = None
    nom_client: Optional[str] = None
    nomClient: Optional[str] = None
    latitude: Optional[float] = None
    lat: Optional[float] = None
    longitude: Optional[float] = None
    lng: Optional[float] = None
    timestamp: Optional[str] = None
    heure: Optional[str] = None
    observations: Optional[str] = None

    def resolved(self) -> dict:
        return {
            "client_id": self.client_id if self.client_id is not None else self.clientId,
            "code_client": self.code_client or self.codeClient,
            "nom_client": self.nom_client or self.nomClient,
            "latitude": self.latitude if self.latitude is not None else self.lat,
            "longitude": self.longitude if self.longitude is not None else self.lng,
            "date_pointage": self.timestamp or self.heure,
            "observations": self.observations,
        }


class PointageOut(BaseModel):
    id: int
    client_id: Optional[int] = None
    code_client: Optional[str] = None
    nom_client: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    date_pointage: Optional[str] = None
    observations: Optional[str] = None


class ProspectIn(BaseModel):
    nom: str
    code: Optional[str] = None
    tel: Optional[str] = None
    adresse: Optional[str] = None
    wilaya: Optional[str] = None
    lat: Optional[float] = None
    latitude: Optional[float] = None
    lng: Optional[float] = None
    longitude: Optional[float] = None
    vendeur_id: Optional[int] = None

    def resolved_lat(self) -> Optional[float]:
        return self.latitude if self.latitude is not None else self.lat

    def resolved_lng(self) -> Optional[float]:
        return self.longitude if self.longitude is not None else self.lng


class ProspectOut(BaseModel):
    id: int
    code: str
    nom: str
    tel: Optional[str] = None
    adresse: Optional[str] = None
    wilaya: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    date_creation: str
    statut: str


class SignatureBLIn(BaseModel):
    bon_vente_id: Optional[int] = None
    numero: Optional[str] = None
    signature: str = Field(..., description="Image de la signature encodée en base64 (PNG/JPEG data URL ou brut)")
    signataire_nom: Optional[str] = None


class SignatureBLOut(BaseModel):
    bon_vente_id: int
    numero: str
    signataire_nom: Optional[str] = None
    date_signature: str
    statut: str