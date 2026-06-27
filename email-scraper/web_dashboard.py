"""
Simple web dashboard for email scraper.
No FastAPI, no complex integration - just a Flask server that runs jobs.
"""

import asyncio
import json
import os
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path

app = Flask(__name__)

# Job storage
JOBS_DIR = Path("web_jobs")
JOBS_DIR.mkdir(exist_ok=True)

active_jobs = {}  # job_id -> {"process": subprocess, "status": "running", ...}


def get_job_file(job_id):
    """Get path to job's JSON file."""
    return JOBS_DIR / f"{job_id}.json"


def save_job(job_id, data):
    """Save job data to JSON."""
    with open(get_job_file(job_id), 'w') as f:
        json.dump(data, f, indent=2)


def load_job(job_id):
    """Load job data from JSON."""
    file = get_job_file(job_id)
    if not file.exists():
        return None
    with open(file, 'r') as f:
        return json.load(f)


def load_all_jobs():
    """Load all jobs."""
    jobs = []
    for file in JOBS_DIR.glob("*.json"):
        try:
            with open(file, 'r') as f:
                jobs.append(json.load(f))
        except:
            pass
    return sorted(jobs, key=lambda x: x.get('created_at', ''), reverse=True)


def run_scraper_job(job_id, query, engine, backend, check_mx, output_file):
    """Run the CLI scraper and track stats."""
    job = load_job(job_id)
    job['status'] = 'running'
    job['started_at'] = datetime.now().isoformat()
    save_job(job_id, job)
    
    # Build command
    cmd = ['python', 'main.py', query, '--engine', engine, '--backend', backend]
    if not check_mx:
        cmd.append('--no-mx')
    if output_file:
        cmd.extend(['--output', output_file])
    
    print(f"[JOB {job_id}] Running: {' '.join(cmd)}")
    
    try:
        # Run the scraper
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        active_jobs[job_id] = {'process': process, 'start_time': time.time()}
        
        logs = []
        stats = {
            'pages_crawled': 0,
            'new_emails': 0,
            'total_emails': 0,
            'errors': 0,
            'last_email': '',
            'rate_per_min': 0.0
        }
        
        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            # Parse stats from output
            if 'new emails' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'new' in part.lower() and i + 1 < len(parts):
                            stats['new_emails'] = int(parts[i + 1].replace(',', ''))
                except:
                    pass
            
            if 'total' in line.lower() and 'email' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'total' in part.lower() and i + 1 < len(parts):
                            stats['total_emails'] = int(parts[i + 1].replace(',', '').replace(')', ''))
                except:
                    pass
            
            if 'pages crawled' in line.lower() or 'crawled' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'crawled' in part.lower() and i - 1 >= 0:
                            stats['pages_crawled'] = int(parts[i - 1].replace(',', ''))
                except:
                    pass
            
            # Store log
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"{timestamp} | {line[:200]}"
            logs.append(log_entry)
            if len(logs) > 100:
                logs = logs[-100:]
            
            # Update job file
            elapsed = int(time.time() - active_jobs[job_id]['start_time'])
            if stats['new_emails'] > 0 and elapsed > 0:
                stats['rate_per_min'] = (stats['new_emails'] / elapsed) * 60
            
            job['stats'] = stats
            job['logs'] = logs[-50:]  # Keep last 50 logs
            job['elapsed_seconds'] = elapsed
            save_job(job_id, job)
        
        # Wait for process to complete
        process.wait()
        
        # Update final status
        job = load_job(job_id)
        job['status'] = 'completed' if process.returncode == 0 else 'failed'
        job['completed_at'] = datetime.now().isoformat()
        if process.returncode != 0:
            job['error'] = f"Process exited with code {process.returncode}"
        save_job(job_id, job)
        
        print(f"[JOB {job_id}] Finished with status: {job['status']}")
        
    except Exception as e:
        print(f"[JOB {job_id}] Error: {e}")
        job = load_job(job_id)
        job['status'] = 'failed'
        job['error'] = str(e)
        job['completed_at'] = datetime.now().isoformat()
        save_job(job_id, job)
    finally:
        if job_id in active_jobs:
            del active_jobs[job_id]


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    jobs = load_all_jobs()
    return jsonify({'jobs': jobs})


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create and start a new job."""
    data = request.json
    
    # Generate job ID
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create job record
    job = {
        'id': job_id,
        'query': data.get('query'),
        'engine': data.get('engine', 'google'),
        'backend': data.get('backend', 'scrapling'),
        'check_mx': data.get('check_mx', True),
        'output_file': data.get('output_file', f'output/emails_{job_id}.csv'),
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'stats': {
            'pages_crawled': 0,
            'new_emails': 0,
            'total_emails': 0,
            'errors': 0,
            'last_email': '',
            'rate_per_min': 0.0
        },
        'logs': [],
        'elapsed_seconds': 0
    }
    
    save_job(job_id, job)
    
    # Start job in background thread
    thread = threading.Thread(
        target=run_scraper_job,
        args=(job_id, job['query'], job['engine'], job['backend'], job['check_mx'], job['output_file'])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify(job)


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status."""
    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def stop_job(job_id):
    """Stop a running job."""
    if job_id in active_jobs:
        try:
            active_jobs[job_id]['process'].terminate()
            job = load_job(job_id)
            job['status'] = 'stopped'
            job['completed_at'] = datetime.now().isoformat()
            save_job(job_id, job)
        except:
            pass
    return jsonify({'success': True})


@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_job(job_id):
    """Download job results."""
    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    output_file = job.get('output_file', f'output/emails_{job_id}.csv')
    if not os.path.exists(output_file):
        return jsonify({'error': 'Results file not found'}), 404
    
    return send_file(output_file, as_attachment=True, download_name=f'emails_{job_id}.csv')


if __name__ == '__main__':
    print("=" * 60)
    print("Email Scraper Web Dashboard")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:5000")
    print()
    print("Open your browser and go to: http://localhost:5000")
    print()
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
