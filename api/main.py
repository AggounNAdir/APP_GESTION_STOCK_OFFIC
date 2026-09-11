"""
API Portail Client — Application de Gestion de Stock
======================================================
Lancement (depuis la racine du projet) :
    uvicorn api.main:app --host 0.0.0.0 --port 8000

Documentation interactive une fois lancée : http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.db import run_api_migrations
from api.routers import auth, clients, produits, ventes, factures, versements, commandes

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ajoute les colonnes/tables portail (password_hash, commandes_clients, ...)
    # sur la base SQLite existante, sans toucher aux tables métier.
    run_api_migrations()
    yield

app = FastAPI(
    title="API Portail Client — Gestion de Stock",
    description="API permettant au portail client de consulter son compte et de passer des commandes.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Santé"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(produits.router)
app.include_router(ventes.router)
app.include_router(factures.router)
app.include_router(versements.router)
app.include_router(commandes.router)