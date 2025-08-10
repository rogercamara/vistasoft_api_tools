import requests
import json
import os
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

API_IMOVEIS_KEY = os.getenv("API_IMOVEIS_KEY")
API_URL = "https://seu-endereco.vistahost.com.br/imoveis/listar"
HEADERS = {"Accept": "application/json"}

def trata_data(valor):
    if not valor or not isinstance(valor, str):
        return None
    valor_limpo = valor.strip()
    if (
        valor_limpo in ("", "0000-00-00", "0000-00-00 00:00:00")
        or valor_limpo.replace("0", "").replace("-", "").replace(":", "").replace(" ", "") == ""
    ):
        return None
    return valor

def listar_imoveis():
    todos_imoveis = []
    pagina = 1
    quantidade = 50
    while True:
        pesquisa = {
            "fields": [
                "Codigo", "Categoria", "Bairro", "Status", "Orulo",
                "DataHoraAtualizacao", "PendenteProntuario",
                "DataDeAtivacao", "DataAtualizacao"
            ],
            "paginacao": {
                "pagina": pagina,
                "quantidade": quantidade
            }
        }
        params = {
            "key": API_IMOVEIS_KEY,
            "showtotal": 1,
            "showInternal: 1,
            "pesquisa": json.dumps(pesquisa)
        }
        print(f"Consultando página {pagina}...")
        response = requests.get(API_URL, headers=HEADERS, params=params)
        try:
            data = response.json()
        except Exception as e:
            print("Erro ao decodificar JSON da resposta:")
            print(response.text)
            raise

        print(f"Resposta da API (chaves): {list(data.keys())}")

        # Se a resposta vier com status/message, é erro da API
        if "status" in data and "message" in data:
            print(f"ERRO da API: {data.get('message')} (status {data.get('status')})")
            print("RESPOSTA COMPLETA DA API:", data)
            break

        imoveis_coletados = 0
        for key, item in data.items():
            if key in ["total", "paginas", "pagina", "quantidade"]:
                continue
            if isinstance(item, dict):
                todos_imoveis.append(item)
                imoveis_coletados += 1
            else:
                print(f"Ignorando item inesperado na chave {key}: {item}")
        print(f"Imóveis coletados nesta página: {imoveis_coletados}")

        paginas = data.get("paginas", 1)
        if pagina >= paginas:
            break
        pagina += 1
    print(f"Total geral coletado: {len(todos_imoveis)}")
    return todos_imoveis

def salvar_imoveis_csv(imoveis, nome_arquivo="imoveis.csv"):
    if not imoveis:
        print("Nenhum imóvel para salvar!")
        return
    lista_final = []
    for im in imoveis:
        item = {
            "codigoimovel": im.get("Codigo"),
            "categoria": im.get("Categoria"),
            "bairro": im.get("Bairro"),
            "status": im.get("Status"),
            "orulo": im.get("Orulo"),
            "datahoraatualizacao": trata_data(im.get("DataHoraAtualizacao")),
            "pendenteprontuario": im.get("PendenteProntuario"),
            "datadeativacao": trata_data(im.get("DataDeAtivacao")),
            "dataatualizacao": trata_data(im.get("DataAtualizacao")),
        }
        lista_final.append(item)
    df = pd.DataFrame(lista_final)
    df.to_csv(nome_arquivo, index=False, encoding="utf-8-sig")
    print(f"{len(df)} imóveis salvos em {nome_arquivo}")

if __name__ == "__main__":
    imoveis = listar_imoveis()
    if imoveis:
        print("Exemplo do primeiro imóvel coletado:")
        print(json.dumps(imoveis[0], indent=2, ensure_ascii=False))
        salvar_imoveis_csv(imoveis)
    else:
        print("Nenhum imóvel coletado para salvar.")
