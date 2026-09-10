import os

app_file = os.path.join('modules', 'app.py')
with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

page_classes = [
    'DashboardPage', 'ProduitPage', 'TiersPage', 'BonAchatPage', 
    'BonVentePage', 'FacturePage', 'VersementPage', 'RetourPage', 
    'SituationPage', 'StatistiquesAchatsPage', 'StatistiquesVentesPage', 
    'AnalyseProduitsPage', 'GestionProfilsPage'
]

imports = ""
for cls in page_classes:
    mod_name = cls.lower()
    imports += f"from modules.{mod_name} import {cls}\n"

content = imports + "\n" + content
with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("All page imports added to app.py successfully!")
