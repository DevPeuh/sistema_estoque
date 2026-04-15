from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, CategoriaViewSet, UnidadeDeMedidaViewSet, MovimentacaoEstoqueViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'unidades-de-medida', UnidadeDeMedidaViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'movimentacoes-estoque', MovimentacaoEstoqueViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
