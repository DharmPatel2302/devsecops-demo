"""
Intentionally vulnerable demo app for a DevSecOps CI/CD talk.
DO NOT deploy this anywhere real. It exists to be caught by scanners.
"""
from flask import Flask, request
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)")
    conn.execute("INSERT INTO users (username, role) SELECT 'admin', 'admin' WHERE NOT EXISTS (SELECT 1 FROM users)")
    conn.commit()
    return conn


@app.route("/")
def home():
    return "DevSecOps demo app is running. Try /user?name=admin"


# --- INTENTIONAL VULNERABILITY: SQL Injection (CWE-89) ---
# Semgrep should flag this during the SAST step of the pipeline.
@app.route("/user")
def get_user():
    name = request.args.get("name", "")
    conn = get_db()
    query = "SELECT id, username, role FROM users WHERE username = ?"
    cursor = conn.execute(query, (name,))
    rows = cursor.fetchall()
    return {"results": rows}


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
