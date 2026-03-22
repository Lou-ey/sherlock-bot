import json
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACTS_JSON = os.path.join(BASE_DIR, "facts.json")
USED_JSON = os.path.join(BASE_DIR, "used_facts.json")
DB_FILE = os.path.join(BASE_DIR, "facts.db")


def migrate():
    if not os.path.exists(FACTS_JSON):
        print("❌ File facts.json not found. Please ensure it exists in the api/ directory.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS facts
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     fact_text
                     TEXT
                     UNIQUE
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS used_facts
                 (
                     day
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     fact_id
                     INTEGER,
                     fact_text
                     TEXT,
                     use_date
                     TEXT,
                     use_time
                     TEXT
                 )''')

    with open(FACTS_JSON, "r", encoding="utf-8") as f:
        all_facts = json.load(f)

    print(f"📥 Importing {len(all_facts)} facts into the database...")
    for fact in all_facts:
        try:
            c.execute('INSERT INTO facts (fact_text) VALUES (?)', (fact,))
        except sqlite3.IntegrityError:
            pass  # Ignore duplicates

    if os.path.exists(USED_JSON):
        with open(USED_JSON, "r", encoding="utf-8") as f:
            used_data = json.load(f)

        print(f"📥 Restauring history of {len(used_data)} days...")
        for entry in used_data:
            c.execute('SELECT id FROM facts WHERE fact_text = ?', (entry['fact'],))
            res = c.fetchone()
            fact_id = res[0] if res else None

            c.execute('''INSERT INTO used_facts (day, fact_id, fact_text, use_date, use_time)
                         VALUES (?, ?, ?, ?, ?)''',
                      (entry['day'], fact_id, entry['fact'], entry['use_date'], entry['use_time']))

    conn.commit()
    conn.close()
    print("✅ Migration concluded successfully!")


if __name__ == "__main__":
    migrate()