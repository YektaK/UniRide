from academic_benchmark.tsplib_manager import is_db_populated, get_all_problems, cmd_status
import sqlite3

print("Is DB populated?", is_db_populated())
try:
    problems = get_all_problems()
    print("Total problems:", len(problems))
except Exception as e:
    print("Error:", e)

