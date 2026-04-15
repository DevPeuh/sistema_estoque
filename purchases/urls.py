from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FornecedorViewSet, CompraViewSet, ItemCompraViewSet, ContaPagarViewSet

router = DefaultRouter()
router.register(r'fornecedores', FornecedorViewSet)
router.register(r'compras', CompraViewSet)
router.register(r'itens-compra', ItemCompraViewSet)
router.register(r'contas-pagar', ContaPagarViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
