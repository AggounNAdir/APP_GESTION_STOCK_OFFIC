import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()
c.execute('PRAGMA table_info(clients)')
cols = [col[1] for col in c.fetchall()]
print("Colonnes clients:", cols)
if 'code' not in cols:
    c.execute('ALTER TABLE clients ADD COLUMN code TEXT')
    conn.commit()
    print("Colonne code ajoutée !")
conn.close()
