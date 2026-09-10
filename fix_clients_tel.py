import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()
c.execute('PRAGMA table_info(clients)')
cols = [col[1] for col in c.fetchall()]
print("Clients cols:", cols)
if 'tel' not in cols:
    c.execute('ALTER TABLE clients ADD COLUMN tel TEXT')
    conn.commit()
    print("Colonne tel ajoutée à clients !")
conn.close()
