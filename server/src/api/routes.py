"""
API Routes Module
=================

Flask API routes for the fitness monitor server.
"""

import base64
import time
import traceback

import cv2
import numpy as np
from flask import Response, render_template_string, request, jsonify

from ..analyzers import SquatAnalyzer, JumpAnalyzer
from ..utils import CameraManager, MobileFrameProcessor

# Global instances
camera_manager = CameraManager()
mobile_processor = MobileFrameProcessor()


def _encode_frame(frame: np.ndarray) -> bytes:
    """Encode frame to JPEG bytes."""
    ret, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ret else b""


def _stream_frames(analyzer_cls, analyzer_type: str):
    """Generator for streaming frames from camera."""
    if not camera_manager.start(analyzer_cls, analyzer_type):
        return
    
    while camera_manager.running and camera_manager.analyzer_type == analyzer_type:
        frame = camera_manager.get_frame()
        if frame is not None:
            chunk = _encode_frame(frame)
            if chunk:
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + chunk + b"\r\n")
        time.sleep(0.03)  # ~30 FPS


def register_routes(app, html_template: str):
    """
    Register all API routes with the Flask app.
    
    Args:
        app: Flask application instance
        html_template: HTML template string for the index page
    """
    
    @app.route("/")
    def index():
        """Serve the main web interface."""
        return render_template_string(html_template)

    @app.route("/squat_feed")
    def squat_feed():
        """Stream MJPEG video with squat analysis overlay."""
        return Response(
            _stream_frames(SquatAnalyzer, "squat"),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/jump_feed")
    def jump_feed():
        """Stream MJPEG video with jump analysis overlay."""
        return Response(
            _stream_frames(JumpAnalyzer, "jump"),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/process_frame", methods=["POST"])
    def process_frame():
        """
        Process a frame from mobile camera and return analyzed frame.
        
        Request JSON:
            {
                "image": "<base64-encoded-jpeg>",
                "mode": "squat" | "jump"
            }
            
        Response JSON:
            {
                "image": "<base64-encoded-jpeg>",
                "feedback": "<feedback-message>"
            }
        """
        try:
            data = request.get_json()
            if not data or "image" not in data:
                return jsonify({"error": "No image data"}), 400
            
            mode = data.get("mode", "squat")
            image_data = data["image"]
            
            # Validate base64 data
            if not image_data or len(image_data) < 100:
                return jsonify({"error": "Invalid image data - too small"}), 400
            
            # Decode base64 image
            try:
                img_bytes = base64.b64decode(image_data)
            except Exception as e:
                return jsonify({"error": f"Base64 decode error: {str(e)}"}), 400
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                return jsonify({"error": "Failed to decode image"}), 400
            
            # Validate frame dimensions
            if frame.shape[0] < 10 or frame.shape[1] < 10:
                return jsonify({"error": "Image too small"}), 400
            
            # Process frame based on mode
            if mode == "squat":
                analyzer = mobile_processor.get_squat_analyzer()
            else:
                analyzer = mobile_processor.get_jump_analyzer()
            
            processed_frame = analyzer.process_frame(frame)
            
            if processed_frame is None:
                return jsonify({"error": "Processing failed"}), 500
            
            # Encode processed frame to JPEG
            ret, buffer = cv2.imencode(".jpg", processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                return jsonify({"error": "Failed to encode processed frame"}), 500
            
            encoded_image = base64.b64encode(buffer).decode("utf-8")
            
            return jsonify({
                "image": encoded_image,
                "feedback": analyzer.feedback or ""
            })
        except Exception as e:
            print(f"Error processing frame: {e}")
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/reset_analyzer", methods=["POST"])
    def reset_analyzer():
        """
        Reset analyzer counters and state.
        
        Request JSON:
            {
                "mode": "squat" | "jump"
            }
        """
        try:
            data = request.get_json()
            mode = data.get("mode", "squat") if data else "squat"
            
            if mode == "squat":
                mobile_processor.reset_squat_analyzer()
            else:
                mobile_processor.reset_jump_analyzer()
            
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "camera_running": camera_manager.is_running(),
            "analyzer_type": camera_manager.get_analyzer_type()
        })
