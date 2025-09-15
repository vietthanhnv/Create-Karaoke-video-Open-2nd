"""
Audio-subtitle synchronization utilities.

This module provides advanced synchronization features for aligning
audio and subtitle timing with high precision.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import math

from ..core.models import AudioFile, SubtitleFile


logger = logging.getLogger(__name__)


@dataclass
class SyncPoint:
    """Represents a synchronization point between audio and subtitles."""
    audio_time: float
    subtitle_time: float
    confidence: float  # 0.0 to 1.0


@dataclass
class SyncAnalysis:
    """Analysis results for audio-subtitle synchronization."""
    sync_points: List[SyncPoint]
    average_offset: float
    offset_variance: float
    sync_quality: float  # 0.0 to 1.0
    recommendations: List[str]


class AudioSubtitleSynchronizer:
    """Advanced audio-subtitle synchronization engine."""
    
    def __init__(self):
        """Initialize the synchronizer."""
        self.timing_tolerance = 0.1  # 100ms tolerance
        self.min_sync_points = 3
        
    def analyze_synchronization(self, audio_file: AudioFile, 
                              subtitle_file: SubtitleFile) -> SyncAnalysis:
        """
        Analyze synchronization between audio and subtitles.
        
        Args:
            audio_file: Audio file to analyze
            subtitle_file: Subtitle file to analyze
            
        Returns:
            SyncAnalysis with detailed synchronization information
        """
        sync_points = self._find_sync_points(audio_file, subtitle_file)
        
        if not sync_points:
            return SyncAnalysis(
                sync_points=[],
                average_offset=0.0,
                offset_variance=0.0,
                sync_quality=0.0,
                recommendations=["No synchronization points found"]
            )
        
        # Calculate statistics
        offsets = [point.audio_time - point.subtitle_time for point in sync_points]
        average_offset = sum(offsets) / len(offsets)
        
        # Calculate variance
        variance = sum((offset - average_offset) ** 2 for offset in offsets) / len(offsets)
        
        # Calculate sync quality (lower variance = higher quality)
        max_variance = 1.0  # 1 second variance threshold
        sync_quality = max(0.0, 1.0 - (variance / max_variance))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            sync_points, average_offset, variance, audio_file, subtitle_file
        )
        
        return SyncAnalysis(
            sync_points=sync_points,
            average_offset=average_offset,
            offset_variance=variance,
            sync_quality=sync_quality,
            recommendations=recommendations
        )
    
    def _find_sync_points(self, audio_file: AudioFile, 
                         subtitle_file: SubtitleFile) -> List[SyncPoint]:
        """
        Find synchronization points between audio and subtitles.
        
        This is a simplified implementation that uses subtitle timing
        as reference points. In a full implementation, this would use
        audio analysis to detect speech patterns.
        """
        sync_points = []
        
        if not hasattr(subtitle_file, 'lines') or not subtitle_file.lines:
            return sync_points
        
        # Use subtitle start times as potential sync points
        for i, line in enumerate(subtitle_file.lines):
            if hasattr(line, 'start_time') and hasattr(line, 'text'):
                # Simple heuristic: longer lines are more likely to be good sync points
                text_length = len(line.text.strip())
                confidence = min(1.0, text_length / 50.0)  # Normalize to 0-1
                
                sync_point = SyncPoint(
                    audio_time=line.start_time,  # Assume perfect sync initially
                    subtitle_time=line.start_time,
                    confidence=confidence
                )
                sync_points.append(sync_point)
        
        # Sort by confidence and keep top sync points
        sync_points.sort(key=lambda x: x.confidence, reverse=True)
        return sync_points[:min(10, len(sync_points))]  # Keep top 10
    
    def _generate_recommendations(self, sync_points: List[SyncPoint],
                                average_offset: float, variance: float,
                                audio_file: AudioFile, subtitle_file: SubtitleFile) -> List[str]:
        """Generate synchronization recommendations."""
        recommendations = []
        
        if abs(average_offset) > 0.5:
            recommendations.append(
                f"Apply timing offset of {-average_offset:.2f} seconds to subtitles"
            )
        
        if variance > 0.25:
            recommendations.append(
                "High timing variance detected - manual review recommended"
            )
        
        if len(sync_points) < self.min_sync_points:
            recommendations.append(
                "Insufficient sync points - consider adding more subtitle markers"
            )
        
        # Check duration compatibility
        duration_diff = abs(audio_file.duration - self._get_subtitle_duration(subtitle_file))
        if duration_diff > 2.0:
            recommendations.append(
                f"Duration mismatch: {duration_diff:.2f}s difference between audio and subtitles"
            )
        
        if not recommendations:
            recommendations.append("Synchronization appears good")
        
        return recommendations
    
    def _get_subtitle_duration(self, subtitle_file: SubtitleFile) -> float:
        """Get the total duration of subtitles."""
        if not hasattr(subtitle_file, 'lines') or not subtitle_file.lines:
            return 0.0
        
        max_end_time = 0.0
        for line in subtitle_file.lines:
            if hasattr(line, 'end_time'):
                max_end_time = max(max_end_time, line.end_time)
        
        return max_end_time
    
    def apply_timing_correction(self, subtitle_file: SubtitleFile, 
                              offset: float) -> bool:
        """
        Apply timing correction to subtitle file.
        
        Args:
            subtitle_file: Subtitle file to correct
            offset: Time offset in seconds (positive = delay subtitles)
            
        Returns:
            True if correction was applied successfully
        """
        try:
            if not hasattr(subtitle_file, 'lines') or not subtitle_file.lines:
                return False
            
            for line in subtitle_file.lines:
                if hasattr(line, 'start_time'):
                    line.start_time = max(0.0, line.start_time + offset)
                if hasattr(line, 'end_time'):
                    line.end_time = max(0.0, line.end_time + offset)
            
            logger.info(f"Applied timing correction: {offset:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply timing correction: {e}")
            return False
    
    def validate_timing_precision(self, subtitle_file: SubtitleFile) -> Dict[str, Any]:
        """
        Validate timing precision and detect potential issues.
        
        Args:
            subtitle_file: Subtitle file to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'total_lines': 0,
            'timing_errors': [],
            'warnings': [],
            'average_duration': 0.0,
            'min_gap': float('inf'),
            'max_gap': 0.0
        }
        
        if not hasattr(subtitle_file, 'lines') or not subtitle_file.lines:
            return results
        
        lines = subtitle_file.lines
        results['total_lines'] = len(lines)
        
        durations = []
        gaps = []
        
        for i, line in enumerate(lines):
            if not (hasattr(line, 'start_time') and hasattr(line, 'end_time')):
                results['timing_errors'].append(f"Line {i+1}: Missing timing information")
                continue
            
            # Check line duration
            duration = line.end_time - line.start_time
            if duration <= 0:
                results['timing_errors'].append(
                    f"Line {i+1}: Invalid duration ({duration:.2f}s)"
                )
            elif duration < 0.5:
                results['warnings'].append(
                    f"Line {i+1}: Very short duration ({duration:.2f}s)"
                )
            elif duration > 10.0:
                results['warnings'].append(
                    f"Line {i+1}: Very long duration ({duration:.2f}s)"
                )
            
            durations.append(duration)
            
            # Check gap to next line
            if i < len(lines) - 1:
                next_line = lines[i + 1]
                if hasattr(next_line, 'start_time'):
                    gap = next_line.start_time - line.end_time
                    gaps.append(gap)
                    
                    if gap < 0:
                        results['timing_errors'].append(
                            f"Lines {i+1}-{i+2}: Overlapping timing ({gap:.2f}s)"
                        )
        
        # Calculate statistics
        if durations:
            results['average_duration'] = sum(durations) / len(durations)
        
        if gaps:
            results['min_gap'] = min(gaps)
            results['max_gap'] = max(gaps)
        
        return results