import logging
import threading
import sys
import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.db_service import db
from processing.classifier import CATEGORY_DISPLAY
from pipeline import run_pipeline

# Logging ayari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Scraping durumu
scrape_status = {"running": False, "last_run": None, "last_stats": None}


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


# ─── Haberler ─────────────────────────────────────────────────────────────────
@app.route("/api/news")
def get_news():
    filters = {}
    if request.args.get("category"):
        filters["category"] = request.args.get("category")
    if request.args.get("district"):
        filters["district"] = request.args.get("district")
    if request.args.get("date_from"):
        try:
            filters["date_from"] = datetime.fromisoformat(request.args.get("date_from"))
        except Exception:
            pass
    if request.args.get("date_to"):
        try:
            filters["date_to"] = datetime.fromisoformat(request.args.get("date_to"))
        except Exception:
            pass
    if request.args.get("has_location") == "true":
        filters["has_location"] = True

    limit = min(int(request.args.get("limit", 500)), 1000)
    news = db.get_all_news(filters, limit)
    return jsonify({"success": True, "count": len(news), "data": news})


@app.route("/api/news/<news_id>")
def get_news_by_id(news_id):
    news = db.get_news_by_id(news_id)
    if not news:
        return jsonify({"success": False, "error": "Haber bulunamadi"}), 404
    return jsonify({"success": True, "data": news})


# ─── Scraping ─────────────────────────────────────────────────────────────────
@app.route("/api/scrape", methods=["GET", "POST"])
def trigger_scrape():
    global scrape_status

    if scrape_status["running"]:
        return jsonify({"success": False, "message": "Scraping zaten çalışıyor"}), 409

    source_keys = request.json.get("sources") if request.json else None

    def _run():
        global scrape_status
        scrape_status["running"] = True
        try:
            stats = run_pipeline(source_keys)
            scrape_status["last_stats"] = stats
            scrape_status["last_run"] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Pipeline hatasi: {e}")
            scrape_status["last_stats"] = {"error": str(e)}
        finally:
            scrape_status["running"] = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"success": True, "message": "Scraping başlatıldı"})


@app.route("/api/scrape/status")
def scrape_status_endpoint():
    return jsonify({"success": True, "data": scrape_status})


# ─── Filtreler ────────────────────────────────────────────────────────────────
@app.route("/api/categories")
def get_categories():
    categories = [
        {"key": k, "display": v}
        for k, v in CATEGORY_DISPLAY.items()
    ]
    return jsonify({"success": True, "data": categories})


@app.route("/api/districts")
def get_districts():
    return jsonify({"success": True, "data": Config.KOCAELI_DISTRICTS})


# ─── İstatistik ───────────────────────────────────────────────────────────────
@app.route("/api/stats")
def get_stats():
    stats = db.get_stats()
    return jsonify({"success": True, "data": stats})


# ─── Google API Key (frontend için) ──────────────────────────────────────────
@app.route("/api/config")
def get_config():
    return jsonify({
        "success": True,
        "data": {
            "googleApiKey": Config.GOOGLE_API_KEY,
            "kocaeliCenter": {
                "lat": Config.KOCAELI_CENTER_LAT,
                "lng": Config.KOCAELI_CENTER_LNG,
            }
        }
    })


if __name__ == "__main__":
    logger.info("Flask sunucusu basliyor... http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)
