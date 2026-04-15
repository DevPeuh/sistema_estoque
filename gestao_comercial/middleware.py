import time
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.db import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class LoginRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/api/token/' and request.method == 'POST':
            ip = self._get_client_ip(request)
            cache_key = f'login_rl:{ip}'
            current = cache.get(cache_key, 0)
            if current >= settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
                return JsonResponse(
                    {'detail': 'Muitas tentativas de login. Tente novamente em instantes.'},
                    status=429
                )
            cache.set(cache_key, current + 1, timeout=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            response = JsonResponse({}, status=200)
        else:
            response = self.get_response(request)

        origin = request.headers.get('Origin')
        if origin and origin in settings.CORS_ALLOWED_ORIGINS:
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'

        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('Referrer-Policy', 'same-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=(self)')
        response.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com https://cdnjs.cloudflare.com;"
        )
        return response


class ApiExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except (ProgrammingError, OperationalError) as exc:
            logger.exception('Falha crítica de banco ao processar %s %s: %s', request.method, request.path, str(exc))
            if request.path.startswith('/api/'):
                detail = 'Falha de estrutura do banco de dados. Execute as migrações pendentes com: python manage.py migrate'
                return JsonResponse({'detail': detail, 'code': 'schema_outdated'}, status=503)
            raise
