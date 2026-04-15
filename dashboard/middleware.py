from .models import AccessLog

class AccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Log only authenticated requests or certain paths if needed
        AccessLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            ip_address=self.get_client_ip(request),
            path=request.path,
            method=request.method
        )
        
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
