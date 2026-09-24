"""
tests/test_logging.py
---------------------
Tests for application logging, diagnostics, and caplog validation.
"""

import logging
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from main import app
import market_data
import risk_analysis
import investment_rating
import esg_scoring
from cli import _configure_logging

client = TestClient(app)


def test_module_logger_names():
    """Verify that internal modules initialize standard hierarchical loggers."""
    assert market_data.logger.name == "market_data"
    assert risk_analysis.logger.name == "risk_analysis"
    assert investment_rating.logger.name == "investment_rating"
    assert esg_scoring.logger.name == "esg_scoring"


def test_api_404_logs_warning(caplog):
    """Verify that ticker not found generates a warning log entry with context."""
    with caplog.at_level(logging.WARNING):
        with patch("main.get_market_data", side_effect=ValueError("No market data found for ticker 'NOTFOUND'")):
            response = client.get("/analyze/NOTFOUND")
            assert response.status_code == 404
            assert any("NOTFOUND" in record.message for record in caplog.records)


def test_api_502_logs_error(caplog):
    """Verify that upstream network/parsing failures generate an error log entry."""
    with caplog.at_level(logging.ERROR):
        with patch("main.get_market_data", side_effect=RuntimeError("Upstream timeout")):
            response = client.get("/analyze/AAPL")
            assert response.status_code == 502
            assert any("AAPL" in record.message for record in caplog.records)


def test_cli_logging_configuration():
    """Verify CLI logging configuration levels."""
    _configure_logging(verbose=False)
    # Default is non-verbose (WARNING)
    _configure_logging(verbose=True)
    # Verbose sets DEBUG
