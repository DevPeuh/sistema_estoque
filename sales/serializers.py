import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from .models import Cliente, Venda, ItemVenda, ContaReceber

logger = logging.getLogger(__name__)

class ClienteSerializer(serializers.ModelSerializer):
    def validate_nome(self, value):
        nome = (value or '').strip()
        if not nome:
            raise serializers.ValidationError('O nome do cliente é obrigatório.')
        return nome

    def validate_cpf_cnpj(self, value):
        if value in (None, ''):
            return None
        normalized = ''.join(ch for ch in str(value) if ch.isdigit())
        if len(normalized) not in (11, 14):
            raise serializers.ValidationError('CPF/CNPJ deve conter 11 ou 14 dígitos.')
        qs = Cliente.objects.filter(cpf_cnpj=normalized, ativo=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe cliente cadastrado com este CPF/CNPJ.')
        return normalized

    def validate(self, attrs):
        for field in ['telefone', 'email', 'endereco_entrega']:
            if attrs.get(field) == '':
                attrs[field] = None
        return attrs

    class Meta:
        model = Cliente
        fields = '__all__'

class ItemVendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade', 'preco_unitario']

class VendaSerializer(serializers.ModelSerializer):
    itens = ItemVendaSerializer(many=True)
    cliente_nome = serializers.ReadOnlyField(source='cliente.nome')

    class Meta:
        model = Venda
        fields = ['id', 'cliente', 'cliente_nome', 'data_venda', 'valor_total', 'status_pagamento', 'data_vencimento', 'itens']
        read_only_fields = ['valor_total']

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        if not validated_data['cliente'].ativo:
            raise serializers.ValidationError('Selecione um cliente ativo.')
        if not itens_data:
            raise serializers.ValidationError('Adicione ao menos um item para registrar a venda.')
        if validated_data.get('status_pagamento') != 'pago' and not validated_data.get('data_vencimento'):
            raise serializers.ValidationError('Informe a data de vencimento para vendas pendentes ou não pagas.')

        for item_data in itens_data:
            produto = item_data['produto']
            if not produto.ativo:
                raise serializers.ValidationError(f"O produto '{produto.descricao}' está inativo.")
            quantidade_vendida = item_data['quantidade']
            preco_unitario = item_data['preco_unitario']
            if quantidade_vendida <= 0:
                raise serializers.ValidationError(f"Quantidade inválida para o produto '{produto.descricao}'.")
            if preco_unitario <= 0:
                raise serializers.ValidationError(f"Preço unitário inválido para o produto '{produto.descricao}'.")
            if produto.estoque_atual < quantidade_vendida:
                raise serializers.ValidationError(
                    f"Estoque insuficiente para o produto '{produto.descricao}'. "
                    f"Disponível: {produto.estoque_atual}, Solicitado: {quantidade_vendida}."
                )
        try:
            with transaction.atomic():
                numero_nf = validated_data.get('numero_nota_fiscal')
                if not numero_nf:
                    validated_data['numero_nota_fiscal'] = f"NFV-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
                venda = Venda.objects.create(**validated_data)
                valor_total_venda = 0
                for item_data in itens_data:
                    item = ItemVenda.objects.create(venda=venda, **item_data)
                    valor_total_venda += item.subtotal
                if valor_total_venda <= 0:
                    raise serializers.ValidationError('Valor total da venda inválido.')
                venda.valor_total = valor_total_venda
                venda.save()
                return venda
        except Exception as exc:
            logger.exception('Falha ao registrar venda: %s', exc)
            raise

class ContaReceberSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.ReadOnlyField(source='cliente.nome')

    def validate(self, attrs):
        status = attrs.get('status', getattr(self.instance, 'status', None))
        data_recebimento = attrs.get('data_recebimento', getattr(self.instance, 'data_recebimento', None))
        metodo_pagamento = attrs.get('metodo_pagamento', getattr(self.instance, 'metodo_pagamento', None))
        justificativa_status = attrs.get('justificativa_status', getattr(self.instance, 'justificativa_status', None))
        if status == 'pago':
            if not data_recebimento:
                raise serializers.ValidationError('Informe a data de recebimento para marcar como pago.')
            if not metodo_pagamento:
                raise serializers.ValidationError('Informe o método de recebimento para marcar como pago.')
        if status in ['pendente', 'atrasado'] and not justificativa_status:
            raise serializers.ValidationError('Informe uma justificativa ao marcar conta como não paga.')
        return attrs

    def update(self, instance, validated_data):
        with transaction.atomic():
            locked = ContaReceber.objects.select_for_update().get(pk=instance.pk)
            previous_status = locked.status
            updated = super().update(locked, validated_data)
            if previous_status != updated.status or validated_data.get('data_recebimento') or validated_data.get('metodo_pagamento'):
                historico = list(updated.historico_pagamentos or [])
                historico.append({
                    'status': updated.status,
                    'data_recebimento': str(updated.data_recebimento) if updated.data_recebimento else None,
                    'metodo_pagamento': updated.metodo_pagamento,
                    'observacoes': updated.observacoes
                })
                updated.historico_pagamentos = historico
                updated.save(update_fields=['historico_pagamentos'])
            return updated

    class Meta:
        model = ContaReceber
        fields = [
            'id', 'venda', 'cliente', 'cliente_nome', 'valor', 'data_vencimento', 'status',
            'data_recebimento', 'metodo_pagamento', 'observacoes', 'justificativa_status',
            'historico_pagamentos'
        ]
