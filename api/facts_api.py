from datetime import datetime
from flask import Flask, jsonify, request
import sqlite3
import random
import os

app = Flask(__name__)

# Caminho absoluto para evitar problemas com o Systemd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "facts.db")


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
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
    conn.commit()
    conn.close()

init_db()

@app.route("/fact", methods=["GET"])
def get_random_fact():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''SELECT id, fact_text
                 FROM facts
                 WHERE id NOT IN (SELECT fact_id FROM used_facts)''')
    available = c.fetchall()

    if not available:
        c.execute('DELETE FROM used_facts')
        conn.commit()
        c.execute('SELECT id, fact_text FROM facts')
        available = c.fetchall()
        print("♻️ Todos os factos foram usados — a lista foi reiniciada.")

    if not available:
        conn.close()
        return jsonify({"error": "Não há factos na base de dados."}), 404

    chosen = random.choice(available)
    fact_id = chosen['id']
    fact_text = chosen['fact_text']

    now = datetime.now()
    use_date = now.strftime("%d/%m/%Y")
    use_time = now.strftime("%H:%M")

    c.execute('''INSERT INTO used_facts (fact_id, fact_text, use_date, use_time)
                 VALUES (?, ?, ?, ?)''', (fact_id, fact_text, use_date, use_time))
    day = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"day": day, "fact": fact_text, "use_date": use_date, "use_time": use_time})


@app.route("/fact/<day_or_date>", methods=["GET"])
def get_fact_by_day_or_date(day_or_date):
    conn = get_db_connection()
    c = conn.cursor()

    if day_or_date.isdigit():
        c.execute('SELECT * FROM used_facts WHERE day = ?', (int(day_or_date),))
    else:
        # Se for data no formato DD-MM-YYYY
        date_search = day_or_date.replace("-", "/")
        c.execute('SELECT * FROM used_facts WHERE use_date = ? LIMIT 1', (date_search,))

    row = c.fetchone()
    conn.close()

    if row:
        return jsonify(dict(row))
    return jsonify({"error": "Facto não encontrado."}), 404


@app.route("/fact", methods=["POST"])
def add_fact():
    data = request.get_json()
    if not data or "fact" not in data:
        return jsonify({"error": "Falta o campo 'fact'"}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO facts (fact_text) VALUES (?)', (data['fact'],))
        conn.commit()
        conn.close()
        return jsonify({"message": "Facto adicionado com sucesso!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Esse facto já existe."}), 409


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)