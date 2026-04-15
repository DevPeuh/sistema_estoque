from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Produto, Categoria, UnidadeDeMedida, MovimentacaoEstoque
from .serializers import ProdutoSerializer, CategoriaSerializer, UnidadeDeMedidaSerializer, MovimentacaoEstoqueSerializer
from dashboard.models import DeletionAuditLog

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.filter(ativo=True).order_by('nome')
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'categorias'

    def create(self, request, *args, **kwargs):
        nome = (request.data.get('nome') or '').strip()
        if not nome:
            return Response({'detail': 'O nome da categoria é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        categoria_existente = Categoria.objects.filter(nome__iexact=nome).first()
        if categoria_existente and categoria_existente.ativo:
            return Response({'detail': 'Já existe uma categoria ativa com este nome.'}, status=status.HTTP_400_BAD_REQUEST)
        if categoria_existente and not categoria_existente.ativo:
            categoria_existente.nome = nome
            categoria_existente.ativo = True
            categoria_existente.save(update_fields=['nome', 'ativo'])
            serializer = self.get_serializer(categoria_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm('products.delete_categoria'):
            return Response({'detail': 'Você não tem permissão para excluir categoria.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        if instance.produtos.exists():
            instance.ativo = False
            instance.save(update_fields=['ativo'])
            DeletionAuditLog.objects.create(
                user=request.user,
                ip_address=self._get_client_ip(request),
                model_name='Categoria',
                object_id=str(instance.id),
                object_repr=instance.nome,
                action='soft_delete',
                reason='Categoria vinculada a produtos. Registro desativado.'
            )
            return Response({'detail': 'Categoria vinculada a produtos e desativada com sucesso.'}, status=status.HTTP_200_OK)
        with transaction.atomic():
            DeletionAuditLog.objects.create(
                user=request.user,
                ip_address=self._get_client_ip(request),
                model_name='Categoria',
                object_id=str(instance.id),
                object_repr=instance.nome,
                action='hard_delete',
                reason='Exclusão definitiva sem vínculos.'
            )
            instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class UnidadeDeMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadeDeMedida.objects.all()
    serializer_class = UnidadeDeMedidaSerializer

class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.filter(ativo=True).order_by('descricao')
    serializer_class = ProdutoSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'produtos'

    def create(self, request, *args, **kwargs):
        sku = (request.data.get('sku') or '').strip()
        if not sku:
            return Response({'detail': 'Informe o nome do produto.'}, status=status.HTTP_400_BAD_REQUEST)
        existing_active = Produto.objects.filter(sku__iexact=sku, ativo=True).first()
        if existing_active:
            return Response({'detail': 'Produto com este Nome do Produto já existe.'}, status=status.HTTP_400_BAD_REQUEST)
        existing_inactive = Produto.objects.filter(sku__iexact=sku, ativo=False).first()
        if existing_inactive:
            mutable = request.data.copy()
            barcode = (mutable.get('codigo_barras') or '').strip()
            mutable['codigo_barras'] = barcode or None
            serializer = self.get_serializer(existing_inactive, data=mutable)
            serializer.is_valid(raise_exception=True)
            produto = serializer.save(ativo=True)
            response_serializer = self.get_serializer(produto)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(ativo=True)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm('products.delete_produto'):
            return Response({'detail': 'Você não tem permissão para excluir produto.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        has_dependencies = (
            instance.movimentacoes.exists()
            or instance.itemvenda_set.exists()
            or instance.itemcompra_set.exists()
        )
        with transaction.atomic():
            if has_dependencies:
                instance.ativo = False
                instance.save(update_fields=['ativo'])
                DeletionAuditLog.objects.create(
                    user=request.user,
                    ip_address=self._get_client_ip(request),
                    model_name='Produto',
                    object_id=str(instance.id),
                    object_repr=instance.descricao,
                    action='soft_delete',
                    reason='Produto com histórico de movimentação/venda/compra. Registro desativado.'
                )
                return Response(
                    {'detail': 'Produto possui histórico e foi desativado para preservar integridade dos dados.'},
                    status=status.HTTP_200_OK
                )
            DeletionAuditLog.objects.create(
                user=request.user,
                ip_address=self._get_client_ip(request),
                model_name='Produto',
                object_id=str(instance.id),
                object_repr=instance.descricao,
                action='hard_delete',
                reason='Exclusão definitiva sem vínculos.'
            )
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def get_queryset(self):
        queryset = Produto.objects.select_related('categoria', 'unidade_medida').filter(ativo=True).order_by('descricao')
        categoria = self.request.query_params.get('categoria')
        search = self.request.query_params.get('search')
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if search:
            queryset = queryset.filter(
                Q(descricao__icontains=search) |
                Q(sku__icontains=search) |
                Q(codigo_barras__icontains=search)
            )
        return queryset

class MovimentacaoEstoqueViewSet(viewsets.ModelViewSet):
    queryset = MovimentacaoEstoque.objects.all()
    serializer_class = MovimentacaoEstoqueSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'produtos'
