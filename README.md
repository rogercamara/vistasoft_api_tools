## VistaSoft - Integrações e usos extras
---

## 📦 Conteúdo

- **Python**
  - `ImportadorVista.py` — Importa **imóveis** da API do Vista e faz *upsert* no banco (PostgreSQL/Supabase ou similar), usando `codigo` como chave de negócio.
    
  - `ImportadorProntuarios.py` — Consulta **prontuários de cada imóvel** e grava em uma tabela de exemplo chamada `imovel_prontuario` (upsert em lote; datas/booleanos normalizados).
 
  - `importa_imoveis_mysql.py` — Variante para **MySQL** (execução direta, *executemany* + `ON DUPLICATE KEY UPDATE`).
    
  - `chatgpt.json` - Schema para o uso da API vista com um assistente GPT na plataforma do CHAT GPT

- **Next.js (App Router)**
  - `app/api/negocios/[etapa]/[status]/[periodo]/route.ts` — Exemplo de endpoint tratado para métricas de **negócios** por etapa/status, com períodos `semana` ou `mes`.

- **SQL (schemas)**
  - `schema_imoveis_local.sql` — Esquema MySQL sugerido para `imoveis`.
  - Esquemas Postgres/Supabase (no README dos scripts) para `imoveis` e `imovel_prontuario`.

---

## ⚙️ Variáveis de Ambiente (.env)

Exemplo consolidado (Python + Next.js): 

```env
# Supabase / Postgres (quando aplicável)
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_KEY=sua_chave_api_supabase

# Vistahost (Vista CRM)
API_IMOVEIS_KEY=sua_chave_api_vista
API_BASE_URL=https://seudominio.vistahost.com.br
API_LISTAR_PATH=/imoveis/listar
API_TIMEOUT=25
API_SLEEP_BETWEEN=0.2
PAGE_SIZE=50

# MySQL (quando usar importa_imoveis_mysql.py)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=colnaghi
DB_TABLE_IMOVEIS=imoveis_local

# Endpoint Next.js
VISTAHOST_BASE_URL=https://seudominio.vistahost.com.br
VISTAHOST_KEY=sua_chave_api_vistahost
```
---

## 🐍 Scripts Python

### 1) `ImportadorVista.py`
Importa **imóveis** da API de listagem (paginada), normaliza campos (datas/flags) e faz *upsert* na tabela `imoveis` (Postgres/Supabase).

```bash
pip install requests python-dotenv supabase tqdm
python ImportadorVista.py
```

### 2) `ImportadorProntuarios.py`
Para cada `codigo` da tabela `imoveis`, consulta a API de **detalhes** e grava o campo `prontuarios` em `imovel_prontuario` (upsert em lote). Respeita rate limit com *retries* e `sleep` configurável.

```bash
pip install requests python-dotenv supabase tqdm
python ImportadorProntuarios.py
```

**Schema (Postgres/Supabase) — resumo:**
- `imoveis(codigo TEXT UNIQUE, ... indices por bairro/status/datas)`
- `imovel_prontuario(codigo_imovel TEXT, codigo_prontuario BIGINT, UNIQUE(codigo_imovel, codigo_prontuario))`

> Esquemas completos com `updated_at` por trigger estão nos READMEs dos scripts.

### 3) `importa_imoveis_mysql.py`
Mesmo propósito do primeiro, mas com **MySQL** (`executemany` + upsert via `ON DUPLICATE KEY UPDATE`). Datas saneadas (`YYYY-MM-DD`), flags `TINYINT(1)`.

```bash
pip install requests python-dotenv mysql-connector-python
python importa_imoveis_mysql.py
```

**Schema (MySQL) recomendado:** ver [`schema_imoveis_local.sql`](./schema_imoveis_local.sql).

---

## ⚡ Endpoint Next.js (TypeScript)

**Rota:** `GET /api/negocios/[etapa]/[status]/[periodo]`  
**Períodos:** `semana` | `mes`  
**TZ:** America/Sao_Paulo (datas normalizadas para evitar erros de fuso).  
**Env:** `VISTAHOST_BASE_URL`, `VISTAHOST_KEY`

**O que faz:**
- `semana` → soma os últimos **7 dias** (inclui hoje) e retorna também o **total por dia** (`YYYY-MM-DD`).
- `mes` → soma dos **últimos ~30 dias** e retorna `{ total, valorTotal }` conforme a API.

**Exemplos:**
```bash
# Últimos 7 dias — etapa=Captação, status=Em aberto
curl -s https://seu-dominio.com/api/negocios/captacao/aberto/semana

# Último mês — etapa=Proposta, status=Ganho
curl -s https://seu-dominio.com/api/negocios/proposta/ganho/mes
```

**Notas técnicas:**
- Datas formatadas em `YYYY-MM-DD` fixando `America/Sao_Paulo` via `Intl.DateTimeFormat`.
- Normalização de parâmetros: `"aberto"` → `"Em aberto"`; etapa com capitalização inicial.
- Consulta segura (try/catch) e respostas coesas em JSON.

---

## 🧪 Checklist rápido

- [.env] preenchido com chaves/URLs corretas
- Tabelas criadas (Postgres/MySQL) conforme schemas
- Dependências instaladas (`pip install ...` / projeto Next.js)
- Endpoint acessível em `/api/negocios/...` com a base Vistahost configurada

---


## Extra: Integracao DIRETA com o CHATGPT (GPT`s Personalizados)

## 📄 Esquema OpenAPI — Buscar Imóveis

Arquivo: `vista_schema.json`

**Objetivo:**  
Permitir que um Assistente GPT consulte imóveis diretamente da API da imobiliária, usando filtros como cidade, bairro, faixa de valor, etc.  
O esquema define parâmetros esperados (`key`, `showtotal`, `pesquisa`) e retorna dados detalhados, incluindo foto destaque e informações do corretor. Tudo isso em uma conversa natural dentro de um GPT configurado especialmente para este cenário. 
- O esquema é adicionado ao configurar um GPT, na opção `Ações`
- Voce deve adicionar o endpoint direto na URL solicitada durante a configuracao
- Depois, adicionar o conteudo do schema no painel de configuração da ação

**Exemplo de uso no GPT (instrução):**
> "Buscar apartamentos disponíveis no bairro Centro, na cidade de Curitiba, com 2 dormitórios e valor de venda até R$ 500.000, retornando código, bairro, valor de venda, área privativa e nome do corretor."

O Assistente usará o *action* `buscarImoveis` e preencherá os parâmetros de `pesquisa` com esses filtros.

