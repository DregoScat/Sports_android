"""
Mobile Frame Processor Module
=============================

Thread-safe processor for handling frames from mobile devices.
"""

import threading
from typing import Optional

from ..analyzers import SquatAnalyzerMobile, JumpAnalyzerMobile


class MobileFrameProcessor:
    """
    Thread-safe processor for mobile camera frames.
    
    Manages lazy initialization and access to mobile analyzers
    for both squat and jump analysis modes.
    
    Usage:
        processor = MobileFrameProcessor()
        squat_analyzer = processor.get_squat_analyzer()
        jump_analyzer = processor.get_jump_analyzer()
    """
    
    def __init__(self):
        """Initialize the mobile frame processor."""
        self._squat_analyzer: Optional[SquatAnalyzerMobile] = None
        self._jump_analyzer: Optional[JumpAnalyzerMobile] = None
        self._lock = threading.Lock()
    
    def get_squat_analyzer(self) -> SquatAnalyzerMobile:
        """
        Get or create the squat analyzer instance.
        
        Returns:
            Thread-safe squat analyzer instance
        """
        with self._lock:
            if self._squat_analyzer is None:
                self._squat_analyzer = SquatAnalyzerMobile()
            return self._squat_analyzer
    
    def get_jump_analyzer(self) -> JumpAnalyzerMobile:
        """
        Get or create the jump analyzer instance.
        
        Returns:
            Thread-safe jump analyzer instance
        """
        with self._lock:
            if self._jump_analyzer is None:
                self._jump_analyzer = JumpAnalyzerMobile()
            return self._jump_analyzer
    
    def reset_squat_analyzer(self) -> None:
        """Reset the squat analyzer counters and state."""
        analyzer = self.get_squat_analyzer()
        analyzer.reset()
    
    def reset_jump_analyzer(self) -> None:
        """Reset the jump analyzer counters and state."""
        analyzer = self.get_jump_analyzer()
        analyzer.reset()
