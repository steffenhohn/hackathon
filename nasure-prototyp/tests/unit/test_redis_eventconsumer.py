"""Unit tests for Redis event consumer filtering logic."""

import pytest
from unittest.mock import Mock, patch
from lab_dp.entrypoints.redis_eventconsumer import is_laborbericht, handle_bundle_stored


class TestIsLaborbericht:
    """Test the is_laborbericht filtering function."""

    def test_returns_true_for_laborbericht_code(self):
        """Test that Laborbericht code 4241000179101 returns True."""
        bundle_type = ("4241000179101", "Laborbericht")
        assert is_laborbericht(bundle_type) is True

    def test_returns_false_for_other_codes(self):
        """Test that other codes return False."""
        bundle_type = ("9999999999999", "Other Report Type")
        assert is_laborbericht(bundle_type) is False

    def test_returns_false_for_empty_tuple(self):
        """Test that empty tuple returns False."""
        assert is_laborbericht(()) is False

    def test_returns_false_for_none(self):
        """Test that None returns False."""
        assert is_laborbericht(None) is False

    def test_handles_list_format(self):
        """Test that list format is also handled (for compatibility)."""
        bundle_type = ["4241000179101", "Laborbericht"]
        assert is_laborbericht(bundle_type) is True

    def test_returns_false_for_list_with_wrong_code(self):
        """Test that list with wrong code returns False."""
        bundle_type = ["9999999999999", "Other Report"]
        assert is_laborbericht(bundle_type) is False


class TestHandleBundleStoredFiltering:
    """Test that handle_bundle_stored correctly filters by bundle_type."""

    @patch('lab_dp.entrypoints.redis_eventconsumer.messagebus')
    @patch('lab_dp.entrypoints.redis_eventconsumer.SqlAlchemyUnitOfWork')
    def test_processes_laborbericht_bundle(self, mock_uow, mock_messagebus):
        """Test that Laborbericht bundles are processed."""
        message = {
            "data": '{"bundle_id": "test-123", "bundle_type": ["4241000179101", "Laborbericht"]}'
        }

        handle_bundle_stored(message)

        # Should have created the command and processed it
        mock_messagebus.handle.assert_called_once()
        call_args = mock_messagebus.handle.call_args
        assert call_args[0][0].bundle_id == "test-123"

    @patch('lab_dp.entrypoints.redis_eventconsumer.messagebus')
    @patch('lab_dp.entrypoints.redis_eventconsumer.SqlAlchemyUnitOfWork')
    def test_skips_non_laborbericht_bundle(self, mock_uow, mock_messagebus):
        """Test that non-Laborbericht bundles are skipped."""
        message = {
            "data": '{"bundle_id": "test-456", "bundle_type": ["9999999999999", "Other Report"]}'
        }

        handle_bundle_stored(message)

        # Should NOT have processed the bundle
        mock_messagebus.handle.assert_not_called()

    @patch('lab_dp.entrypoints.redis_eventconsumer.messagebus')
    @patch('lab_dp.entrypoints.redis_eventconsumer.SqlAlchemyUnitOfWork')
    def test_skips_bundle_with_no_bundle_type(self, mock_uow, mock_messagebus):
        """Test that bundles without bundle_type are skipped."""
        message = {
            "data": '{"bundle_id": "test-789"}'
        }

        handle_bundle_stored(message)

        # Should NOT have processed the bundle
        mock_messagebus.handle.assert_not_called()

    @patch('lab_dp.entrypoints.redis_eventconsumer.messagebus')
    @patch('lab_dp.entrypoints.redis_eventconsumer.SqlAlchemyUnitOfWork')
    def test_skips_bundle_with_empty_bundle_type(self, mock_uow, mock_messagebus):
        """Test that bundles with empty bundle_type are skipped."""
        message = {
            "data": '{"bundle_id": "test-999", "bundle_type": null}'
        }

        handle_bundle_stored(message)

        # Should NOT have processed the bundle
        mock_messagebus.handle.assert_not_called()

    @patch('lab_dp.entrypoints.redis_eventconsumer.messagebus')
    @patch('lab_dp.entrypoints.redis_eventconsumer.SqlAlchemyUnitOfWork')
    def test_processes_laborbericht_tuple_format(self, mock_uow, mock_messagebus):
        """Test that tuple format (code, display) works correctly."""
        # Note: JSON doesn't have tuples, so this would come as a list
        message = {
            "data": '{"bundle_id": "test-tuple", "bundle_type": ["4241000179101", "Laborbericht"]}'
        }

        handle_bundle_stored(message)

        # Should have processed the bundle
        mock_messagebus.handle.assert_called_once()
