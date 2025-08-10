
## 🎯 Objetivo
Script Python para importar **prontuários de imóveis** da API Vistahost e inserir/atualizar na tabela `imovel_prontuario`.
Usa rate limit seguro e tratamento de erros com múltiplas tentativas.

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
API_DETALHES_PATH=/imoveis/detalhes
```

## ▶️ Execução
```bash
pip install requests python-dotenv supabase tqdm
python ImportadorProntuarios.py
```

## 📌 Observações
- Itera sobre todos os códigos de imóveis já salvos.
- Faz upsert em lote com `codigo_imovel` + `codigo_prontuario` como chave única.
- Converte datas e valores monetários para tipos seguros.
