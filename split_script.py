import os
import re

with open('gestion_stock.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

class_positions = []
for i, line in enumerate(lines):
    if line.startswith('class '):
        name = line.split()[1].split('(')[0]
        class_positions.append((i, name))

class_positions.append((len(lines), 'EOF'))
os.makedirs('modules', exist_ok=True)
for idx in range(len(class_positions)-1):
    start, name = class_positions[idx]
    end, next_name = class_positions[idx+1]
    filename = os.path.join('modules', f'{name.lower()}.py')
    print(f'Writing {filename} (lines {start} to {end})')
    with open(filename, 'w', encoding='utf-8') as out:
        out.writelines(lines[start:end])
print("Modules generated successfully!")
