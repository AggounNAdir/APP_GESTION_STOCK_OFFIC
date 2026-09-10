import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()
for table in ['bons_vente', 'lignes_vente']:
    c.execute(f'PRAGMA table_info({table})')
    print(table, [col[1] for col in c.fetchall()])
conn.close()
