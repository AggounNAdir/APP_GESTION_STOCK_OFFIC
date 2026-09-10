import os

for fname in os.listdir('modules'):
    if fname.endswith('.py') and fname != 'core.py':
        fpath = os.path.join('modules', fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write('from modules.core import *\n\n' + content)

print("All modules updated with core imports!")
