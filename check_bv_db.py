import sqlite3
from api.db import DB_PATH  # base unique : api/gestion_stock.db
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('PRAGMA table_info(bons_vente)')
print('bons_vente cols:', [col[1] for col in c.fetchall()])
c.execute('PRAGMA table_info(lignes_vente)')
print('lignes_vente cols:', [col[1] for col in c.fetchall()])
conn.close()
