from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, VendaViewSet, ItemVendaViewSet, ContaReceberViewSet

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'vendas', VendaViewSet)
router.register(r'itens-venda', ItemVendaViewSet)
router.register(r'contas-receber', ContaReceberViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
