from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def full_profile_html() -> str:
    return load_fixture("profile_full.html")


@pytest.fixture
def minimal_profile_html() -> str:
    return load_fixture("profile_minimal.html")


@pytest.fixture
def malformed_profile_html() -> str:
    return load_fixture("profile_malformed.html")


@pytest.fixture
def mobile_full_html() -> str:
    return load_fixture("profile_mobile_full.html")


@pytest.fixture
def mobile_full_soup(mobile_full_html: str) -> BeautifulSoup:
    return BeautifulSoup(mobile_full_html, "lxml")


@pytest.fixture
def mobile_minimal_html() -> str:
    return load_fixture("profile_mobile_minimal.html")


@pytest.fixture
def mobile_minimal_soup(mobile_minimal_html: str) -> BeautifulSoup:
    return BeautifulSoup(mobile_minimal_html, "lxml")
