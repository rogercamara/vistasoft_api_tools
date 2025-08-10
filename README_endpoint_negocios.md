
## 🎯 Objetivo
Endpoint `GET /api/negocios/[etapa]/[status]/[periodo]` para retornar métricas de negócios da API Vistahost.

## 🛠 Tecnologias
- Next.js (App Router)
- TypeScript

## ⚙️ Variáveis de Ambiente (.env)
```env
VISTAHOST_BASE_URL=https://seudominio.vistahost.com.br
VISTAHOST_KEY=sua_chave_api_vistahost
```

## ▶️ Execução
- Coloque o arquivo `route.ts` em `app/api/negocios/[etapa]/[status]/[periodo]/route.ts`.
- Rode o projeto Next.js normalmente.

## 📌 Observações
- Períodos aceitos: `semana` (últimos 7 dias) ou `mes` (últimos ~30 dias).
- Datas formatadas com timezone `America/Sao_Paulo`.
- Respostas no formato JSON com totais e valores agregados.
