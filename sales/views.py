from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Cliente, Venda, ItemVenda, ContaReceber
from .serializers import ClienteSerializer, VendaSerializer, ItemVendaSerializer, ContaReceberSerializer
from dashboard.models import DeletionAuditLog

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.filter(ativo=True).order_by('nome')
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'clientes'

    def create(self, request, *args, **kwargs):
        cpf_cnpj = request.data.get('cpf_cnpj')
        normalized = ''.join(ch for ch in str(cpf_cnpj) if ch.isdigit()) if cpf_cnpj else None
        if normalized:
            cliente_existente = Cliente.objects.filter(cpf_cnpj=normalized).first()
            if cliente_existente and cliente_existente.ativo:
                return Response({'detail': 'Já existe cliente ativo com este CPF/CNPJ.'}, status=status.HTTP_400_BAD_REQUEST)
            if cliente_existente and not cliente_existente.ativo:
                cliente_existente.ativo = True
                cliente_existente.nome = (request.data.get('nome') or cliente_existente.nome).strip()
                cliente_existente.telefone = request.data.get('telefone') or cliente_existente.telefone
                cliente_existente.email = request.data.get('email') or cliente_existente.email
                cliente_existente.endereco_entrega = request.data.get('endereco_entrega') or cliente_existente.endereco_entrega
                cliente_existente.save()
                serializer = self.get_serializer(cliente_existente)
                return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm('sales.delete_cliente'):
            return Response({'detail': 'Você não tem permissão para excluir cliente.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        has_dependencies = instance.vendas.exists() or instance.contareceber_set.exists()
        with transaction.atomic():
            if has_dependencies:
                instance.ativo = False
                instance.save(update_fields=['ativo'])
                DeletionAuditLog.objects.create(
                    user=request.user,
                    ip_address=self._get_client_ip(request),
                    model_name='Cliente',
                    object_id=str(instance.id),
                    object_repr=instance.nome,
                    action='soft_delete',
                    reason='Cliente vinculado a vendas/contas. Registro desativado.'
                )
                return Response({'detail': 'Cliente vinculado a vendas e desativado com sucesso.'}, status=status.HTTP_200_OK)
            DeletionAuditLog.objects.create(
                user=request.user,
                ip_address=self._get_client_ip(request),
                model_name='Cliente',
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

class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all().order_by('-data_venda')
    serializer_class = VendaSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'vendas'

class ItemVendaViewSet(viewsets.ModelViewSet):
    queryset = ItemVenda.objects.all()
    serializer_class = ItemVendaSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'vendas'

class ContaReceberViewSet(viewsets.ModelViewSet):
    queryset = ContaReceber.objects.all()
    serializer_class = ContaReceberSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'financeiro'

    def get_queryset(self):
        queryset = ContaReceber.objects.select_related('cliente', 'venda').all().order_by('data_vencimento')
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
        base = ContaReceber.objects.all()
        a_receber = base.filter(status='pendente')
        monitoradas = base.filter(status__in=['pendente', 'atrasado'])
        total_pendente = a_receber.aggregate(total=Sum('valor'))['total'] or 0
        vencidas = monitoradas.filter(data_vencimento__lt=today).count()
        proximas = monitoradas.filter(data_vencimento__gte=today, data_vencimento__lte=today + timezone.timedelta(days=7)).count()
        fluxo = (
            a_receber.annotate(mes=TruncMonth('data_vencimento'))
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
