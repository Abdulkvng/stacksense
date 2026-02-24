"""
Tests for utility functions
"""

import pytest
from stacksense.utils.helpers import (
    format_cost,
    format_tokens,
    parse_model_name,
    calculate_rate_limit
)


def test_format_cost():
    """Test cost formatting."""
    assert format_cost(0.0001) == "$0.0001"
    assert format_cost(1.23) == "$1.23"
    assert format_cost(100.50) == "$100.50"


def test_format_tokens():
    """Test token formatting."""
    assert format_tokens(100) == "100"
    assert format_tokens(1000) == "1.00K"
    assert format_tokens(1000000) == "1.00M"


def test_parse_model_name():
    """Test model name parsing."""
    result = parse_model_name("gpt-4")
    assert result["provider"] == "openai"
    assert result["model_name"] == "gpt-4"
    
    result = parse_model_name("claude-3-5-sonnet")
    assert result["provider"] == "anthropic"


def test_calculate_rate_limit():
    """Test rate limit calculation."""
    assert calculate_rate_limit(100, 10) == 10.0
    assert calculate_rate_limit(0, 10) == 0.0
    assert calculate_rate_limit(1000, 60) == pytest.approx(16.67, rel=0.01)


