"""
tests/test_config.py
--------------------
Tests for application configuration and environment variable overrides.
"""

import os
import pytest
from market_data import _get_cache_ttl
from dashboard import _get_request_timeout


def test_market_data_cache_ttl_default(monkeypatch):
    """Verify default cache TTL when environment variable is absent."""
    monkeypatch.delenv("CACHE_TTL_SECONDS", raising=False)
    assert _get_cache_ttl() == 600


def test_market_data_cache_ttl_env_override(monkeypatch):
    """Verify cache TTL can be overridden via CACHE_TTL_SECONDS."""
    monkeypatch.setenv("CACHE_TTL_SECONDS", "120")
    assert _get_cache_ttl() == 120


def test_market_data_cache_ttl_invalid_fallback(monkeypatch):
    """Verify invalid CACHE_TTL_SECONDS safely falls back to default 600."""
    monkeypatch.setenv("CACHE_TTL_SECONDS", "not_a_number")
    assert _get_cache_ttl() == 600


def test_dashboard_request_timeout_default(monkeypatch):
    """Verify default request timeout when environment variable is absent."""
    monkeypatch.delenv("REQUEST_TIMEOUT", raising=False)
    assert _get_request_timeout() == 30


def test_dashboard_request_timeout_env_override(monkeypatch):
    """Verify request timeout can be overridden via REQUEST_TIMEOUT."""
    monkeypatch.setenv("REQUEST_TIMEOUT", "45")
    assert _get_request_timeout() == 45


def test_dashboard_request_timeout_invalid_fallback(monkeypatch):
    """Verify invalid REQUEST_TIMEOUT safely falls back to default 30."""
    monkeypatch.setenv("REQUEST_TIMEOUT", "invalid_timeout")
    assert _get_request_timeout() == 30
