import logging
from django.db import OperationalError
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class DatabaseHealthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except OperationalError as exc:
            logger.error(f"Database operational error encountered: {exc}", exc_info=True)
            return JsonResponse({'detail': 'Database temporarily unavailable please retry'}, status=503)

    def process_exception(self, request, exception):
        if isinstance(exception, OperationalError):
            logger.error(f"Database operational error in process_exception: {exception}", exc_info=True)
            return JsonResponse({'detail': 'Database temporarily unavailable please retry'}, status=503)
        return None
