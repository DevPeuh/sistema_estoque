from django.urls import path
from .views import DashboardHealthView, DashboardStatsView

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('health/', DashboardHealthView.as_view(), name='dashboard-health'),
]
