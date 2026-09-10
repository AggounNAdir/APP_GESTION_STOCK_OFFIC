import os

with open('gestion_stock.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class PrixSpeciauxClientDialog')
import_part = text[:idx]

with open(os.path.join('modules', 'core.py'), 'w', encoding='utf-8') as out:
    out.write(import_part)

print("modules/core.py created successfully!")
