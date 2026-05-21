import re

with open("academic_benchmark/master_numba_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "if os.path.isdir(_ab_dir):",
    "_ab_dir = os.path.join(_ENGINE_DIR, 'bildiri2026')\n    if os.path.isdir(_ab_dir):"
)

with open("academic_benchmark/master_numba_engine.py", "w", encoding="utf-8") as f:
    f.write(text)
