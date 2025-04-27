# lidar_server.py
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import subprocess
import os
import threading
import time
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/broulo/lidar_server.log')
    ]
)
logger = logging.getLogger("lidar_server")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
SCAN_DIR = "/home/broulo/scansTemp2del"
CURRENT_SCAN = None
SCAN_PROCESS = None
SCAN_STATUS = "idle"  # idle, scanning, processing

# Make sure scan directory exists
os.makedirs(SCAN_DIR, exist_ok=True)

# test
@app.route('/test', methods=['GET'])
def test_connection():
    logger.info("Connexion Test Requested")
    try:
        return jsonify({"message": "Connected successfully"})
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route('/status', methods=['GET'])
def get_status():
    logger.info("Status request received")
    try:
        disk_space = get_disk_space()
        return jsonify({
            "status": SCAN_STATUS,
            "current_scan": CURRENT_SCAN,
            "disk_space": disk_space
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

# SCAN
@app.route('/start_scan', methods=['POST'])
def start_scan():
    global SCAN_PROCESS, SCAN_STATUS, CURRENT_SCAN
    
    logger.info("Start scan request received")
    
    if SCAN_STATUS != "idle":
        logger.warning("Scanner already in use")
        return jsonify({"error": "Scanner already in use"}), 400
    
    scan_name = request.json.get('name', f"scan_{int(time.time())}")
    CURRENT_SCAN = scan_name
    SCAN_STATUS = "scanning"
    
    try:
        # Launch scan process in background
        cmd = ["/home/jetson/lidar_scripts/start_scan.sh", scan_name]
        logger.info(f"Executing command: {' '.join(cmd)}")
        SCAN_PROCESS = subprocess.Popen(cmd)
        
        return jsonify({"status": "started", "scan_name": scan_name})
    except Exception as e:
        SCAN_STATUS = "idle"
        CURRENT_SCAN = None
        logger.error(f"Error starting scan: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    global SCAN_PROCESS, SCAN_STATUS
    
    logger.info("Stop scan request received")
    
    if SCAN_STATUS != "scanning":
        logger.warning("No active scan to stop")
        return jsonify({"error": "No active scan to stop"}), 400
    
    try:
        # Signal stop to scan script
        if SCAN_PROCESS and SCAN_PROCESS.poll() is None:
            subprocess.run(["/home/jetson/lidar_scripts/stop_scan.sh"])
            SCAN_PROCESS.wait()
        
        SCAN_STATUS = "processing"
        
        # Post-scan processing
        def process_scan():
            global SCAN_STATUS
            try:
                logger.info(f"Processing scan: {CURRENT_SCAN}")
                subprocess.run(["/home/jetson/lidar_scripts/process_scan.sh", CURRENT_SCAN])
                logger.info("Scan processing complete")
            except Exception as e:
                logger.error(f"Error processing scan: {str(e)}")
            finally:
                SCAN_STATUS = "idle"
        
        threading.Thread(target=process_scan).start()
        
        return jsonify({"status": "stopping", "message": "Scan stopped and processing"})
    except Exception as e:
        logger.error(f"Error stopping scan: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ACCESS
@app.route('/scans', methods=['GET'])
def list_scans():
    logger.info("List scans request received")
    try:
        scans = [f for f in os.listdir(SCAN_DIR) if f.endswith('.pcd')]
        scan_data = []
        
        for scan in scans:
            path = os.path.join(SCAN_DIR, scan)
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            
            scan_data.append({
                "name": scan,
                "size": size,
                "date": int(mtime)
            })
        
        logger.info(f"Found {len(scans)} scans")
        return jsonify({"scans": scan_data})
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/scans/<scan_name>', methods=['GET'])
def get_scan(scan_name):
    logger.info(f"Download request for scan: {scan_name}")
    try:
        file_path = os.path.join(SCAN_DIR, scan_name)
        if not os.path.exists(file_path):
            logger.warning(f"Scan not found: {scan_name}")
            return jsonify({"error": "Scan not found"}), 404
        
        return send_file(file_path, mimetype='application/octet-stream', 
                        as_attachment=True, download_name=scan_name)
    except Exception as e:
        logger.error(f"Error serving scan file: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_disk_space():
    """Get available disk space"""
    try:
        stat = os.statvfs(SCAN_DIR)
        free = stat.f_bavail * stat.f_frsize
        total = stat.f_blocks * stat.f_frsize
        used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
        
        return {
            "free": free,
            "total": total,
            "used": used,
            "percent_used": (used / total) * 100
        }
    except Exception as e:
        logger.error(f"Error getting disk space: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)