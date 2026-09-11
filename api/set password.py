"""
Utilitaire pour le personnel : active l'accès portail et définit/réinitialise
le mot de passe d'un client.

Usage (depuis la racine du projet) :
    python -m api.set_password CLT-0001
    python -m api.set_password CLT-0001 --password "MonMotDePasse123"
    python -m api.set_password CLT-0001 --disable   (désactive l'accès portail)
"""
import argparse
import getpass
import sys

from api.db import get_conn, run_api_migrations
from api.security import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code_client", help="Code du client (colonne 'code' de la table clients)")
    parser.add_argument("--password", help="Mot de passe (sinon demandé de façon masquée)")
    parser.add_argument("--disable", action="store_true", help="Désactive l'accès portail pour ce client")
    args = parser.parse_args()

    run_api_migrations()
    conn = get_conn()
    try:
        client = conn.execute("SELECT id, nom FROM clients WHERE code=?", (args.code_client,)).fetchone()
        if client is None:
            print(f"❌ Aucun client trouvé avec le code '{args.code_client}'.")
            sys.exit(1)

        if args.disable:
            conn.execute("UPDATE clients SET portail_actif=0 WHERE id=?", (client["id"],))
            conn.commit()
            print(f"✅ Accès portail désactivé pour {client['nom']} ({args.code_client}).")
            return

        password = args.password or getpass.getpass("Nouveau mot de passe : ")
        if len(password) < 6:
            print("❌ Le mot de passe doit contenir au moins 6 caractères.")
            sys.exit(1)

        conn.execute(
            "UPDATE clients SET password_hash=?, portail_actif=1 WHERE id=?",
            (hash_password(password), client["id"]),
        )
        conn.commit()
        print(f"✅ Mot de passe défini et accès portail activé pour {client['nom']} ({args.code_client}).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()