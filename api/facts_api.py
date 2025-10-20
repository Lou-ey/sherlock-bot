from datetime import datetime
from flask import Flask, jsonify, request
import random
import json
import os

app = Flask(__name__)
FACTS_FILE = "facts.json"
USED_FILE = "used_facts.json"

# --- Ler factos ---
def load_facts():
    if os.path.exists(FACTS_FILE):
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_used_facts():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_used_facts(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

@app.route("/fact", methods=["GET"])
def get_random_fact():
    facts = load_facts()
    used = load_used_facts()

    used_texts = [u["fact"] for u in used]

    available = [f for f in facts if f not in used_texts]

    if not available:
        # Todos os factos foram usados — reiniciar
        used = []
        available = facts
        print("♻️ Todos os factos foram usados — a lista foi reiniciada.")

    fact = random.choice(available)

    day_number = len(used) + 1

    # Registar o a data do facto usado
    use_date = datetime.now().strftime("%d/%m/%Y")
    use_time = datetime.now().strftime("%H:%M")

    used.append({"day": day_number, "fact": fact, "use_date": use_date, "use_time": use_time})
    save_used_facts(used)

    return jsonify({"day": day_number, "fact": fact, "use_date": use_date, "use_time": use_time})

@app.route("/fact/<day_or_date>", methods=["GET"])
def get_fact_by_day_or_date(day_or_date=None):
    used = load_used_facts()

    date_param = request.args.get("date")
    if date_param:
        for entry in used:
            if entry["use_date"] == date_param:
                return jsonify(entry)
        return jsonify({"error": "Fact not found for that day."}), 404

    if day_or_date:
        if day_or_date.isdigit():
            day = int(day_or_date)
            for entry in used:
                if entry.get("day") == day:
                    return jsonify(entry)
            return jsonify({"error": "Fact not found for that day."}), 404
        else:
            # tenta interpretar como data
            try:
                datetime.strptime(day_or_date, "%d-%m-%Y")
                date_search = day_or_date.replace("-", "/")
            except ValueError:
                return jsonify({"error": "Invalid date format. Use DD-MM-YYYY."}), 400

            for entry in used:
                if entry.get("use_date") == date_search:
                    return jsonify(entry)

            return jsonify({"error": f"Fact not found for date {date_search}."}), 404

    return jsonify({"error": "Day or date not provided."}), 400

@app.route("/fact", methods=["POST"])
def add_fact():
    data = request.get_json()
    if not data or "fact" not in data:
        return jsonify({"error": "Missing 'fact' field"}), 400

    facts = load_facts()
    facts.append(data["fact"])

    with open(FACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)

    return jsonify({"message": "Fact added successfully!"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
