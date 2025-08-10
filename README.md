# vistasoft_api_tools

Ferramentas que auxiliam na extração de dados da API REST do CRM Vista para imobiliárias.

## ImportadorVista.py

Script python responsável por consumir os dados da API do Vista CRM, processar e normalizar campos, e realizar *upsert* no banco de dados (Supabase/PostgreSQL) com base no campo `codigo` como chave de negócio.  
Ele percorre todas as páginas da API, extrai os campos principais e mantém o banco sempre atualizado.

### Estrutura da Tabela no Banco

```sql
CREATE TABLE IF NOT EXISTS imoveis (
  id              BIGSERIAL PRIMARY KEY,
  codigo          TEXT        NOT NULL,
  categoria       TEXT,
  bairro          TEXT,
  status          TEXT,
  orulo           TEXT,
  exibirnosite    BOOLEAN,
  dataatualizacao DATE,
  datadeativacao  DATE,
  datacadastro    DATE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT imoveis_codigo_uniq UNIQUE (codigo)
);

CREATE INDEX IF NOT EXISTS idx_imoveis_bairro          ON imoveis (bairro);
CREATE INDEX IF NOT EXISTS idx_imoveis_status          ON imoveis (status);
CREATE INDEX IF NOT EXISTS idx_imoveis_exibirnosite    ON imoveis (exibirnosite);
CREATE INDEX IF NOT EXISTS idx_imoveis_dataatualizacao ON imoveis (dataatualizacao);
CREATE INDEX IF NOT EXISTS idx_imoveis_datacadastro    ON imoveis (datacadastro);
```

### Exemplo de arquivo `.env`

```env
# Credenciais do Supabase
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_KEY=sua_chave_api_supabase

# Chave da API do Vista CRM
API_IMOVEIS_KEY=sua_chave_api_vista

# URL da API de imóveis do Vista CRM
API_IMOVEIS_URL=https://seudominio.vistahost.com.br/imoveis/listar
```

### Como executar

1. Clone este repositório ou copie o script `ImportadorVista.py` para seu projeto.
2. Crie um arquivo `.env` na raiz do projeto com as credenciais e chaves (veja o exemplo acima).
3. Instale as dependências necessárias:

```bash
pip install requests python-dotenv supabase tqdm
```

4. Execute o script:

```bash
python ImportadorVista.py
```

### Exemplo de saída no terminal

```
Coletando páginas: 100%|██████████████████████████████████| 5/5 [00:12<00:00,  2.45s/pág]
Total coletado: 250
Exemplo do primeiro imóvel:
{
  "Codigo": "123456",
  "Categoria": "Apartamento",
  "Bairro": "Centro",
  "Status": "Venda",
  "Orulo": "Sim",
  "ExibirNoSite": true,
  "DataAtualizacao": "2025-08-01",
  "DataDeAtivacao": "2025-07-15",
  "DataCadastro": "2024-07-15"
}
250 imóveis inseridos/atualizados com sucesso.
```
