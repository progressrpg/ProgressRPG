"""
Request Logging Middleware

This middleware adds unique request IDs to all logs for easier tracing
and debugging in production environments.
"""

import logging
import uuid


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.id = str(uuid.uuid4())[:8]
        
        # Add request_id to all log records
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = getattr(request, 'id', 'no-request')
            record.user_id = getattr(request.user, 'id', 'anonymous') if hasattr(request, 'user') else 'no-user'
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        try:
            response = self.get_response(request)
            return response
        finally:
            logging.setLogRecordFactory(old_factory)
