
## 🎯 Objetivo
Versão MySQL do importador de imóveis.
Importa imóveis da API Vistahost e realiza *upsert* (`ON DUPLICATE KEY UPDATE`) na tabela `imoveis_local`.

## 🛠 Tecnologias
- Python 3.9+
- requests
- python-dotenv
- mysql-connector-python

## ⚙️ Variáveis de Ambiente (.env)
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=imobiliaria
DB_TABLE_IMOVEIS=imoveis_local
API_IMOVEIS_KEY=sua_chave_api_vista
API_BASE_URL=https://seudominio.vistahost.com.br
API_LISTAR_PATH=/imoveis/listar
PAGE_SIZE=50
```

## ▶️ Execução
```bash
pip install requests python-dotenv mysql-connector-python
python importa_imoveis_mysql.py
```

## 📌 Observações
- Campos de data e booleanos são normalizados.
- Executa inserções em lote (`executemany`).
