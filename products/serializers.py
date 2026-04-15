from rest_framework import serializers
from .models import Produto, Categoria, UnidadeDeMedida, MovimentacaoEstoque

class CategoriaSerializer(serializers.ModelSerializer):
    def validate_nome(self, value):
        nome = (value or '').strip()
        if not nome:
            raise serializers.ValidationError('O nome da categoria é obrigatório.')
        qs = Categoria.objects.filter(nome__iexact=nome, ativo=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe uma categoria ativa com este nome.')
        return nome

    class Meta:
        model = Categoria
        fields = '__all__'

class UnidadeDeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeDeMedida
        fields = '__all__'

class ProdutoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.ReadOnlyField(source='categoria.nome')
    unidade_sigla = serializers.ReadOnlyField(source='unidade_medida.sigla')
    sku = serializers.CharField(validators=[])
    codigo_barras = serializers.CharField(required=False, allow_blank=True, allow_null=True, validators=[])

    class Meta:
        model = Produto
        fields = ['id', 'sku', 'descricao', 'categoria', 'categoria_nome', 'unidade_sigla', 'preco_custo', 'preco_venda', 'estoque_atual', 'estoque_minimo', 'codigo_barras']
        extra_kwargs = {
            'sku': {'label': 'Nome do Produto'},
        }

    def validate_categoria(self, value):
        if value and not value.ativo:
            raise serializers.ValidationError('Selecione uma categoria ativa.')
        return value

    def validate_sku(self, value):
        nome = (value or '').strip()
        if not nome:
            raise serializers.ValidationError('Informe o nome do produto.')
        qs = Produto.objects.filter(sku__iexact=nome, ativo=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Produto com este Nome do Produto já existe.')
        return nome

    def validate_codigo_barras(self, value):
        if value is None:
            return None
        codigo = str(value).strip()
        if not codigo:
            return None
        qs = Produto.objects.filter(codigo_barras=codigo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe um produto com este código de barras.')
        return codigo

class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimentacaoEstoque
        fields = '__all__'
