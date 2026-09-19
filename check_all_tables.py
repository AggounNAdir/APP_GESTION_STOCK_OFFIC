import sqlite3
from api.db import DB_PATH  # base unique : api/gestion_stock.db
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
for table in ['bons_vente', 'lignes_vente']:
    c.execute(f'PRAGMA table_info({table})')
    print(table, [col[1] for col in c.fetchall()])
conn.close()
