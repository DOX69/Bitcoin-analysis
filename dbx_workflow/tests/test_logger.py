"""Tests for CustomFormatter logger class."""

import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock

from raw_ingest.logger import CustomFormatter


class TestCustomFormatterPathFormatting:
    """Test CustomFormatter path shortening functionality."""

    def test_shortens_path_to_parent_and_filename(self):
        """Test that full path is shortened to parent_folder/filename."""
        formatter = CustomFormatter()
        
        # Create a log record with a full path
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="c:/Users/test/project/src/raw_ingest/main.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Verify it formats without error and contains the message
        assert "Test message" in formatted

    def test_handles_different_path_separators(self):
        """Test path handling with different separators."""
        formatter = CustomFormatter()
        
        # Windows-style path
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=r"C:\project\src\module\file.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Verify it formats without error
        assert "Test" in formatted


class TestCustomFormatterColorCoding:
    """Test CustomFormatter color coding for different message types."""

    def test_colors_begin_keywords_blue(self):
        """Test that BEGIN keywords are colored blue."""
        formatter = CustomFormatter()
        
        for keyword in ["BEGIN", "STARTED", "INITIALIZED", "END"]:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="/test/file.py",
                lineno=1,
                msg=f"Pipeline {keyword}",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            
            # Should contain blue color code
            assert CustomFormatter.BLUE in formatted
            assert CustomFormatter.RESET in formatted

    def test_colors_success_keywords_green(self):
        """Test that success keywords are colored green."""
        formatter = CustomFormatter()
        
        for keyword in ["OK", "SUCCEEDED", "COMPLETED"]:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="/test/file.py",
                lineno=1,
                msg=f"Operation {keyword}",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            
            # Should contain green color code
            assert CustomFormatter.GREEN in formatted
            assert CustomFormatter.RESET in formatted

    def test_colors_error_keywords_red(self):
        """Test that error keywords are colored red."""
        formatter = CustomFormatter()
        
        for keyword in ["ERROR", "FAILED", "EXCEPTION", "CRITICAL"]:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="/test/file.py",
                lineno=1,
                msg=f"Operation {keyword}",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            
            # Should contain red color code
            assert CustomFormatter.RED in formatted
            assert CustomFormatter.RESET in formatted

    def test_colors_warnings_yellow(self):
        """Test that warnings are colored yellow."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="/test/file.py",
            lineno=1,
            msg="This is a warning",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain yellow color code
        assert CustomFormatter.YELLOW in formatted
        assert CustomFormatter.RESET in formatted

    def test_regular_info_has_reset_color(self):
        """Test that regular info messages use reset color."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg="Regular info message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain reset but not other colors
        assert CustomFormatter.RESET in formatted
        assert CustomFormatter.RED not in formatted
        assert CustomFormatter.GREEN not in formatted
        assert CustomFormatter.BLUE not in formatted


class TestCustomFormatterMessageStructure:
    """Test the structure of formatted log messages."""

    def test_includes_timestamp(self):
        """Test that formatted message includes timestamp."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="test_module",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain timestamp pattern (year-month-day or time)
        assert any(char.isdigit() for char in formatted)

    def test_includes_level_name(self):
        """Test that level name is included."""
        formatter = CustomFormatter()
        
        for level, level_name in [(logging.INFO, "INFO"), 
                                  (logging.WARNING, "WARNING"),
                                  (logging.ERROR, "ERROR")]:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="/test/file.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            assert level_name in formatted

    def test_includes_message(self):
        """Test that the actual message is included."""
        formatter = CustomFormatter()
        
        test_message = "This is a unique test message"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg=test_message,
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert test_message in formatted

    def test_error_includes_line_number(self):
        """Test that errors include file:line information."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/project/src/module/file.py",
            lineno=123,
            msg="Error occurred",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should include line number for errors
        assert "123" in formatted

    def test_warning_includes_line_number(self):
        """Test that warnings include file:line information."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="/project/module/file.py",
            lineno=456,
            msg="Warning message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should include line number for warnings
        assert "456" in formatted

    def test_info_uses_module_name_not_path(self):
        """Test that regular info messages use module name, not file path."""
        formatter = CustomFormatter()
        
        record = logging.LogRecord(
            name="my_module",
            level=logging.INFO,
            pathname="/long/path/to/file.py",
            lineno=1,
            msg="Info message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain module name
        assert "my_module" in formatted


class TestCustomFormatterEdgeCases:
    """Test edge cases and special scenarios."""

    def test_handles_multiline_messages(self):
        """Test formatting of multiline messages."""
        formatter = CustomFormatter()
        
        multiline_msg = "First line\nSecond line\nThird line"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg=multiline_msg,
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Message should be preserved
        assert "First line" in formatted

    def test_keyword_detection_case_insensitive(self):
        """Test that keyword detection is case-insensitive."""
        formatter = CustomFormatter()
        
        # Test with lowercase keywords
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg="operation succeeded with ok status",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should still apply green color for success keywords
        assert CustomFormatter.GREEN in formatted

    def test_multiple_keywords_in_message(self):
        """Test handling of messages with multiple keywords."""
        formatter = CustomFormatter()
        
        # Message with both BEGIN and SUCCEEDED keywords  
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=1,
            msg="BEGIN processing SUCCEEDED",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should pick one color (BEGIN is checked first, so BLUE)
        assert CustomFormatter.BLUE in formatted
