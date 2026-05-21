import os
import glob
import re

patterns = [
    re.compile(r'import sys\s+import os\s+sys\.path\.insert\(0,\s*os\.path\.abspath\([^)]+\)\)\n?', re.MULTILINE),
    re.compile(r'_ENGINE_DIR = os\.path\.dirname\(.*?\)\n_PROJECT_ROOT = .*?\nif _PROJECT_ROOT not in sys\.path:\n\s+sys\.path\.insert\(0, _PROJECT_ROOT\)\n?', re.MULTILINE | re.DOTALL),
    re.compile(r'import sys\nimport os\n\n# Proje kök dizinini Python path.*?\n_PROJECT_ROOT = .*?\nif _PROJECT_ROOT not in sys\.path:\n\s+sys\.path\.insert\(0, _PROJECT_ROOT\)\n?', re.MULTILINE | re.DOTALL)
]

def clean_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for p in patterns:
        content = p.sub('', content)
        
    # Extra cleanup for scattered pieces
    content = re.sub(r'sys\.path\.insert\(0, _PROJECT_ROOT\)\n?', '', content)
    content = re.sub(r'sys\.path\.append\(_PROJECT_ROOT\)\n?', '', content)
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

for filename in glob.iglob('academic_benchmark/**/*.py', recursive=True):
    clean_file(filename)

# Also clean optimizer_api/faz0_interactive.py
clean_file('optimizer_api/faz0_interactive.py')
