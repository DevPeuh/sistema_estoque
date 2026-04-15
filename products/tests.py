from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Categoria, UnidadeDeMedida, Produto

class ProdutoAdminLabelTest(TestCase):
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
        
    def test_produto_labels(self):
        """Verifica se os labels amigáveis estão sendo aplicados no modelo"""
        produto = Produto(sku="Telha")
        self.assertEqual(produto._meta.get_field('sku').verbose_name, "Nome do Produto")
        self.assertEqual(produto._meta.get_field('preco_venda').verbose_name, "Preço de Venda")

    def test_cliente_labels(self):
        """Verifica se os labels amigáveis estão no modelo Cliente"""
        from sales.models import Cliente
        cliente = Cliente(nome="Peu")
        self.assertEqual(cliente._meta.get_field('cpf_cnpj').verbose_name, "CPF/CNPJ")
        self.assertEqual(cliente._meta.get_field('nome').verbose_name, "Nome Completo")
