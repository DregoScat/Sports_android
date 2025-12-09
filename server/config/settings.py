"""
Server Configuration
====================

Configuration settings for the fitness monitor server.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    threaded: bool = True


@dataclass
class CameraConfig:
    """Camera configuration settings."""
    index: Optional[int] = None  # None for auto-detect
    width: int = 640
    height: int = 480
    fps: int = 30


@dataclass 
class AnalyzerConfig:
    """Analyzer configuration settings."""
    # Squat thresholds
    squat_stage_s1: float = 160.0
    squat_stage_s2: float = 95.0
    visibility_threshold: float = 0.8
    depth_hold_requirement: int = 3
    
    # Jump thresholds
    calibration_inches: float = 12.0
    calibration_pixels: float = 100.0
    min_jump_inches: float = 2.0
    smoothing_window: int = 5
    min_airborne_frames: int = 6


def get_server_config() -> ServerConfig:
    """Get server configuration from environment."""
    return ServerConfig(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        threaded=True
    )


def get_camera_config() -> CameraConfig:
    """Get camera configuration from environment."""
    index = os.getenv("CAMERA_INDEX")
    return CameraConfig(
        index=int(index) if index else None,
        width=int(os.getenv("CAMERA_WIDTH", "640")),
        height=int(os.getenv("CAMERA_HEIGHT", "480")),
        fps=int(os.getenv("CAMERA_FPS", "30"))
    )


def get_analyzer_config() -> AnalyzerConfig:
    """Get analyzer configuration from environment."""
    return AnalyzerConfig(
        calibration_inches=float(os.getenv("CALIBRATION_INCHES", "12")),
        calibration_pixels=float(os.getenv("CALIBRATION_PIXELS", "100")),
        min_jump_inches=float(os.getenv("MIN_JUMP_INCHES", "2.0")),
        smoothing_window=int(os.getenv("SMOOTHING_WINDOW", "5")),
        min_airborne_frames=int(os.getenv("MIN_AIRBORNE_FRAMES", "6"))
    )
