"""
Request Logging Middleware

This middleware adds unique request IDs to all logs for easier tracing
and debugging in production environments.
"""

import logging
import uuid
from threading import local

_thread_locals = local()


def get_request_context():
    """Get the current request context for logging"""
    return getattr(_thread_locals, 'request_id', 'no-request'), getattr(_thread_locals, 'user_id', 'no-user')


class RequestContextFilter(logging.Filter):
    """Logging filter that adds request_id and user_id to log records"""
    
    def filter(self, record):
        request_id, user_id = get_request_context()
        record.request_id = request_id
        record.user_id = user_id
        return True


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Add the filter to all relevant handlers
        for logger_name in ['errors', 'general', 'activity', 'django']:
            logger = logging.getLogger(logger_name)
            if not any(isinstance(f, RequestContextFilter) for f in logger.filters):
                logger.addFilter(RequestContextFilter())

    def __call__(self, request):
        # Set request context in thread-local storage
        request.id = str(uuid.uuid4())[:8]
        _thread_locals.request_id = request.id
        
        # Safely get user_id
        user_id = 'no-user'
        if hasattr(request, 'user') and request.user:
            if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
                user_id = getattr(request.user, 'id', 'anonymous')
            else:
                user_id = 'anonymous'
        _thread_locals.user_id = user_id
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up thread-local storage
            _thread_locals.request_id = 'no-request'
            _thread_locals.user_id = 'no-user'
