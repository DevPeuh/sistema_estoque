from django.db import connection
from django.db.models import F, Sum
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sales.models import Venda, ItemVenda
from purchases.models import ContaPagar
from sales.models import ContaReceber
from products.models import Produto

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        vendas_pagas = Venda.objects.filter(status_pagamento='pago')

        # Vendas do dia e mês
        vendas_dia = vendas_pagas.filter(data_venda__date=today).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        vendas_mes = vendas_pagas.filter(data_venda__date__gte=month_start).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        
        # Produtos mais vendidos (top 5)
        top_produtos = (
            ItemVenda.objects
            .filter(venda__status_pagamento='pago', produto__isnull=False)
            .values('produto__descricao')
            .annotate(total_vendido=Sum('quantidade'))
            .order_by('-total_vendido')[:5]
        )
        
        # Alertas de estoque baixo
        estoque_baixo = Produto.objects.filter(estoque_atual__lte=F('estoque_minimo')).count()
        
        # Contas a pagar/receber pendentes
        contas_pagar_pendentes = ContaPagar.objects.filter(status__in=['pendente', 'atrasado']).aggregate(Sum('valor'))['valor__sum'] or 0
        contas_receber_pendentes = ContaReceber.objects.filter(status='pendente').aggregate(Sum('valor'))['valor__sum'] or 0
        
        return Response({
            'vendas_dia': vendas_dia,
            'vendas_mes': vendas_mes,
            'top_produtos': top_produtos,
            'estoque_baixo_count': estoque_baixo,
            'contas_pagar_pendentes': contas_pagar_pendentes,
            'contas_receber_pendentes': contas_receber_pendentes,
        })


class DashboardHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            db_ok = cursor.fetchone()[0] == 1
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        return Response({
            'database_ok': db_ok,
            'pending_migrations': len(plan),
            'status': 'ok' if db_ok and len(plan) == 0 else 'warning'
        })
