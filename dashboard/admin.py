from django.contrib import admin
from .models import AccessLog

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'method', 'path', 'ip_address', 'timestamp')
    list_filter = ('method', 'timestamp')
    search_fields = ('user__username', 'path', 'ip_address')
    readonly_fields = ('user', 'method', 'path', 'ip_address', 'timestamp')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
