import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()
c.execute('PRAGMA table_info(bons_vente)')
print('bons_vente cols:', [col[1] for col in c.fetchall()])
c.execute('PRAGMA table_info(lignes_vente)')
print('lignes_vente cols:', [col[1] for col in c.fetchall()])
conn.close()
