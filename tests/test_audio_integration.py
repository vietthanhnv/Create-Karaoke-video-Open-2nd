"""
Integration tests for audio processing and synchronization.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.audio import AudioProcessor, AudioSubtitleSynchronizer
from src.core.models import AudioFile, SubtitleFile
from src.core.validation import ValidationError


class TestAudioProcessingIntegration:
    """Integration tests for complete audio processing workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()
        self.synchronizer = AudioSubtitleSynchronizer()
        
    @patch('subprocess.run')
    def test_complete_audio_processing_workflow(self, mock_run):
        """Test complete workflow from file loading to synchronization."""
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Mock ffprobe output
            mock_output = {
                "streams": [{
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "44100",
                    "channels": 2,
                    "bit_rate": "128000"
                }],
                "format": {
                    "duration": "180.5",
                    "format_name": "mp3",
                    "size": "2304000",
                    "bit_rate": "128000"
                }
            }
            
            mock_run.return_value = Mock(
                stdout=json.dumps(mock_output),
                returncode=0
            )
            
            # Step 1: Load audio file
            audio_file = self.processor.load_audio_file(tmp_path)
            
            assert isinstance(audio_file, AudioFile)
            assert audio_file.duration == 180.5
            assert audio_file.sample_rate == 44100
            assert audio_file.channels == 2
            
            # Step 2: Create mock subtitle file
            subtitle_file = Mock()
            subtitle_file.lines = [
                Mock(start_time=0.0, end_time=5.0, text="First line"),
                Mock(start_time=10.0, end_time=15.0, text="Second line"),
                Mock(start_time=175.0, end_time=180.0, text="Last line")  # Closer to audio duration
            ]
            
            # Step 3: Validate timing
            timing_result = self.processor.validate_audio_duration(
                audio_file, subtitle_file
            )
            
            assert timing_result.is_synchronized == True
            assert timing_result.audio_duration == 180.5
            assert timing_result.subtitle_duration == 180.0
            assert abs(timing_result.timing_offset - 0.5) < 0.1
            
            # Step 4: Analyze synchronization
            sync_analysis = self.synchronizer.analyze_synchronization(
                audio_file, subtitle_file
            )
            
            assert len(sync_analysis.sync_points) > 0
            assert sync_analysis.sync_quality >= 0.0
            assert len(sync_analysis.recommendations) > 0
            
            # Step 5: Generate FFmpeg arguments
            ffmpeg_args = self.processor.create_ffmpeg_audio_args(audio_file)
            
            expected_args = [
                '-i', tmp_path,
                '-c:a', 'aac',
                '-b:a', '128k',
                '-q:a', '2'
            ]
            
            assert ffmpeg_args == expected_args
            
        finally:
            os.unlink(tmp_path)
    
    @patch('subprocess.run')
    def test_audio_subtitle_synchronization_workflow(self, mock_run):
        """Test audio-subtitle synchronization workflow."""
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Mock ffprobe output for WAV file
            mock_output = {
                "streams": [{
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_rate": "48000",
                    "channels": 2,
                    "bit_rate": "1536000"
                }],
                "format": {
                    "duration": "120.0",
                    "format_name": "wav",
                    "size": "23040000",
                    "bit_rate": "1536000"
                }
            }
            
            mock_run.return_value = Mock(
                stdout=json.dumps(mock_output),
                returncode=0
            )
            
            # Load audio file
            audio_file = self.processor.load_audio_file(tmp_path)
            
            # Create subtitle file with timing issues
            subtitle_file = Mock()
            subtitle_file.lines = [
                Mock(start_time=2.0, end_time=7.0, text="Delayed first line"),
                Mock(start_time=12.0, end_time=17.0, text="Delayed second line"),
                Mock(start_time=112.0, end_time=117.0, text="Delayed last line")
            ]
            
            # Analyze synchronization
            analysis = self.synchronizer.analyze_synchronization(
                audio_file, subtitle_file
            )
            
            # Apply timing correction
            correction_applied = self.synchronizer.apply_timing_correction(
                subtitle_file, -2.0  # Advance subtitles by 2 seconds
            )
            
            assert correction_applied == True
            
            # Verify timing was corrected
            assert subtitle_file.lines[0].start_time == 0.0
            assert subtitle_file.lines[0].end_time == 5.0
            assert subtitle_file.lines[1].start_time == 10.0
            assert subtitle_file.lines[1].end_time == 15.0
            assert subtitle_file.lines[2].start_time == 110.0
            assert subtitle_file.lines[2].end_time == 115.0
            
            # Validate timing precision
            precision_results = self.synchronizer.validate_timing_precision(
                subtitle_file
            )
            
            assert precision_results['total_lines'] == 3
            assert precision_results['average_duration'] == 5.0
            
        finally:
            os.unlink(tmp_path)
    
    def test_audio_format_compatibility_check(self):
        """Test audio format compatibility checking."""
        # Test compatible format (AAC)
        audio_file_aac = AudioFile(
            path="test.m4a",
            duration=180.0,
            format="aac"
        )
        
        with patch.object(self.processor, 'extract_metadata') as mock_extract:
            from src.audio.audio_processor import AudioMetadata
            mock_extract.return_value = AudioMetadata(
                duration=180.0,
                sample_rate=44100,
                channels=2,
                bitrate=128000,
                codec='aac',
                format='m4a',
                file_size=2304000
            )
            
            info = self.processor.get_audio_stream_info("test.m4a")
            
            assert info['compatible_with_h264'] == True
            assert info['needs_conversion'] == False
        
        # Test incompatible format (FLAC)
        with patch.object(self.processor, 'extract_metadata') as mock_extract:
            mock_extract.return_value = AudioMetadata(
                duration=180.0,
                sample_rate=44100,
                channels=2,
                bitrate=1000000,
                codec='flac',
                format='flac',
                file_size=23040000
            )
            
            info = self.processor.get_audio_stream_info("test.flac")
            
            assert info['compatible_with_h264'] == False
            assert info['needs_conversion'] == True
    
    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            self.processor.load_audio_file("nonexistent.mp3")
        
        # Test with unsupported format
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError):
                self.processor.load_audio_file(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        # Test synchronization with invalid subtitle file
        audio_file = AudioFile(path="test.mp3", duration=180.0)
        subtitle_file = Mock()
        subtitle_file.lines = None  # Invalid
        
        # Should handle gracefully
        result = self.processor.validate_audio_duration(audio_file, subtitle_file)
        assert result.subtitle_duration == 0.0
    
    @patch('subprocess.run')
    def test_metadata_extraction_edge_cases(self, mock_run):
        """Test metadata extraction with various edge cases."""
        # Test with multiple audio streams
        mock_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "channels": 2,
                    "bit_rate": "128000"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "22050",
                    "channels": 1,
                    "bit_rate": "64000"
                }
            ],
            "format": {
                "duration": "180.5",
                "format_name": "mp4",
                "size": "2304000"
            }
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_output),
            returncode=0
        )
        
        metadata = self.processor.extract_metadata("test.mp4")
        
        # Should use first audio stream
        assert metadata.codec == "aac"
        assert metadata.sample_rate == 44100
        assert metadata.channels == 2
    
    def test_timing_validation_comprehensive(self):
        """Test comprehensive timing validation scenarios."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        
        # Test various timing scenarios
        test_cases = [
            {
                'name': 'perfect_sync',
                'lines': [
                    Mock(start_time=0.0, end_time=5.0),
                    Mock(start_time=10.0, end_time=15.0),
                    Mock(start_time=175.0, end_time=180.0)
                ],
                'expected_sync': True
            },
            {
                'name': 'minor_mismatch',
                'lines': [
                    Mock(start_time=0.0, end_time=5.0),
                    Mock(start_time=10.0, end_time=15.0),
                    Mock(start_time=175.0, end_time=178.0)  # 2 second difference
                ],
                'expected_sync': True  # Within tolerance
            },
            {
                'name': 'major_mismatch',
                'lines': [
                    Mock(start_time=0.0, end_time=5.0),
                    Mock(start_time=10.0, end_time=15.0),
                    Mock(start_time=100.0, end_time=105.0)  # 75 second difference
                ],
                'expected_sync': False
            }
        ]
        
        for case in test_cases:
            subtitle_file = Mock()
            subtitle_file.lines = case['lines']
            
            result = self.processor.validate_audio_duration(audio_file, subtitle_file)
            
            assert result.is_synchronized == case['expected_sync'], \
                f"Failed for case: {case['name']}"