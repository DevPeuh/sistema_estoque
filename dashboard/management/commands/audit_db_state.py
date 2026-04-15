from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from products.models import Categoria, Produto, UnidadeDeMedida, MovimentacaoEstoque
from purchases.models import Fornecedor, Compra, ItemCompra, ContaPagar
from sales.models import Cliente, Venda, ItemVenda, ContaReceber


class Command(BaseCommand):
    help = "Audita o estado do banco atual e informa se está limpo para produção."

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict-empty',
            action='store_true',
            help='Falha com erro se houver qualquer dado nas tabelas auditadas.'
        )

    def handle(self, *args, **options):
        tables = {
            'clientes': Cliente.objects.count(),
            'fornecedores': Fornecedor.objects.count(),
            'produtos': Produto.objects.count(),
            'categorias': Categoria.objects.count(),
            'unidades_medida': UnidadeDeMedida.objects.count(),
            'vendas': Venda.objects.count(),
            'itens_venda': ItemVenda.objects.count(),
            'compras': Compra.objects.count(),
            'itens_compra': ItemCompra.objects.count(),
            'contas_receber': ContaReceber.objects.count(),
            'contas_pagar': ContaPagar.objects.count(),
            'movimentacoes_estoque': MovimentacaoEstoque.objects.count(),
        }
        total = sum(tables.values())
        self.stdout.write(self.style.MIGRATE_HEADING('=== Auditoria de Banco ==='))
        self.stdout.write(f"Vendor: {connection.vendor}")
        self.stdout.write(f"Database: {connection.settings_dict.get('NAME')}")
        for key, value in tables.items():
            self.stdout.write(f"- {key}: {value}")
        self.stdout.write(f"TOTAL REGISTROS AUDITADOS: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Banco limpo: sem registros nas tabelas auditadas.'))
        else:
            self.stdout.write(self.style.WARNING('Banco contém dados persistidos.'))

        if options['strict_empty'] and total > 0:
            raise CommandError('Banco não está limpo para go-live.')

