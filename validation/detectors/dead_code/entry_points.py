"""
Dead Code Detector Validation - Entry Points

This module tests the detector's handling of various entry point patterns
that should prevent functions from being marked as dead code.
"""

# =============================================================================
# MAIN ENTRY POINTS
# =============================================================================

def main():
    """Standard main function entry point."""
    print("Main executed")
    return 0

def cli_main():
    """CLI main function."""
    print("CLI main executed")
    return 0

def app_main():
    """Application main function."""
    print("App main executed")
    return 0

# Standard Python entry point
if __name__ == "__main__":
    main()

# =============================================================================
# SETUP.PY ENTRY POINTS
# =============================================================================

def console_script_entry():
    """Entry point for console script."""
    print("Console script executed")

def gui_script_entry():
    """Entry point for GUI script."""
    print("GUI script executed")

# =============================================================================
# WEB FRAMEWORK ENTRY POINTS
# =============================================================================

def wsgi_application(environ, start_response):
    """WSGI application entry point."""
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello World']

def asgi_application(scope, receive, send):
    """ASGI application entry point."""
    async def app(scope, receive, send):
        await send({
            'type': 'http.response.start',
            'status': 200,
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello World',
        })
    return app(scope, receive, send)

# Flask-style entry points
def create_app():
    """Flask application factory."""
    return "app"

app = create_app()

# =============================================================================
# TEST FRAMEWORK ENTRY POINTS
# =============================================================================

def test_something():
    """Test function that should not be marked as dead."""
    assert True

def test_another_thing():
    """Another test function."""
    assert 1 + 1 == 2

class TestClass:
    """Test class with test methods."""
    
    def test_method(self):
        """Test method that should not be marked as dead."""
        assert True
    
    def setUp(self):
        """Setup method for tests."""
        pass
    
    def tearDown(self):
        """Teardown method for tests."""
        pass

# =============================================================================
# PYTEST FIXTURES
# =============================================================================

def pytest_fixture():
    """Pytest fixture function."""
    return "fixture data"

# =============================================================================
# SIGNAL HANDLERS
# =============================================================================

def signal_handler(signum, frame):
    """Signal handler function."""
    print(f"Signal {signum} received")

# =============================================================================
# CALLBACK REGISTRATIONS
# =============================================================================

def click_handler():
    """Event handler function."""
    print("Click handled")

def error_handler(error):
    """Error handler function."""
    print(f"Error: {error}")

# =============================================================================
# PLUGIN ENTRY POINTS
# =============================================================================

def plugin_init():
    """Plugin initialization function."""
    print("Plugin initialized")

def plugin_setup():
    """Plugin setup function."""
    print("Plugin setup")

def plugin_teardown():
    """Plugin teardown function."""
    print("Plugin teardown")

# =============================================================================
# SERIALIZATION HOOKS
# =============================================================================

def json_serializer(obj):
    """Custom JSON serializer."""
    return str(obj)

def json_deserializer(data):
    """Custom JSON deserializer."""
    return data

# =============================================================================
# ORM HOOKS
# =============================================================================

def before_insert(mapper, connection, target):
    """SQLAlchemy before insert hook."""
    pass

def after_update(mapper, connection, target):
    """SQLAlchemy after update hook."""
    pass

# =============================================================================
# CELERY TASKS
# =============================================================================

def celery_task():
    """Celery task function."""
    return "Task completed"

# =============================================================================
# API ENDPOINTS
# =============================================================================

def api_endpoint():
    """API endpoint function."""
    return {"status": "ok"}

def webhook_handler():
    """Webhook handler function."""
    return {"received": True}

# =============================================================================
# SCHEDULED JOBS
# =============================================================================

def scheduled_job():
    """Scheduled job function."""
    print("Scheduled job executed")

def cron_job():
    """Cron job function."""
    print("Cron job executed")

# =============================================================================
# MIGRATION FUNCTIONS
# =============================================================================

def upgrade():
    """Database upgrade function."""
    print("Database upgraded")

def downgrade():
    """Database downgrade function."""
    print("Database downgraded")

# =============================================================================
# COMMAND LINE FUNCTIONS
# =============================================================================

def cmd_init():
    """Command line init command."""
    print("Initialized")

def cmd_start():
    """Command line start command."""
    print("Started")

def cmd_stop():
    """Command line stop command."""
    print("Stopped")

# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_logger():
    """Logger factory function."""
    return "logger"

def create_database():
    """Database factory function."""
    return "database"

def create_cache():
    """Cache factory function."""
    return "cache"

# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================

def configure_app():
    """Application configuration function."""
    return {"configured": True}

def configure_logging():
    """Logging configuration function."""
    pass

def configure_database():
    """Database configuration function."""
    pass
