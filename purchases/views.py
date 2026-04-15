from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Fornecedor, Compra, ItemCompra, ContaPagar
from .serializers import FornecedorSerializer, CompraSerializer, ItemCompraSerializer, ContaPagarSerializer
from dashboard.models import DeletionAuditLog

class FornecedorViewSet(viewsets.ModelViewSet):
    queryset = Fornecedor.objects.filter(ativo=True).order_by('razao_social')
    serializer_class = FornecedorSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'fornecedores'

    def create(self, request, *args, **kwargs):
        cnpj = ''.join(ch for ch in str(request.data.get('cnpj') or '') if ch.isdigit())
        if len(cnpj) not in (11, 14):
            return Response({'detail': 'CNPJ/CPF deve conter 11 ou 14 dígitos.'}, status=status.HTTP_400_BAD_REQUEST)
        fornecedor_existente = Fornecedor.objects.filter(cnpj=cnpj).first()
        if fornecedor_existente and fornecedor_existente.ativo:
            return Response({'detail': 'Já existe fornecedor ativo com este CNPJ/CPF.'}, status=status.HTTP_400_BAD_REQUEST)
        if fornecedor_existente and not fornecedor_existente.ativo:
            fornecedor_existente.ativo = True
            fornecedor_existente.razao_social = (request.data.get('razao_social') or fornecedor_existente.razao_social).strip()
            fornecedor_existente.nome_fantasia = (request.data.get('nome_fantasia') or fornecedor_existente.nome_fantasia or fornecedor_existente.razao_social).strip()
            fornecedor_existente.contato_nome = (request.data.get('contato_nome') or fornecedor_existente.contato_nome or fornecedor_existente.razao_social).strip()
            fornecedor_existente.telefone = (request.data.get('telefone') or fornecedor_existente.telefone).strip()
            raw_email = request.data.get('email')
            fornecedor_existente.email = (str(raw_email).strip() if raw_email else fornecedor_existente.email)
            fornecedor_existente.endereco = (request.data.get('endereco') or fornecedor_existente.endereco or 'Não informado').strip()
            fornecedor_existente.save()
            serializer = self.get_serializer(fornecedor_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)
        mutable = request.data.copy()
        mutable['cnpj'] = cnpj
        if not mutable.get('contato_nome'):
            mutable['contato_nome'] = mutable.get('razao_social')
        if not mutable.get('nome_fantasia'):
            mutable['nome_fantasia'] = mutable.get('razao_social')
        if not mutable.get('endereco'):
            mutable['endereco'] = 'Não informado'
        serializer = self.get_serializer(data=mutable)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm('purchases.delete_fornecedor'):
            return Response({'detail': 'Você não tem permissão para excluir fornecedor.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        has_dependencies = instance.compras.exists() or instance.contapagar_set.exists()
        with transaction.atomic():
            if has_dependencies:
                instance.ativo = False
                instance.save(update_fields=['ativo'])
                DeletionAuditLog.objects.create(
                    user=request.user,
                    ip_address=self._get_client_ip(request),
                    model_name='Fornecedor',
                    object_id=str(instance.id),
                    object_repr=instance.razao_social,
                    action='soft_delete',
                    reason='Fornecedor vinculado a compras/contas. Registro desativado.'
                )
                return Response({'detail': 'Fornecedor vinculado a compras e desativado com sucesso.'}, status=status.HTTP_200_OK)
            DeletionAuditLog.objects.create(
                user=request.user,
                ip_address=self._get_client_ip(request),
                model_name='Fornecedor',
                object_id=str(instance.id),
                object_repr=instance.razao_social,
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

class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.all().order_by('-data_emissao')
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'compras'

class ItemCompraViewSet(viewsets.ModelViewSet):
    queryset = ItemCompra.objects.all()
    serializer_class = ItemCompraSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'compras'

class ContaPagarViewSet(viewsets.ModelViewSet):
    queryset = ContaPagar.objects.all()
    serializer_class = ContaPagarSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'financeiro'

    def get_queryset(self):
        queryset = ContaPagar.objects.select_related('fornecedor', 'compra').all().order_by('data_vencimento')
        status_param = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        min_valor = self.request.query_params.get('min_valor')
        max_valor = self.request.query_params.get('max_valor')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if date_from:
            queryset = queryset.filter(data_vencimento__gte=date_from)
        if date_to:
            queryset = queryset.filter(data_vencimento__lte=date_to)
        if min_valor:
            queryset = queryset.filter(valor__gte=min_valor)
        if max_valor:
            queryset = queryset.filter(valor__lte=max_valor)
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        today = timezone.now().date()
        base = ContaPagar.objects.all()
        pendentes = base.filter(status__in=['pendente', 'atrasado'])
        total_pendente = pendentes.aggregate(total=Sum('valor'))['total'] or 0
        vencidas = pendentes.filter(data_vencimento__lt=today).count()
        proximas = pendentes.filter(data_vencimento__gte=today, data_vencimento__lte=today + timezone.timedelta(days=7)).count()
        fluxo = (
            pendentes.annotate(mes=TruncMonth('data_vencimento'))
            .values('mes')
            .annotate(total=Sum('valor'))
            .order_by('mes')
        )
        return Response({
            'total_pendente': total_pendente,
            'vencidas': vencidas,
            'proximas_vencer': proximas,
            'fluxo_caixa_previsto': [{'mes': item['mes'], 'total': item['total']} for item in fluxo]
        })
