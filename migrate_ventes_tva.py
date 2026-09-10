import sqlite3
conn = sqlite3.connect('gestion_stock.db')
c = conn.cursor()

# 1. Ajouter les colonnes manquantes dans bons_vente
c.execute("PRAGMA table_info(bons_vente)")
bv_cols = [col[1] for col in c.fetchall()]
for col_def in [
    ("total_ht", "REAL DEFAULT 0"),
    ("tva_total", "REAL DEFAULT 0"),
    ("total_ttc", "REAL DEFAULT 0")
]:
    if col_def[0] not in bv_cols:
        c.execute(f"ALTER TABLE bons_vente ADD COLUMN {col_def[0]} {col_def[1]}")
        print(f"✅ Colonne {col_def[0]} ajoutée à bons_vente")

# 2. Ajouter les colonnes manquantes dans lignes_vente
c.execute("PRAGMA table_info(lignes_vente)")
lv_cols = [col[1] for col in c.fetchall()]
for col_def in [
    ("total_ht", "REAL DEFAULT 0"),
    ("tva_taux", "REAL DEFAULT 0"),
    ("total_tva", "REAL DEFAULT 0"),
    ("total_ttc", "REAL DEFAULT 0")
]:
    if col_def[0] not in lv_cols:
        c.execute(f"ALTER TABLE lignes_vente ADD COLUMN {col_def[0]} {col_def[1]}")
        print(f"✅ Colonne {col_def[0]} ajoutée à lignes_vente")

conn.commit()
conn.close()
print("Migration tables ventes (HT, TVA, TTC) terminée avec succès !")
