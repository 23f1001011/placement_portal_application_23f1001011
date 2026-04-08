#!/usr/bin/env python
"""
Celery worker startup script that initializes the Flask app context.
This ensures that tasks have access to current_app and other Flask globals.

Usage:
    python celery_worker.py
"""
import os
import sys
from app import create_app, celery as celery_app

# Create Flask app
app = create_app(os.environ.get('FLASK_CONFIG', 'default'))

# Now start the worker with the Flask app context available
if __name__ == '__main__':
    # Import celery's main after app is created
    from celery.bin import worker
    
    # Create a worker instance
    w = worker.worker(app=celery_app)
    
    # Set default options for Windows
    options = {
        'loglevel': 'info',
        'pool': 'solo' if sys.platform == 'win32' else 'prefork',
    }
    
    # Run the worker
    w.run(**options)
