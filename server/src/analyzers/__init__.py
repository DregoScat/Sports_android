"""
Exercise Analyzers Module
=========================

Contains pose detection and analysis classes for different exercises.
"""

from .squat_analyzer import SquatAnalyzer, SquatAnalyzerMobile
from .jump_analyzer import JumpAnalyzer, JumpAnalyzerMobile

__all__ = [
    "SquatAnalyzer",
    "SquatAnalyzerMobile", 
    "JumpAnalyzer",
    "JumpAnalyzerMobile",
]
