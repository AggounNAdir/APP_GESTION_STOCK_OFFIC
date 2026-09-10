import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()
c.execute('PRAGMA table_info(clients)')
cols = [col[1] for col in c.fetchall()]
for col_name in ['email', 'contact', 'plafond_credit']:
    if col_name not in cols:
        c.execute(f'ALTER TABLE clients ADD COLUMN {col_name} TEXT')
        print(f"Colonne {col_name} ajoutée à clients !")
conn.commit()
conn.close()
