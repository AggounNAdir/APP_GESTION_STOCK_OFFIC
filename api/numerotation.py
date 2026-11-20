def prochain_numero(conn, table: str, prefixe: str, colonne: str = "numero") -> str:
    """Prochain numéro 'PREFIXE0001'. Prend le verrou d'écriture avant de lire le MAX,
    pour que deux requêtes simultanées ne reçoivent jamais le même numéro."""
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    row = conn.execute(
        f"SELECT MAX({colonne}) FROM {table} WHERE {colonne} LIKE ?", (prefixe + "%",)
    ).fetchone()
    dernier = row[0]
    try:
        suivant = int(str(dernier)[-4:]) + 1 if dernier else 1
    except ValueError:
        suivant = 1
    return f"{prefixe}{suivant:04d}"