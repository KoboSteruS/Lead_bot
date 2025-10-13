import sqlite3

conn = sqlite3.connect('leadbot.db')
cursor = conn.cursor()

print("Таблицы в базе данных:")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for table in tables:
    print(f"  - {table[0]}")

conn.close()



