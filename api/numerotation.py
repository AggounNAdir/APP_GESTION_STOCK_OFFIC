def prochain_numero(conn, table: str, prefixe: str) -> str:
    """Prochain numéro 'PREFIXE0001'. À appeler APRÈS BEGIN IMMEDIATE."""
    conn.execute("BEGIN IMMEDIATE")  # verrou d'écriture : plus de doublon concurrent
    row = conn.execute(
        f"SELECT MAX(numero) FROM {table} WHERE numero LIKE ?", (prefixe + "%",)
    ).fetchone()
    dernier = row[0]
    suivant = int(dernier[-4:]) + 1 if dernier else 1
    return f"{prefixe}{suivant:04d}"