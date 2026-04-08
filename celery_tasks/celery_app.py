from celery import Celery
import os
import sys
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Create Celery instance immediately
celery = Celery(
    'placement_portal',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    pool='solo' if sys.platform == 'win32' else 'prefork'
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Store Flask app reference (will be set by init_app)
_flask_app = None
_context_task = None


def init_app(app):
    """
    Initialize Celery with a Flask app.
    This sets up the app context for tasks and stores mail config.
    """
    global _flask_app, _context_task
    
    _flask_app = app
    
    # Store Flask app and mail in celery config for access in tasks
    # Using update() for Celery 5.x+ compatibility
    celery.conf.update(
        flask_app=app,
        mail=app.extensions.get('mail')
    )
    
    # Auto-discover tasks in the 'celery_tasks' module
    celery.autodiscover_tasks(['celery_tasks'])
    
    # Add Flask context to tasks
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    _context_task = ContextTask
    celery.Task = ContextTask
    
    return celery


# Auto-initialize if running as worker
# This allows 'celery -A celery_tasks.celery_app worker' to work
def _init_worker():
    """Initialize Celery for worker process if app hasn't been initialized yet."""
    global _flask_app
    
    if _flask_app is not None:
        return  # Already initialized
    
    try:
        # Try to import and create the app
        from app import create_app
        app = create_app(os.environ.get('FLASK_CONFIG', 'default'))
        init_app(app)
        print("✅ Celery worker initialized with Flask app context")
    except Exception as e:
        print(f"⚠️  Warning: Could not auto-initialize Flask app for worker: {e}")
        print("   Tasks may fail if they need app context. Run with proper initialization.")


# Trigger worker initialization when this module is imported
_init_worker()
