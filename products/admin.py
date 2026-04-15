from django.contrib import admin
from .models import Categoria, UnidadeDeMedida, Produto, MovimentacaoEstoque

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(UnidadeDeMedida)
class UnidadeDeMedidaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla')
    search_fields = ('nome', 'sigla')

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('sku', 'descricao', 'categoria', 'unidade_medida', 'preco_venda', 'estoque_atual', 'estoque_minimo')
    list_filter = ('categoria', 'criado_em')
    search_fields = ('sku', 'descricao', 'codigo_barras')
    readonly_fields = ('estoque_atual', 'criado_em', 'atualizado_em')
    autocomplete_fields = ('categoria', 'unidade_medida')
    list_editable = ('preco_venda', 'estoque_minimo')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('sku', 'descricao', 'categoria', 'unidade_medida', 'codigo_barras', 'imagem')
        }),
        ('Preços', {
            'fields': ('preco_custo', 'preco_venda')
        }),
        ('Estoque', {
            'fields': ('estoque_atual', 'estoque_minimo', 'estoque_maximo')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('get_produto', 'tipo_movimento', 'quantidade', 'data_movimento')
    list_filter = ('tipo_movimento', 'data_movimento')
    search_fields = ('produto__descricao', 'produto__sku')
    readonly_fields = ('data_movimento',)
    
    def get_produto(self, obj):
        return obj.produto.descricao
    get_produto.short_description = 'Produto'
