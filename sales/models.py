from django.db import models
from products.models import Produto

class Cliente(models.Model):
    cpf_cnpj = models.CharField(max_length=18, unique=True, verbose_name="CPF/CNPJ", blank=True, null=True)
    nome = models.CharField(max_length=255, verbose_name="Nome Completo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone", blank=True, null=True)
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    endereco_entrega = models.TextField(verbose_name="Endereço de Entrega", blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.nome

class Venda(models.Model):
    STATUS_PAGAMENTO_CHOICES = (
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado'),
    )

    numero_nota_fiscal = models.CharField(max_length=50, unique=True, blank=True, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='vendas')
    data_venda = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status_pagamento = models.CharField(max_length=10, choices=STATUS_PAGAMENTO_CHOICES, default='pendente')
    data_vencimento = models.DateField(blank=True, null=True, verbose_name="Data de Vencimento")

    def __str__(self):
        return f"Venda {self.id} - {self.cliente}"

class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('products.Produto', on_delete=models.PROTECT, null=True, blank=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantidade}x {self.produto} em {self.venda}"

class ContaReceber(models.Model):
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('atrasado', 'Atrasado'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado'),
    )

    venda = models.OneToOneField(Venda, on_delete=models.CASCADE, related_name='conta_receber')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    data_recebimento = models.DateField(blank=True, null=True)
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    justificativa_status = models.TextField(blank=True, null=True)
    historico_pagamentos = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Conta a Receber - {self.cliente} - R$ {self.valor}"
