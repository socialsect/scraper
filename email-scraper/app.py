"""
Simple Flask app that serves HTML frontend for the email scraper.
Polls the FastAPI backend for updates.
"""

import requests
import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO

app = Flask(__name__)
CORS(app)

API_URL = "http://localhost:8000"

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")

@app.route("/api/create-job", methods=["POST"])
def create_job():
    """Create a new scrape job."""
    try:
        data = request.json
        response = requests.post(f"{API_URL}/jobs", json=data)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/job/<job_id>", methods=["GET"])
def get_job(job_id):
    """Get job status and stats."""
    try:
        response = requests.get(f"{API_URL}/jobs/{job_id}/status")
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/job/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id):
    """Get job logs."""
    try:
        response = requests.get(f"{API_URL}/jobs/{job_id}/logs")
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """List all jobs."""
    try:
        response = requests.get(f"{API_URL}/jobs")
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop-job/<job_id>", methods=["POST"])
def stop_job(job_id):
    """Stop a running job."""
    try:
        response = requests.delete(f"{API_URL}/jobs/{job_id}")
        response.raise_for_status()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download/<job_id>", methods=["GET"])
def download_csv(job_id):
    """Download results as CSV."""
    try:
        response = requests.get(f"{API_URL}/jobs/{job_id}/download")
        response.raise_for_status()
        
        return send_file(
            BytesIO(response.content),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"emails_{job_id}.csv"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health():
    """Check if API is up."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        response.raise_for_status()
        return jsonify({"status": "ok"})
    except:
        return jsonify({"status": "down"}), 503

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
