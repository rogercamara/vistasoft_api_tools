# README — Esquema OpenAPI para Busca de Imóveis

## 🎯 Objetivo
Definir uma *action* para Assistentes GPT consultarem imóveis na API Vistahost (ou compatível).

## 📄 Arquivo
`esquema_imobiliaria_placeholder.json`

## 📌 Uso no GPT
Permite que o assistente construa chamadas HTTP à API para buscar imóveis com filtros como cidade, bairro, valor, número de dormitórios etc.

**Exemplo de instrução para o GPT:**
> "Buscar apartamentos no bairro Centro, na cidade de Curitiba, com 2 dormitórios e valor de venda até R$ 500.000, retornando código, bairro, valor de venda, área privativa e nome do corretor."

## 🛠 Estrutura
- Método: GET `/imoveis/listar`
- Parâmetros:
  - `key`: chave de API
  - `showtotal`: opcional
  - `pesquisa`: JSON serializado com filtros e paginação
  - Header `Accept: application/json`
