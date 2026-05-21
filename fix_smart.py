with open("academic_benchmark/smart_benchmark.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("if _PROJECT_ROOT not in sys.path:\n    \nfrom", "from")
with open("academic_benchmark/smart_benchmark.py", "w", encoding="utf-8") as f:
    f.write(text)
