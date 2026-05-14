from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database as db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats")
async def stats():
    cleanups = db.get_cleanups()
    spots = db.get_trash_spots()
    leaders = db.get_leaderboard(limit=1000)
    total_kg = sum(c[8] for c in cleanups)
    return {
        "total_kg": total_kg,
        "total_cleanups": len(cleanups),
        "total_spots": len(spots),
        "total_volunteers": len(leaders)
    }

@app.get("/api/cleanups")
async def api_cleanups():
    rows = db.get_cleanups()
    return [{"lat": r[2], "lon": r[3], "location": r[4], "date": r[5],
             "volunteer": r[6] + (f" ({r[7]})" if r[7] else ""), "weight_kg": r[8]} for r in rows]

@app.get("/api/spots")
async def api_spots():
    rows = db.get_trash_spots()
    return [{"lat": r[0], "lon": r[1], "desc": r[2], "date": r[3], "reporter": r[4]} for r in rows]

@app.get("/api/monthly")
async def api_monthly():
    rows = db.get_monthly_stats()
    return {"labels": [r[0] for r in rows], "kg": [r[1] for r in rows]}

@app.get("/api/bytype")
async def api_bytype():
    rows = db.get_stats_by_type()
    return {"labels": [r[0] for r in rows], "kg": [r[1] for r in rows]}

@app.get("/api/leaders")
async def api_leaders():
    rows = db.get_leaderboard(limit=50)
    return [{"name": r[0], "username": r[1] or "", "group": r[4] or "", "kg": r[2], "cleanups": r[3]} for r in rows]

@app.get("/api/groups")
async def api_groups():
    rows = db.get_group_stats()
    return [{"name": r[0], "members": r[1], "kg": r[2], "cleanups": r[3]} for r in rows]