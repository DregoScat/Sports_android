"""
AI Fitness Monitor Server
=========================

Main entry point for the Flask server.

Usage:
    python run.py
    
Or with gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 run:app
"""

import os
import sys

# Add server source to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from src.api import register_routes
from templates.index import HTML_TEMPLATE

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Create Flask app
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Register routes
register_routes(app, HTML_TEMPLATE)


def main():
    """Main entry point."""
    print(f"""
╔══════════════════════════════════════════════════════╗
║          AI Fitness Monitor Server                   ║
╠══════════════════════════════════════════════════════╣
║  Server running at: http://{HOST}:{PORT:<5}              ║
║  Debug mode: {str(DEBUG):<5}                               ║
║                                                      ║
║  Endpoints:                                          ║
║    GET  /           - Web interface                  ║
║    GET  /squat_feed - Squat analysis stream          ║
║    GET  /jump_feed  - Jump analysis stream           ║
║    POST /process_frame - Mobile frame processing     ║
║    POST /reset_analyzer - Reset analyzer state       ║
║    GET  /health     - Health check                   ║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)


if __name__ == "__main__":
    main()
