# conftest.py — pytest configuration
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require external dependencies (chromadb, etc.)"
    )
