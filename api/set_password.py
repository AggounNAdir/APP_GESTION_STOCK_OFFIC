"""
Script utilitaire pour créer ou réinitialiser le mot de passe d'un client
et activer son accès au portail client de l'API.

Usage (depuis la racine du projet) :
    python -m api.set_password CLT-0001
    python -m api.set_password CLT-0001 --password "MonMotDePasse123"
    python -m api.set_password CLT-0001 --disable   (désactive l'accès portail)
"""
import argparse
import getpass
import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import get_conn, init_db
from api.security import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code_client", help="Code du client (colonne 'code' de la table clients)")
    parser.add_argument("--password", help="Mot de passe (sinon demandé de façon masquée)")
    parser.add_argument("--disable", action="store_true", help="Désactive l'accès portail pour ce client")
    args = parser.parse_args()

    init_db()
    conn = get_conn()
    try:
        client = conn.execute(
            "SELECT id, code, nom FROM clients WHERE code=?", (args.code_client,)
        ).fetchone()

        if not client:
            print(f"❌ Aucun client trouvé avec le code '{args.code_client}'.")
            sys.exit(1)

        if args.disable:
            conn.execute(
                "UPDATE clients SET portail_actif=0 WHERE id=?", (client["id"],)
            )
            conn.commit()
            print(f"🔒 Accès portail désactivé pour le client {client['code']} ({client['nom']}).")
            return

        password = args.password or getpass.getpass(f"Nouveau mot de passe pour {client['code']} ({client['nom']}) : ")
        if len(password) < 6:
            print("❌ Le mot de passe doit contenir au moins 6 caractères.")
            sys.exit(1)

        conn.execute(
            "UPDATE clients SET password_hash=?, portail_actif=1 WHERE id=?",
            (hash_password(password), client["id"]),
        )
        conn.commit()
        print(f"✅ Mot de passe mis à jour et accès portail activé avec succès pour {client['code']} ({client['nom']}) !")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
