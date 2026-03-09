from unittest.mock import MagicMock, patch

from django.test import TestCase


class AppsIdempotencyGuardTests(TestCase):
    """Test that the FormsConfig.ready() method properly handles idempotency."""

    @patch("djangocms_form_builder.apps.clear_url_caches")
    @patch("djangocms_form_builder.apps.settings")
    @patch("djangocms_form_builder.apps.import_module")
    def test_urls_not_registered_twice_with_same_module(
        self, mock_import, mock_settings, mock_clear_cache
    ):
        """Test that URLs are not registered twice when the same module is already included."""
        # Create a mock urlconf module
        mock_urlconf = MagicMock()

        # Create a mock pattern that already has the form builder urls
        mock_pattern = MagicMock()
        mock_pattern.urlconf_name = "djangocms_form_builder.urls"
        mock_pattern.urlconf_module = None  # Ensure this doesn't match the second check

        mock_urlconf.urlpatterns = [mock_pattern]
        mock_import.return_value = mock_urlconf
        mock_settings.ROOT_URLCONF = "test_urlconf"

        from djangocms_form_builder.apps import FormsConfig

        config = FormsConfig.__new__(FormsConfig)
        config.ready()

        # Verify that urlpatterns was not modified
        self.assertEqual(len(mock_urlconf.urlpatterns), 1)

    @patch("djangocms_form_builder.apps.clear_url_caches")
    @patch("djangocms_form_builder.apps.settings")
    @patch("djangocms_form_builder.apps.import_module")
    def test_urls_not_registered_twice_with_module_attribute(
        self, mock_import, mock_settings, mock_clear_cache
    ):
        """Test that URLs are not registered twice when urlconf_module is already set."""
        # Create a mock urlconf module
        mock_urlconf = MagicMock()

        # Create a mock pattern with urlconf_module attribute
        mock_pattern = MagicMock()
        mock_pattern.urlconf_name = "some.other.path"
        mock_pattern.urlconf_module = MagicMock()
        mock_pattern.urlconf_module.__name__ = "djangocms_form_builder.urls"

        mock_urlconf.urlpatterns = [mock_pattern]
        original_patterns = mock_urlconf.urlpatterns.copy()
        mock_import.return_value = mock_urlconf
        mock_settings.ROOT_URLCONF = "test_urlconf"

        from djangocms_form_builder.apps import FormsConfig

        config = FormsConfig.__new__(FormsConfig)
        config.ready()

        # Verify that urlpatterns was not modified
        self.assertEqual(len(mock_urlconf.urlpatterns), 1)
        self.assertEqual(mock_urlconf.urlpatterns, original_patterns)

    @patch("djangocms_form_builder.apps.clear_url_caches")
    @patch("djangocms_form_builder.apps.settings")
    @patch("djangocms_form_builder.apps.import_module")
    def test_urls_registered_when_not_already_present(
        self, mock_import, mock_settings, mock_clear_cache
    ):
        """Test that URLs are registered when not already present."""
        # Create a mock urlconf module
        mock_urlconf = MagicMock()

        # Create a mock pattern that doesn't have form builder urls
        mock_pattern = MagicMock()
        mock_pattern.urlconf_name = "some.other.urls"

        mock_urlconf.urlpatterns = [mock_pattern]
        mock_import.return_value = mock_urlconf
        mock_settings.ROOT_URLCONF = "test_urlconf"

        from djangocms_form_builder.apps import FormsConfig

        config = FormsConfig.__new__(FormsConfig)
        config.ready()

        # Verify that urlpatterns was modified (new pattern prepended)
        self.assertEqual(len(mock_urlconf.urlpatterns), 2)
