Ferramentas que auxiliam na extração de dados da API REST do CRM Vista para imobiliárias.

# ImportadorVista.py

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



# ImportadorProntuarios.py

Script coletar o campo `prontuarios` de cada imóvel e gravar/atualizar no banco (tabela `imovel_prontuario`).  

Ele lê todos os códigos da tabela `imoveis`, respeita limites de taxa da API (com *retries* e pequenas pausas), normaliza dados (datas/booleanos) e executa *upsert* em lote no Supabase.

### Variáveis de ambiente (.env)

```env
# Supabase
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_KEY=sua_chave_api_supabase

# Vista CRM
API_IMOVEIS_KEY=sua_chave_api_vista
API_IMOVEIS_URL=https://seudominio.vistahost.com.br/imoveis/detalhes

# Opções (ajuste conforme necessidade)
SLEEP_ENTRE_REQ=0.4
MAX_RETRIES_API=4
PAGINATION_LIMIT=1000

# Nome da coluna do código do imóvel na tabela `imoveis`
# Use 'codigo' (recomendado para alinhar com o schema abaixo)
# ou 'codigoimovel' se sua base já estiver assim.
IMOVEIS_CODIGO_COL=codigo
```

### Esquema SQL sugerido (tabela de prontuários)

```sql
-- Função para updated_at automático
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tabela de prontuários
CREATE TABLE IF NOT EXISTS imovel_prontuario (
  id                 BIGSERIAL PRIMARY KEY,
  codigo_imovel      TEXT        NOT NULL,                -- referência ao imóvel (imoveis.codigo)
  codigo_prontuario  BIGINT      NOT NULL,                -- identificador do prontuário na origem
  data               DATE,
  hora               TEXT,
  assunto            TEXT,
  texto              TEXT,
  pendente           BOOLEAN,
  bairro             TEXT,
  anunciado          BOOLEAN,
  retranca           TEXT,
  corretor           TEXT,
  proposta           BOOLEAN,
  status             TEXT,
  datainicio         DATE,
  veiculopublicado   TEXT,
  valorproposta      NUMERIC,
  bairroanuncio      TEXT,
  statusbatecao      TEXT,
  valorbatido        NUMERIC,
  privado            BOOLEAN,
  cliente            TEXT,
  tipoanuncio        TEXT,
  titulado           TEXT,
  statusdoimovel     TEXT,
  codigocorretor     TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT imovel_prontuario_uk UNIQUE (codigo_imovel, codigo_prontuario)
);

-- Trigger de atualização do updated_at
DROP TRIGGER IF EXISTS trg_imovel_prontuario_updated_at ON imovel_prontuario;
CREATE TRIGGER trg_imovel_prontuario_updated_at
BEFORE UPDATE ON imovel_prontuario
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_prontuario_cod_imovel ON imovel_prontuario (codigo_imovel);
CREATE INDEX IF NOT EXISTS idx_prontuario_data       ON imovel_prontuario (data);
```

### Execução

```bash
pip install requests python-dotenv supabase tqdm
python ImportadorProntuarios.py
```

> Observação: por padrão, o script espera que a tabela `imoveis` tenha a coluna `codigo` como chave de negócio.  
> Se a sua base usa `codigoimovel`, defina `IMOVEIS_CODIGO_COL=codigoimovel` no `.env`.

