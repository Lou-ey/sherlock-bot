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

    available = [f for f in facts if f not in used]

    if not available:
        # Todos os factos foram usados — reiniciar
        used = []
        available = facts
        print("♻️ Todos os factos foram usados — a lista foi reiniciada.")

    fact = random.choice(available)
    used.append(fact)
    save_used_facts(used)

    return jsonify({"fact": fact})

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
