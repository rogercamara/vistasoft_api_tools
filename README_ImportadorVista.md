## 🎯 Objetivo
Script Python para importar **imóveis** da API Vistahost (ou compatível) e inserir/atualizar (upsert) no banco de dados (Postgres/Supabase).
Usa paginação automática e normaliza campos de data e booleanos.

## 🛠 Tecnologias
- Python 3.9+
- requests
- python-dotenv
- supabase-py

## ⚙️ Variáveis de Ambiente (.env)
```env
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_KEY=sua_chave_api_supabase
API_IMOVEIS_KEY=sua_chave_api_vista
API_BASE_URL=https://seudominio.vistahost.com.br
API_LISTAR_PATH=/imoveis/listar
PAGE_SIZE=50
```

## ▶️ Execução
```bash
pip install requests python-dotenv supabase tqdm
python ImportadorVista.py
```

## 📌 Observações
- Faz *upsert* usando `codigo` como chave.
- Remove campos inválidos de data ("0000-00-00").
- Pode retomar progresso se configurado para salvar localmente.
