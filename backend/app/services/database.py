import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "milktrix.db")

def init_db():
    """Initializes the SQLite database and creates the runs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            vcm REAL,
            revenue REAL,
            production_cost REAL,
            transport_cost REAL,
            status TEXT,
            inputs TEXT,
            results TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_run(vcm: float, revenue: float, prod_cost: float, trans_cost: float, status: str, inputs: Dict[str, Any], results: Dict[str, Any]) -> int:
    """Saves an optimization run and returns its database ID."""
    init_db()  # Ensure table exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO runs (timestamp, vcm, revenue, production_cost, transport_cost, status, inputs, results)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        vcm,
        revenue,
        prod_cost,
        trans_cost,
        status,
        json.dumps(inputs),
        json.dumps(results)
    ))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def get_runs_history() -> List[Dict[str, Any]]:
    """Retrieves all past optimization runs metadata."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, vcm, revenue, status FROM runs ORDER BY id DESC")
    rows = cursor.fetchall()
    
    runs = []
    for r in rows:
        runs.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "vcm": r["vcm"],
            "revenue": r["revenue"],
            "status": r["status"]
        })
    conn.close()
    return runs

def get_run_details(run_id: int) -> Dict[str, Any]:
    """Retrieves full details of a specific optimization run."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "vcm": row["vcm"],
        "revenue": row["revenue"],
        "production_cost": row["production_cost"],
        "transport_cost": row["transport_cost"],
        "status": row["status"],
        "inputs": json.loads(row["inputs"]),
        "results": json.loads(row["results"])
    }
