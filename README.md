# Sistema de Gestão Comercial - Loja de Materiais de Construção

Este projeto é uma aplicação web de gestão comercial desenvolvida para centralizar e automatizar rotinas críticas de operação, como controle de estoque, registro de compras e vendas, acompanhamento financeiro e análise de indicadores em dashboard. Construído com Django e Django REST Framework, o sistema foi estruturado com foco em segurança, integridade dos dados, usabilidade e escalabilidade, contemplando autenticação JWT, validações de regras de negócio, relatórios gerenciais (PDF/Excel), suporte a fluxos online/offline e arquitetura preparada para ambientes de produção.

## Interface do Sistema

### Visão Geral do Frontend

<img src="static/img/image%20(6).png" alt="Tela 1 - Frontend" width="100%" />

<img src="static/img/image%20(7).png" alt="Tela 2 - Frontend" width="100%" />

<img src="static/img/image%20(8).png" alt="Tela 3 - Frontend" width="100%" />

## Funcionalidades

- **Autenticação JWT**: Login seguro com tokens.
- **Gestão de Produtos**: Cadastro completo com SKU e imagens.
- **Controle de Estoque**: Atualização automática via signals.
- **Gestão de Compras**: Registro de NFs e contas a pagar.
- **Gestão de Vendas**: Registro de saídas e contas a receber.
- **Dashboard**: KPIs em tempo real.
- **Relatórios**: Exportação para PDF e Excel.

## Instalação

1. Clone o repositório.
2. Crie um ambiente virtual: `python -m venv .venv`
3. Ative o ambiente virtual.
4. Instale as dependências: `pip install -r requirements.txt`
5. Configure as variáveis de ambiente (`DATABASE_URL`, `SECRET_KEY`, etc.).
6. Execute as migrações: `python manage.py migrate`
7. Crie um superusuário: `python manage.py createsuperuser`
8. Inicie o servidor: `python manage.py runserver`

## API Endpoints

- `/api/categorias/`: CRUD de categorias.
- `/api/produtos/`: CRUD de produtos.
- `/api/compras/compras/`: CRUD de compras.
- `/api/vendas/vendas/`: CRUD de vendas.
- `/api/dashboard/stats/`: KPIs do sistema.
- `/api/reports/inventory/excel/`: Exportar estoque para Excel.
- `/api/reports/sales/pdf/`: Exportar vendas para PDF.

## Testes

O sistema possui testes unitários e de integração integrados ao fluxo de desenvolvimento:

- **Testes Unitários**:`products/tests.py`, validam modelos e labels.
- **Testes de Integração**: Arquivos `integration_tests.py` e fornece cobertura para API e fluxos de negócio.

## Manual do Usuário - Venda a Prazo (Fiado)

1. Vá para a tela de **Vendas** e clique em **Nova Venda**.
2. Selecione o cliente e os produtos.
3. No campo **Status do Pagamento**, selecione **Pendente** ou **Não Pago**.
4. Um novo campo **Data de Vencimento** aparecerá. Informe a data acordada com o cliente.
5. Ao registrar a venda, o sistema gerará automaticamente uma **Conta a Receber** vinculada a este cliente.
6. Quando o cliente realizar o pagamento, vá ao módulo financeiro (ou via Admin) e altere o status da conta para **Pago**.
7. O sistema atualizará automaticamente o status da venda original para **Pago**.

- **VALIDATION**: Adicionada validação de estoque no backend para impedir vendas de produtos com quantidade insuficiente, prevenindo estoque negativo.
- **TEST**: Adicionados testes de integração para as novas funcionalidades, cobrindo a criação de produtos com estoque inicial, registro de compras e vendas, validação de estoque e o CRUD de clientes.

## Manual Rápido - Gestão Financeira

1. Acesse **Financeiro** no menu lateral ou clique em **Contas a Pagar/Receber** no Dashboard.
2. Selecione o módulo desejado (Pagar ou Receber) usando as abas no topo.
3. Aplique filtros de status, vencimento e valor para localizar contas específicas.
4. Clique em **Atualizar** na linha da conta para registrar pagamento ou marcar como não paga.
5. Para marcar como **Pago**, informe obrigatoriamente a data e o método.
6. Para manter como **Pendente/Não Pago**, informe justificativa.
7. Acompanhe alertas e o gráfico de fluxo de caixa previsto no final da página.
