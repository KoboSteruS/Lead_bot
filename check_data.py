import sqlite3

conn = sqlite3.connect('leadbot.db')
cursor = conn.cursor()

print("=== ЛИД-МАГНИТЫ ===")
magnets = cursor.execute("SELECT name, type, is_active FROM lead_magnets").fetchall()
for m in magnets:
    print(f"  - {m[0]} ({m[1]}) - {'активен' if m[2] else 'неактивен'}")

print("\n=== ТРИПВАЙЕРЫ ===")
products = cursor.execute("SELECT name, type, price, currency FROM products").fetchall()
for p in products:
    print(f"  - {p[0]} ({p[1]}) - {p[2]/100} {p[3]}")

print("\n=== ОФФЕРЫ ===")
offers = cursor.execute("SELECT name, is_active FROM product_offers").fetchall()
for o in offers:
    print(f"  - {o[0]} - {'активен' if o[1] else 'неактивен'}")

print("\n=== СЦЕНАРИИ ПРОГРЕВА ===")
scenarios = cursor.execute("SELECT name, is_active FROM warmup_scenarios").fetchall()
for s in scenarios:
    print(f"  - {s[0]} - {'активен' if s[1] else 'неактивен'}")

print("\n=== СООБЩЕНИЯ ПРОГРЕВА ===")
messages = cursor.execute("SELECT title, message_type, delay_hours FROM warmup_messages ORDER BY \"order\"").fetchall()
for i, msg in enumerate(messages, 1):
    print(f"  {i}. {msg[0]} ({msg[1]}) - через {msg[2]}ч")

conn.close()



