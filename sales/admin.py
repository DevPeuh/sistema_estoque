from django.contrib import admin
from .models import Cliente, Venda, ItemVenda, ContaReceber

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf_cnpj', 'telefone', 'email')
    list_filter = ('email',)
    search_fields = ('nome', 'cpf_cnpj', 'email', 'telefone')
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('cpf_cnpj', 'nome', 'telefone', 'email')
        }),
        ('Endereço', {
            'fields': ('endereco_entrega',)
        }),
    )

class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1
    fields = ('produto', 'quantidade', 'preco_unitario', 'subtotal')
    readonly_fields = ('subtotal',)

@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'data_venda', 'valor_total', 'status_pagamento')
    list_filter = ('status_pagamento', 'data_venda')
    search_fields = ('cliente__nome', 'numero_nota_fiscal', 'cliente__cpf_cnpj')
    inlines = [ItemVendaInline]
    readonly_fields = ('data_venda',)
    fieldsets = (
        ('Cliente e Data', {
            'fields': ('cliente', 'data_venda', 'numero_nota_fiscal')
        }),
        ('Valores e Status', {
            'fields': ('valor_total', 'status_pagamento')
        }),
    )

@admin.register(ItemVenda)
class ItemVendaAdmin(admin.ModelAdmin):
    list_display = ('venda', 'produto', 'quantidade', 'preco_unitario', 'subtotal')
    list_filter = ('venda__data_venda',)
    search_fields = ('venda__cliente__nome', 'produto__descricao')
    readonly_fields = ('subtotal',)

@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('venda', 'valor', 'data_vencimento', 'status')
    list_filter = ('status', 'data_vencimento')
    search_fields = ('venda__cliente__nome', 'venda__numero_nota_fiscal')
