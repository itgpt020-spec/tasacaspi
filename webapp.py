from flask import Flask, render_template, jsonify
from database import (
    init_db, get_cleanups, get_trash_spots, get_leaderboard,
    get_group_stats, get_stats_by_type, get_monthly_stats
)
from config import MAP_CENTER_LAT, MAP_CENTER_LON, TRASH_TYPES

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return render_template("index.html", lat=MAP_CENTER_LAT, lon=MAP_CENTER_LON)


@app.route("/api/stats")
def api_stats():
    cleanups = get_cleanups()
    spots = get_trash_spots()
    total_kg = sum(c[8] or 0 for c in cleanups)
    total_cleanups = len(cleanups)
    total_spots = len(spots)
    volunteers = len(set(c[1] for c in cleanups))
    return jsonify({
        "total_kg": total_kg,
        "total_cleanups": total_cleanups,
        "total_spots": total_spots,
        "total_volunteers": volunteers
    })


@app.route("/api/cleanups")
def api_cleanups():
    rows = get_cleanups()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "lat": r[2],
            "lon": r[3],
            "location": r[4],
            "date": r[5][:10] if r[5] else "",
            "volunteer": r[6] or r[7] or "Аноним",
            "weight_kg": r[8] or 0,
            "bags": r[9] or 0
        })
    return jsonify(out)


@app.route("/api/spots")
def api_spots():
    rows = get_trash_spots()
    out = []
    for r in rows:
        out.append({
            "lat": r[0],
            "lon": r[1],
            "desc": r[2],
            "date": r[3][:10] if r[3] else "",
            "reporter": r[4] or "Аноним"
        })
    return jsonify(out)


@app.route("/api/leaders")
def api_leaders():
    rows = get_leaderboard(20)
    out = []
    for r in rows:
        out.append({
            "name": r[0],
            "username": r[1] or "",
            "kg": r[2] or 0,
            "cleanups": r[3] or 0,
            "group": r[4] or "Индивидуально"
        })
    return jsonify(out)


@app.route("/api/groups")
def api_groups():
    rows = get_group_stats()
    out = []
    for r in rows:
        out.append({
            "name": r[0],
            "kg": r[2] or 0,
            "cleanups": r[3] or 0,
            "members": r[1] or 0
        })
    return jsonify(out)


@app.route("/api/monthly")
def api_monthly():
    rows = get_monthly_stats()
    labels = [r[0] for r in rows]
    kg = [r[1] or 0 for r in rows]
    return jsonify({"labels": labels, "kg": kg})


@app.route("/api/bytype")
def api_bytype():
    rows = get_stats_by_type()
    labels = [TRASH_TYPES.get(r[0], r[0]) for r in rows]
    kg = [r[1] or 0 for r in rows]
    return jsonify({"labels": labels, "kg": kg})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
