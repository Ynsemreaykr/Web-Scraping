import logging
import threading
import sys
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.db_service import db
from processing.classifier import CATEGORY_DISPLAY, classifier
from pipeline import run_pipeline
from scrape_state import reset_progress, get_progress

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
_scrape_thread = None


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
    else:
        filters["date_from"] = datetime.utcnow() - timedelta(days=Config.SCRAPE_DAYS)

    if request.args.get("date_to"):
        try:
            dt_to = datetime.fromisoformat(request.args.get("date_to"))
            filters["date_to"] = dt_to + timedelta(days=1)
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
    global scrape_status, _scrape_thread

    if scrape_status["running"]:
        if _scrape_thread and _scrape_thread.is_alive():
            return jsonify({"success": False, "message": "Scraping zaten çalışıyor"}), 409
        logger.warning("Önceki scraping thread ölmüş ama running=True kalmış, sıfırlanıyor.")
        scrape_status["running"] = False

    body = request.get_json(silent=True) or {}
    source_keys = body.get("sources")
    reset_progress()

    def _run():
        global scrape_status
        scrape_status["running"] = True
        try:
            cleared = db.clear_news_and_cache()
            logger.info("DB temizlendi (scrape oncesi): %s", cleared)
            stats = run_pipeline(source_keys)
            scrape_status["last_stats"] = stats
            scrape_status["last_run"] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Pipeline hatasi: {e}")
            scrape_status["last_stats"] = {"error": str(e)}
        finally:
            scrape_status["running"] = False

    _scrape_thread = threading.Thread(target=_run, daemon=True)
    _scrape_thread.start()

    return jsonify({"success": True, "message": "Scraping başlatıldı"})


@app.route("/api/scrape/status")
def scrape_status_endpoint():
    payload = dict(scrape_status)
    payload["progress"] = get_progress()
    return jsonify({"success": True, "data": payload})


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


@app.route("/api/classifier/keywords")
def get_classifier_keywords():
    """Rapor icin: kategori basina kullanilan anahtar kelimeler."""
    return jsonify({"success": True, "data": classifier.get_all_keywords_flat()})


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


@app.route("/api/reset-db", methods=["POST"])
def reset_database():
    """news + geocoding_cache temizligi (sadece yerel gelistirme)."""
    body = request.get_json(silent=True) or {}
    if body.get("confirm") != "SIL_TUM_HABERLER":
        return jsonify(
            {
                "success": False,
                "error": 'JSON body: {"confirm":"SIL_TUM_HABERLER"} gerekli',
            }
        ), 400
    data = db.clear_news_and_cache()
    return jsonify({"success": True, "data": data})


if __name__ == "__main__":
    db.purge_old_news(keep_days=Config.SCRAPE_DAYS)
    _port = int(os.environ.get("PORT", "5000"))
    logger.info("Flask sunucusu basliyor... http://localhost:%s", _port)
    app.run(debug=True, port=_port, use_reloader=False)
