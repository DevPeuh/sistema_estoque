from django.db import models

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class UnidadeDeMedida(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    sigla = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return f"{self.nome} ({self.sigla})"

class Produto(models.Model):
    sku = models.CharField(max_length=50, unique=True, verbose_name="Nome do Produto", help_text="Stock Keeping Unit")
    descricao = models.TextField(verbose_name="Descrição")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos', verbose_name="Categoria")
    unidade_medida = models.ForeignKey(UnidadeDeMedida, on_delete=models.SET_NULL, related_name='produtos', verbose_name="Unidade de Medida", null=True, blank=True)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Custo")
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    estoque_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Estoque Atual")
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Estoque Mínimo")
    estoque_maximo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Estoque Máximo")
    codigo_barras = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Código de Barras")
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name="Imagem")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.descricao

class MovimentacaoEstoque(models.Model):
    TIPO_MOVIMENTO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('ajuste', 'Ajuste'),
    )

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo_movimento = models.CharField(max_length=10, choices=TIPO_MOVIMENTO_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    data_movimento = models.DateTimeField(auto_now_add=True)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.get_tipo_movimento_display()} de {self.quantidade} em {self.produto}'
