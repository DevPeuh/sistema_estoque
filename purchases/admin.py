from django.contrib import admin
from .models import Fornecedor, Compra, ItemCompra, ContaPagar

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'nome_fantasia', 'cnpj', 'telefone', 'email')
    list_filter = ('cnpj',)
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj', 'email')
    fieldsets = (
        ('Informações Legais', {
            'fields': ('cnpj', 'razao_social', 'nome_fantasia')
        }),
        ('Contato', {
            'fields': ('contato_nome', 'telefone', 'email')
        }),
        ('Endereço e Pagamento', {
            'fields': ('endereco', 'prazo_pagamento_padrao')
        }),
    )

class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    fields = ('produto', 'quantidade', 'preco_unitario', 'subtotal')
    readonly_fields = ('subtotal',)

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('numero_nota_fiscal', 'fornecedor', 'data_emissao', 'valor_total', 'status_pagamento')
    list_filter = ('status_pagamento', 'data_emissao', 'data_vencimento')
    search_fields = ('numero_nota_fiscal', 'fornecedor__razao_social')
    inlines = [ItemCompraInline]
    readonly_fields = ('data_recebimento',)
    fieldsets = (
        ('Nota Fiscal', {
            'fields': ('numero_nota_fiscal', 'fornecedor')
        }),
        ('Datas', {
            'fields': ('data_emissao', 'data_vencimento', 'data_recebimento')
        }),
        ('Valores e Status', {
            'fields': ('valor_total', 'status_pagamento')
        }),
    )

@admin.register(ItemCompra)
class ItemCompraAdmin(admin.ModelAdmin):
    list_display = ('compra', 'produto', 'quantidade', 'preco_unitario', 'subtotal')
    list_filter = ('compra__data_emissao',)
    search_fields = ('compra__numero_nota_fiscal', 'produto__descricao')
    readonly_fields = ('subtotal',)

@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ('compra', 'valor', 'data_vencimento', 'status')
    list_filter = ('status', 'data_vencimento')
    search_fields = ('compra__numero_nota_fiscal', 'compra__fornecedor__razao_social')
