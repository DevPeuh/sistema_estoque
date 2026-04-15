from django.db import models
from products.models import Produto

class Fornecedor(models.Model):
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ")
    razao_social = models.CharField(max_length=255, verbose_name="Razão Social")
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome Fantasia")
    contato_nome = models.CharField(max_length=100, verbose_name="Nome do Contato")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    endereco = models.TextField(verbose_name="Endereço")
    prazo_pagamento_padrao = models.IntegerField(help_text="Prazo em dias", default=30, verbose_name="Prazo de Pagamento Padrão")
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"

    def __str__(self):
        return self.razao_social

class Compra(models.Model):
    STATUS_PAGAMENTO_CHOICES = (
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado'),
    )

    numero_nota_fiscal = models.CharField(max_length=50, unique=True, blank=True, null=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='compras')
    data_emissao = models.DateField()
    data_recebimento = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status_pagamento = models.CharField(max_length=10, choices=STATUS_PAGAMENTO_CHOICES, default='pendente')
    data_vencimento = models.DateField()

    def __str__(self):
        return f"NF {self.numero_nota_fiscal} - {self.fornecedor}"

class ItemCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('products.Produto', on_delete=models.PROTECT, null=True, blank=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantidade}x {self.produto} em {self.compra}"

class ContaPagar(models.Model):
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('atrasado', 'Atrasado'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado'),
    )
    
    compra = models.OneToOneField(Compra, on_delete=models.CASCADE, related_name='conta_pagar')
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    data_pagamento = models.DateField(blank=True, null=True)
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    justificativa_status = models.TextField(blank=True, null=True)
    historico_pagamentos = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Conta a Pagar - {self.fornecedor} - R$ {self.valor}"
