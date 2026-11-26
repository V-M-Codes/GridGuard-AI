# -*- coding: utf-8 -*-
"""
GridGuard AI Microgrid Control Center - Flask REST & Telemetry Server
Serves real-time microgrid APIs and static dashboard files.
"""

import os
import json
import time
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from .microgrid_engine import MicrogridEngine

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "Frontend")

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# Engine singleton
engine = MicrogridEngine()


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route("/api/status", methods=["GET"])
def get_status():
    """Retrieve the real-time telemetry snapshot of the microgrid."""
    return jsonify({
        "status": "success",
        "data": engine.state
    })


@app.route("/api/outage/simulate", methods=["POST"])
def simulate_outage():
    """Simulate loss of main utility power and trigger sub-cycle islanding."""
    new_state = engine.simulate_outage()
    return jsonify({
        "status": "success",
        "action": "simulate_outage",
        "data": new_state
    })


@app.route("/api/outage/restore", methods=["POST"])
def restore_grid():
    """Restore main utility grid synchronization."""
    new_state = engine.restore_grid()
    return jsonify({
        "status": "success",
        "action": "restore_grid",
        "data": new_state
    })


@app.route("/api/weather", methods=["POST"])
def set_weather():
    """Update solar weather irradiance: sunny | cloudy | stormy."""
    data = request.get_json(silent=True) or {}
    weather = data.get("weather", "sunny")
    new_state = engine.set_weather(weather)
    return jsonify({
        "status": "success",
        "action": "set_weather",
        "weather": weather,
        "data": new_state
    })


@app.route("/api/bess/soc", methods=["POST"])
def set_soc():
    """Simulate Battery SoC (5.0 to 100.0)."""
    data = request.get_json(silent=True) or {}
    soc = float(data.get("soc", 88.5))
    new_state = engine.set_soc(soc)
    return jsonify({
        "status": "success",
        "action": "set_soc",
        "soc": soc,
        "data": new_state
    })


@app.route("/api/genset/crank", methods=["POST"])
def test_crank():
    """Initiate 10-second test crank on Backup Genset GS-1."""
    new_state = engine.test_crank_genset()
    return jsonify({
        "status": "success",
        "action": "test_crank",
        "data": new_state
    })


@app.route("/api/genset/mode", methods=["POST"])
def toggle_genset_mode():
    """Toggle or set generator mode: AUTO | MANUAL."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    new_state = engine.toggle_genset_mode(mode)
    return jsonify({
        "status": "success",
        "action": "toggle_mode",
        "mode": engine.genset_mode,
        "data": new_state
    })


@app.route("/api/genset/emergency", methods=["POST"])
def toggle_genset_emergency():
    """Toggle manual emergency run override on Genset GS-1."""
    data = request.get_json(silent=True) or {}
    force_state = data.get("running")
    new_state = engine.toggle_genset_emergency(force_state)
    return jsonify({
        "status": "success",
        "action": "toggle_emergency",
        "running": engine.genset_running,
        "data": new_state
    })


@app.route("/api/drill/execute", methods=["POST"])
def execute_drill():
    """Execute automated ISO 22301 Black-Start resilience test."""
    data = request.get_json(silent=True) or {}
    duration = data.get("duration", "30m")
    new_state = engine.execute_drill(duration)
    return jsonify({
        "status": "success",
        "action": "execute_drill",
        "duration": duration,
        "data": new_state
    })


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Reset all parameters back to baseline nominal state."""
    new_state = engine.reset()
    return jsonify({
        "status": "success",
        "action": "reset",
        "data": new_state
    })


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Retrieve decision stream event logs."""
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({
        "status": "success",
        "logs": engine.event_logs[-limit:]
    })


# ==========================================
# SERVER-SENT EVENTS (SSE) STREAMING
# ==========================================

@app.route("/api/stream", methods=["GET"])
def stream_telemetry():
    """Real-time SSE event stream broadcasting state every second."""
    def event_generator():
        while True:
            state_data = engine.recalculate()
            yield f"data: {json.dumps(state_data)}\n\n"
            time.sleep(1.0)
    return Response(event_generator(), mimetype="text/event-stream")


# ==========================================
# STATIC DASHBOARD SERVING
# ==========================================

@app.route("/", methods=["GET"])
def index():
    """Serve the master GridGuard AI control center dashboard."""
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>", methods=["GET"])
def serve_file(filename):
    """Serve requested static HTML or text files."""
    if os.path.exists(os.path.join(STATIC_DIR, filename)):
        return send_from_directory(STATIC_DIR, filename)
    return jsonify({"error": "File not found"}), 404


def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n===========================================================")
    print(f"  ⚡ GridGuard AI Microgrid Backend Server")
    print(f"  📡 Running at: http://127.0.0.1:{port}")
    print(f"  📄 Master Dashboard: http://127.0.0.1:{port}/gridguard.html")
    print(f"  🌙 Dark Theme:       http://127.0.0.1:{port}/gridguard_dark.html")
    print(f"  ☀️ Light Theme:      http://127.0.0.1:{port}/gridguard_light.html")
    print(f"===========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)