from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import asyncio
from datetime import datetime
from typing import List
import json

# ─── App setup ───
app = FastAPI(title="SafeWatch API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "backend/violations.db"

# ─── WebSocket manager ───
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active:
            try:
                await ws.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ─── DB helper ────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── REST endpoints ────
@app.get("/")
def root():
    return {"status": "SafeWatch API running"}


@app.get("/violations")
def get_violations(limit: int = 50, zone: str = None, violation: str = None):
    conn = get_db()
    query = "SELECT * FROM violations WHERE 1=1"
    params = []

    if zone:
        query += " AND zone = ?"
        params.append(zone)
    if violation:
        query += " AND violation = ?"
        params.append(violation)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/violations/stats")
def get_stats():
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
    unacked = conn.execute("SELECT COUNT(*) FROM violations WHERE acknowledged = 0").fetchone()[0]
    no_hardhat = conn.execute("SELECT COUNT(*) FROM violations WHERE violation = 'No Hardhat'").fetchone()[0]
    no_vest = conn.execute("SELECT COUNT(*) FROM violations WHERE violation = 'No Safety Vest'").fetchone()[0]

    today = datetime.now().date().isoformat()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM violations WHERE DATE(timestamp) = ?", (today,)
    ).fetchone()[0]

    zone_counts = conn.execute(
        "SELECT zone, COUNT(*) as count FROM violations GROUP BY zone"
    ).fetchall()

    hourly = conn.execute(
        """SELECT strftime('%H:00', timestamp) as hour, COUNT(*) as count 
           FROM violations 
           WHERE DATE(timestamp) = ?
           GROUP BY hour ORDER BY hour""",
        (today,)
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "unacknowledged": unacked,
        "no_hardhat": no_hardhat,
        "no_vest": no_vest,
        "today": today_count,
        "by_zone": [dict(r) for r in zone_counts],
        "hourly": [dict(r) for r in hourly]
    }


@app.post("/violations/{violation_id}/acknowledge")
def acknowledge(violation_id: int):
    conn = get_db()
    conn.execute(
        "UPDATE violations SET acknowledged = 1 WHERE id = ?", (violation_id,)
    )
    conn.commit()
    conn.close()
    return {"status": "acknowledged", "id": violation_id}


@app.get("/violations/recent")
def get_recent(since_id: int = 0):
    """Used by dashboard to poll for new violations."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM violations WHERE id > ? ORDER BY timestamp DESC",
        (since_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/zones")
def get_zones():
    conn = get_db()
    zones = conn.execute(
        "SELECT DISTINCT zone FROM violations"
    ).fetchall()
    conn.close()
    return [r[0] for r in zones]


# ─── WebSocket endpoint ────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send existing violations on connect
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM violations ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        conn.close()
        await websocket.send_json({"type": "init", "data": [dict(r) for r in rows]})

        last_id = rows[0]["id"] if rows else 0

        # Poll for new violations every 2 seconds
        while True:
            await asyncio.sleep(2)
            conn = get_db()
            new_rows = conn.execute(
                "SELECT * FROM violations WHERE id > ? ORDER BY timestamp DESC",
                (last_id,)
            ).fetchall()
            conn.close()

            if new_rows:
                last_id = new_rows[0]["id"]
                await websocket.send_json({
                    "type": "new_violations",
                    "data": [dict(r) for r in new_rows]
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── Run ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir="backend")