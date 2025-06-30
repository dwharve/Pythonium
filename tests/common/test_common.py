"""
Unit tests for the common package.

This module contains unit tests for all components in the pythonium.common package.
"""

import pytest

from tests.conftest import BaseTestCase


class TestCommonPackage(BaseTestCase):
    """Test the common package initialization."""

    def test_package_import(self):
        """Test that the common package can be imported."""
        # This will be implemented once we have actual modules
        assert True  # Placeholder

    def test_package_version(self):
        """Test that the package has a version."""
        from pythonium.common import __version__

        assert __version__ == "0.1.0"


# More specific test classes will be added as we implement the modules
