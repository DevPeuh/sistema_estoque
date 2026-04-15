from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from products.models import Categoria, UnidadeDeMedida, Produto
from sales.models import Cliente, Venda, ItemVenda
from purchases.models import Fornecedor, Compra, ItemCompra
from django.utils import timezone
from decimal import Decimal
from io import BytesIO
import openpyxl

class IntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='admin',
            password='adminpassword',
            email='admin@test.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.categoria = Categoria.objects.create(nome="Geral")
        self.unidade = UnidadeDeMedida.objects.create(nome="Unidade", sigla="UN")
        self.produto = Produto.objects.create(
            sku="PROD01",
            descricao="Produto Teste",
            categoria=self.categoria,
            preco_custo=Decimal('10.00'),
            preco_venda=Decimal('20.00'),
            estoque_atual=Decimal('100.00')
        )
        self.cliente = Cliente.objects.create(
            nome="Cliente Teste",
            cpf_cnpj="12345678901",
            email="cliente@test.com",
            telefone="12345678"
        )
        self.fornecedor = Fornecedor.objects.create(
            razao_social="Fornecedor Teste",
            cnpj="12345678000199",
            email="forn@test.com",
            telefone="12345678"
        )

    def test_products_api_returns_list(self):
        response = self.client.get('/api/produtos/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))

    def test_sales_api_returns_list(self):
        response = self.client.get('/api/vendas/vendas/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))

    def test_purchases_api_returns_list(self):
        response = self.client.get('/api/compras/compras/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))

    def test_reports_endpoints(self):
        endpoints = [
            '/api/reports/inventory/excel/',
            '/api/reports/inventory/pdf/',
            '/api/reports/sales/pdf/',
            '/api/reports/sales/excel/',
            '/api/reports/financial/pdf/',
            '/api/reports/financial/excel/',
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed at {url}")

    def test_sales_report_excel_includes_only_paid_sales(self):
        sale_pendente = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [{"produto": self.produto.id, "quantidade": 5, "preco_unitario": 20.00}]
        }
        sale_pago = {
            "cliente": self.cliente.id,
            "status_pagamento": "pago",
            "itens": [{"produto": self.produto.id, "quantidade": 3, "preco_unitario": 20.00}]
        }
        r1 = self.client.post('/api/vendas/vendas/', sale_pendente, format='json')
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post('/api/vendas/vendas/', sale_pago, format='json')
        self.assertEqual(r2.status_code, 201)

        response = self.client.get('/api/reports/sales/excel/')
        self.assertEqual(response.status_code, 200)
        workbook = openpyxl.load_workbook(BytesIO(response.content))
        sheet = workbook.active
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0][0]), r2.data['id'])

    def test_sale_creates_inventory_movement(self):
        from products.models import MovimentacaoEstoque
        venda = Venda.objects.create(cliente=self.cliente, valor_total=Decimal('20.00'))
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=Decimal('2.00'),
            preco_unitario=Decimal('10.00')
        )
        # Verify signal created movement
        movements = MovimentacaoEstoque.objects.filter(produto=self.produto, tipo_movimento='saida')
        self.assertTrue(movements.exists())

    def test_create_product_with_initial_stock(self):
        data = {
            "sku": "PROD02", "descricao": "Produto com Estoque Inicial",
            "categoria": self.categoria.id,
            "preco_custo": "15.00", "preco_venda": "25.00",
            "estoque_atual": "50.00"
        }
        response = self.client.post('/api/produtos/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estoque_atual'], '50.00')

    def test_create_multiple_products_without_barcode(self):
        base_payload = {
            "categoria": self.categoria.id,
            "preco_custo": "10.00",
            "preco_venda": "15.00",
            "estoque_atual": "5.00",
            "estoque_minimo": "1.00",
            "codigo_barras": ""
        }
        p1 = {**base_payload, "sku": "PROD_NO_BAR_1", "descricao": "Sem Código 1"}
        p2 = {**base_payload, "sku": "PROD_NO_BAR_2", "descricao": "Sem Código 2"}
        r1 = self.client.post('/api/produtos/', p1, format='json')
        r2 = self.client.post('/api/produtos/', p2, format='json')
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertIn(r1.data['codigo_barras'], [None, ""])
        self.assertIn(r2.data['codigo_barras'], [None, ""])

    def test_create_purchase_updates_stock(self):
        initial_stock = self.produto.estoque_atual
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF001",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 10, "preco_unitario": 10.00}
            ]
        }
        response = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, initial_stock + 10)
        self.assertEqual(Decimal(response.data['valor_total']), Decimal('100.00'))

    def test_create_purchase_without_invoice_number(self):
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 2, "preco_unitario": 10.00}
            ]
        }
        response = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn(response.data.get('numero_nota_fiscal'), [None, ""])

    def test_create_sale_updates_stock(self):
        initial_stock = self.produto.estoque_atual
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pago",
            "itens": [
                {"produto": self.produto.id, "quantidade": 5, "preco_unitario": 20.00}
            ]
        }
        response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, initial_stock - 5)

    def test_sale_on_credit_creates_account_receivable(self):
        from sales.models import ContaReceber
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(response.status_code, 201)
        
        # Verify account receivable was created with the correct due date
        conta = ContaReceber.objects.get(venda_id=response.data['id'])
        self.assertEqual(str(conta.data_vencimento), "2026-04-18")
        self.assertEqual(conta.status, 'pendente')

    def test_paying_account_updates_sale_status(self):
        from sales.models import ContaReceber
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        venda_id = response.data['id']
        
        conta = ContaReceber.objects.get(venda_id=venda_id)
        conta.status = 'pago'
        conta.save()
        
        from sales.models import Venda
        venda = Venda.objects.get(id=venda_id)
        self.assertEqual(venda.status_pagamento, 'pago')

    def test_cannot_delete_product_with_sales(self):
        # Create a sale for the product
        venda = Venda.objects.create(cliente=self.cliente, valor_total=Decimal('20.00'))
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=Decimal('1.00'),
            preco_unitario=Decimal('20.00')
        )
        
        # Try to delete the product - should fail due to PROTECT
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.produto.delete()
        
        response = self.client.delete(f'/api/produtos/{self.produto.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("desativado", response.data['detail'].lower())
        self.produto.refresh_from_db()
        self.assertFalse(self.produto.ativo)

    def test_recreate_soft_deleted_product_reactivates_existing(self):
        self.produto.ativo = False
        self.produto.save(update_fields=['ativo'])
        payload = {
            "sku": self.produto.sku,
            "descricao": "Produto Reativado",
            "categoria": self.categoria.id,
            "preco_custo": "30.00",
            "preco_venda": "40.00",
            "estoque_atual": "98.00",
            "estoque_minimo": "20.00",
            "codigo_barras": ""
        }
        response = self.client.post('/api/produtos/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertTrue(self.produto.ativo)
        self.assertEqual(self.produto.descricao, "Produto Reativado")
        self.assertEqual(str(self.produto.estoque_atual), "98.00")
        self.assertEqual(Produto.objects.filter(sku=self.produto.sku).count(), 1)

    def test_edit_product_preserves_stock(self):
        initial_stock = self.produto.estoque_atual
        data = {
            "descricao": "Produto Editado",
            "sku": self.produto.sku,
            "categoria": self.categoria.id,
            "preco_custo": "12.00",
            "preco_venda": "22.00"
        }
        # Note: we are NOT sending estoque_atual
        response = self.client.put(f'/api/produtos/{self.produto.id}/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, initial_stock)
        self.assertEqual(self.produto.descricao, "Produto Editado")

    def test_create_client_with_only_name(self):
        data = {"nome": "Cliente Apenas Nome"}
        response = self.client.post('/api/vendas/clientes/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['nome'], "Cliente Apenas Nome")
        self.assertIsNone(response.data['cpf_cnpj'])

    def test_sale_with_insufficient_stock_fails(self):
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pago",
            "itens": [
                {"produto": self.produto.id, "quantidade": 200, "preco_unitario": 20.00}
            ]
        }
        response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_purchase_with_zero_price_fails(self):
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF002",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pago",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 0}
            ]
        }
        response = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_sale_pending_without_due_date_fails(self):
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_dashboard_includes_overdue_payables(self):
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF003",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "atrasado",
            "itens": [
                {"produto": self.produto.id, "quantidade": 2, "preco_unitario": 15.00}
            ]
        }
        response_purchase = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(response_purchase.status_code, 201)

        response_dashboard = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response_dashboard.status_code, 200)
        self.assertGreater(Decimal(str(response_dashboard.data['contas_pagar_pendentes'])), Decimal('0'))

    def test_dashboard_counts_only_paid_sales(self):
        from sales.models import ContaReceber

        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 5, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(Decimal(str(create_response.data['valor_total'])), Decimal('100.00'))

        dashboard_pending = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_pending.status_code, 200)
        self.assertEqual(Decimal(str(dashboard_pending.data['vendas_dia'])), Decimal('0'))
        self.assertEqual(Decimal(str(dashboard_pending.data['vendas_mes'])), Decimal('0'))

        conta = ContaReceber.objects.get(venda_id=create_response.data['id'])
        conta.status = 'atrasado'
        conta.justificativa_status = 'Cliente não pagou no prazo'
        conta.save()

        dashboard_overdue = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_overdue.status_code, 200)
        self.assertEqual(Decimal(str(dashboard_overdue.data['vendas_dia'])), Decimal('0'))
        self.assertEqual(Decimal(str(dashboard_overdue.data['vendas_mes'])), Decimal('0'))

        conta.status = 'pago'
        conta.data_recebimento = timezone.now().date()
        conta.metodo_pagamento = 'PIX'
        conta.save()

        dashboard_paid = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_paid.status_code, 200)
        self.assertEqual(Decimal(str(dashboard_paid.data['vendas_dia'])), Decimal('100.00'))
        self.assertEqual(Decimal(str(dashboard_paid.data['vendas_mes'])), Decimal('100.00'))

    def test_top_products_counts_only_paid_sales(self):
        from sales.models import ContaReceber

        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 10, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)

        dashboard_before = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_before.status_code, 200)
        produto_nome = self.produto.descricao
        top_before = [item for item in dashboard_before.data['top_produtos'] if item['produto__descricao'] == produto_nome]
        self.assertEqual(len(top_before), 0)

        conta = ContaReceber.objects.get(venda_id=create_response.data['id'])
        conta.status = 'atrasado'
        conta.justificativa_status = 'Sem pagamento'
        conta.save()

        dashboard_overdue = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_overdue.status_code, 200)
        top_overdue = [item for item in dashboard_overdue.data['top_produtos'] if item['produto__descricao'] == produto_nome]
        self.assertEqual(len(top_overdue), 0)

        conta.status = 'pago'
        conta.data_recebimento = timezone.now().date()
        conta.metodo_pagamento = 'Dinheiro'
        conta.save()

        dashboard_paid = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dashboard_paid.status_code, 200)
        top_paid = [item for item in dashboard_paid.data['top_produtos'] if item['produto__descricao'] == produto_nome]
        self.assertEqual(len(top_paid), 1)
        self.assertEqual(Decimal(str(top_paid[0]['total_vendido'])), Decimal('10'))

    def test_client_duplicate_cpf_returns_error(self):
        data = {"nome": "Cliente Duplicado", "cpf_cnpj": "123.456.789-01"}
        response = self.client.post('/api/vendas/clientes/', data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_client_crud_operations(self):
        # Create
        client_data = {"nome": "Novo Cliente", "cpf_cnpj": "11122233344", "email": "novo@cliente.com", "telefone": "987654321", "endereco_entrega": "Rua Nova"}
        response = self.client.post('/api/vendas/clientes/', client_data, format='json')
        self.assertEqual(response.status_code, 201)
        client_id = response.data['id']

        # Read
        response = self.client.get(f'/api/vendas/clientes/{client_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nome'], "Novo Cliente")

        # Update
        updated_data = {"nome": "Cliente Atualizado"}
        response = self.client.patch(f'/api/vendas/clientes/{client_id}/', updated_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nome'], "Cliente Atualizado")

        # Delete
        response = self.client.delete(f'/api/vendas/clientes/{client_id}/')
        self.assertEqual(response.status_code, 204)

    def test_accounts_payable_summary_endpoint(self):
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF900",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 3, "preco_unitario": 10.00}
            ]
        }
        create_response = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        summary_response = self.client.get('/api/compras/contas-pagar/summary/')
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreater(Decimal(str(summary_response.data['total_pendente'])), Decimal('0'))

    def test_accounts_receivable_summary_endpoint(self):
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        summary_response = self.client.get('/api/vendas/contas-receber/summary/')
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreater(Decimal(str(summary_response.data['total_pendente'])), Decimal('0'))

    def test_update_payable_paid_requires_method_and_date(self):
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF901",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 10.00}
            ]
        }
        create_response = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        contas = self.client.get('/api/compras/contas-pagar/').data
        conta_id = contas[0]['id']
        invalid_update = self.client.patch(f'/api/compras/contas-pagar/{conta_id}/', {"status": "pago"}, format='json')
        self.assertEqual(invalid_update.status_code, 400)

    def test_update_receivable_unpaid_requires_justification(self):
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        contas = self.client.get('/api/vendas/contas-receber/').data
        conta_id = contas[0]['id']
        invalid_update = self.client.patch(f'/api/vendas/contas-receber/{conta_id}/', {"status": "atrasado"}, format='json')
        self.assertEqual(invalid_update.status_code, 400)

    def test_receivable_total_excludes_non_paid(self):
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)

        summary_before = self.client.get('/api/vendas/contas-receber/summary/')
        self.assertEqual(summary_before.status_code, 200)
        self.assertEqual(Decimal(str(summary_before.data['total_pendente'])), Decimal('20.00'))

        contas = self.client.get('/api/vendas/contas-receber/').data
        conta_id = contas[0]['id']
        update_response = self.client.patch(
            f'/api/vendas/contas-receber/{conta_id}/',
            {"status": "atrasado", "justificativa_status": "Cliente não efetuou pagamento"},
            format='json'
        )
        self.assertEqual(update_response.status_code, 200)

        summary_after = self.client.get('/api/vendas/contas-receber/summary/')
        self.assertEqual(summary_after.status_code, 200)
        self.assertEqual(Decimal(str(summary_after.data['total_pendente'])), Decimal('0'))

    def test_quick_create_category_prevents_duplicate(self):
        create_response = self.client.post('/api/categorias/', {"nome": "Ferragens"}, format='json')
        self.assertIn(create_response.status_code, [200, 201])
        duplicate_response = self.client.post('/api/categorias/', {"nome": "ferragens"}, format='json')
        self.assertEqual(duplicate_response.status_code, 400)

    def test_quick_create_supplier_with_minimal_fields(self):
        supplier_data = {
            "razao_social": "Fornecedor Rápido",
            "cnpj": "12345678901",
            "telefone": "11999999999"
        }
        response = self.client.post('/api/compras/fornecedores/', supplier_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['razao_social'], "Fornecedor Rápido")
        self.assertEqual(response.data['cnpj'], "12345678901")
        self.assertIn(response.data['email'], [None, ""])

    def test_delete_supplier_with_purchase_performs_soft_delete_and_audit_log(self):
        from dashboard.models import DeletionAuditLog
        purchase_data = {
            "fornecedor": self.fornecedor.id,
            "numero_nota_fiscal": "NF990",
            "data_emissao": "2026-01-01",
            "data_vencimento": "2026-02-01",
            "status_pagamento": "pendente",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 10.00}
            ]
        }
        response_purchase = self.client.post('/api/compras/compras/', purchase_data, format='json')
        self.assertEqual(response_purchase.status_code, 201)
        delete_response = self.client.delete(f'/api/compras/fornecedores/{self.fornecedor.id}/')
        self.assertEqual(delete_response.status_code, 200)
        self.fornecedor.refresh_from_db()
        self.assertFalse(self.fornecedor.ativo)
        self.assertTrue(DeletionAuditLog.objects.filter(model_name='Fornecedor', object_id=str(self.fornecedor.id), action='soft_delete').exists())

    def test_delete_client_with_sale_performs_soft_delete_and_audit_log(self):
        from dashboard.models import DeletionAuditLog
        sale_data = {
            "cliente": self.cliente.id,
            "status_pagamento": "pendente",
            "data_vencimento": "2026-04-18",
            "itens": [
                {"produto": self.produto.id, "quantidade": 1, "preco_unitario": 20.00}
            ]
        }
        create_response = self.client.post('/api/vendas/vendas/', sale_data, format='json')
        self.assertEqual(create_response.status_code, 201)
        delete_response = self.client.delete(f'/api/vendas/clientes/{self.cliente.id}/')
        self.assertEqual(delete_response.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.ativo)
        self.assertTrue(DeletionAuditLog.objects.filter(model_name='Cliente', object_id=str(self.cliente.id), action='soft_delete').exists())

    def test_delete_requires_permission(self):
        user_sem_permissao = User.objects.create_user(username='operador', password='123456')
        self.client.force_authenticate(user=user_sem_permissao)
        response = self.client.delete(f'/api/produtos/{self.produto.id}/')
        self.assertEqual(response.status_code, 403)
