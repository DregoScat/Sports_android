"""
Camera Manager Module
=====================

Thread-safe camera management for handling single camera access
across multiple analyzer types.
"""

import threading
import time
from typing import Any, Optional, Type

import numpy as np


class CameraManager:
    """
    Thread-safe camera manager for single camera access.
    
    Handles switching between different analyzer types while
    ensuring only one analyzer can access the camera at a time.
    
    Attributes:
        running (bool): Whether the capture loop is running
        analyzer_type (str): Current analyzer type identifier
    """
    
    def __init__(self):
        """Initialize the camera manager."""
        self.lock = threading.Lock()
        self.analyzer = None
        self.analyzer_type: Optional[str] = None
        self.frame: Optional[np.ndarray] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self, analyzer_cls: Type[Any], analyzer_type: str) -> bool:
        """
        Start or switch to a new analyzer type.
        
        Args:
            analyzer_cls: Analyzer class to instantiate
            analyzer_type: String identifier for this analyzer type
            
        Returns:
            True if analyzer started successfully, False otherwise
        """
        with self.lock:
            # If same type is already running, just return
            if self.analyzer_type == analyzer_type and self.running:
                return True
            
            # Stop existing analyzer
            self._stop_internal()
            
            # Start new analyzer
            try:
                self.analyzer = analyzer_cls()
                if not self.analyzer.is_opened():
                    self.analyzer = None
                    return False
                self.analyzer_type = analyzer_type
                self.running = True
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
                return True
            except Exception as e:
                print(f"Failed to start analyzer: {e}")
                return False
    
    def _stop_internal(self) -> None:
        """Internal method to stop the current analyzer (not thread-safe)."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        if self.analyzer:
            try:
                self.analyzer.release()
            except Exception:
                pass
            self.analyzer = None
        self.frame = None
        self.analyzer_type = None
    
    def stop(self) -> None:
        """Stop the current analyzer (thread-safe)."""
        with self.lock:
            self._stop_internal()
    
    def _capture_loop(self) -> None:
        """Background capture loop for continuous frame acquisition."""
        while self.running and self.analyzer and self.analyzer.is_opened():
            try:
                frame = self.analyzer.read_frame()
                if frame is not None:
                    self.frame = frame.copy()
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Capture error: {e}")
                break
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest captured frame (thread-safe copy).
        
        Returns:
            Copy of latest frame as numpy array, or None if no frame available
        """
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return None
    
    def is_running(self) -> bool:
        """Check if an analyzer is currently running."""
        return self.running
    
    def get_analyzer_type(self) -> Optional[str]:
        """Get the current analyzer type identifier."""
        return self.analyzer_type
