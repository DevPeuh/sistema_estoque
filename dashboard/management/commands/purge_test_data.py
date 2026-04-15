from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Categoria, Produto, UnidadeDeMedida, MovimentacaoEstoque
from purchases.models import Fornecedor, Compra, ItemCompra, ContaPagar
from sales.models import Cliente, Venda, ItemVenda, ContaReceber
from dashboard.models import AccessLog


class Command(BaseCommand):
    help = 'Remove dados de teste do SQLite antes da migração para produção.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='Executa a limpeza.')

    def handle(self, *args, **options):
        markers = ['teste', 'test', 'demo', 'sample', 'qa', 'dev']
        User = get_user_model()
        users_qs = User.objects.filter(username__iregex='|'.join(markers))
        clientes_qs = Cliente.objects.filter(nome__iregex='|'.join(markers))
        fornecedores_qs = Fornecedor.objects.filter(razao_social__iregex='|'.join(markers))
        produtos_qs = Produto.objects.filter(descricao__iregex='|'.join(markers))

        summary = {
            'users': users_qs.count(),
            'clientes': clientes_qs.count(),
            'fornecedores': fornecedores_qs.count(),
            'produtos': produtos_qs.count(),
        }
        self.stdout.write(self.style.WARNING(f"Resumo da limpeza: {summary}"))

        if not options['execute']:
            self.stdout.write(self.style.WARNING('Modo simulação. Use --execute para confirmar remoção.'))
            return

        with transaction.atomic():
            venda_ids = list(Venda.objects.filter(cliente__in=clientes_qs).values_list('id', flat=True))
            compra_ids = list(Compra.objects.filter(fornecedor__in=fornecedores_qs).values_list('id', flat=True))
            ItemVenda.objects.filter(venda_id__in=venda_ids).delete()
            ItemCompra.objects.filter(compra_id__in=compra_ids).delete()
            ContaReceber.objects.filter(venda_id__in=venda_ids).delete()
            ContaPagar.objects.filter(compra_id__in=compra_ids).delete()
            Venda.objects.filter(id__in=venda_ids).delete()
            Compra.objects.filter(id__in=compra_ids).delete()
            MovimentacaoEstoque.objects.filter(produto__in=produtos_qs).delete()
            produtos_qs.delete()
            clientes_qs.delete()
            fornecedores_qs.delete()
            users_qs.delete()
            AccessLog.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Limpeza de dados de teste executada com sucesso.'))

