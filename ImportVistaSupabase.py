from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter, Retry
from supabase import Client, create_client
from tqdm import tqdm

# =========================
# Configuração e Constantes
# =========================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_IMOVEIS_KEY = os.getenv("API_IMOVEIS_KEY")
API_IMOVEIS_URL = os.getenv("API_IMOVEIS_URL")  x

HEADERS = {"Accept": "application/json"}
PAGINACAO_QTD = 50
TIMEOUT = 30  # segundos


def validar_ambiente() -> None:
    faltando = []
    if not SUPABASE_URL:
        faltando.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        faltando.append("SUPABASE_KEY")
    if not API_IMOVEIS_KEY:
        faltando.append("API_IMOVEIS_KEY")
    if not API_IMOVEIS_URL:
        faltando.append("API_IMOVEIS_URL")
    if faltando:
        raise EnvironmentError(
            f"As seguintes variáveis de ambiente estão ausentes: {', '.join(faltando)}"
        )


def sessao_http() -> requests.Session:
    """Sessao com retries exponenciais"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def parse_json_resposta(resp: requests.Response) -> Dict[str, Any]:
    """Decodifica json e trata com mensagem carinhosa o bonito"""
    try:
        return resp.json()
    except Exception as e:
        corpo = resp.text[:1000]
        raise ValueError(
            f"Erro ao decodificar JSON. Status={resp.status_code}. Corpo (parcial): {corpo}"
        ) from e


def montar_pesquisa(pagina: int, quantidade: int) -> Dict[str, Any]:
    """Payload de pesquisa esperado pela API."""
    return {
        "fields": [
            "Codigo", "Categoria", "Bairro", "Status", "Orulo", "DataCadastro",
            "DataDeAtivacao", "DataAtualizacao", "ExibirNoSite",
        ],
        "paginacao": {"pagina": pagina, "quantidade": quantidade},
    }


def parametros_requisicao(pagina: int, quantidade: int) -> Dict[str, Any]:
    """Query string para a API."""
    return {
        "key": API_IMOVEIS_KEY,
        "showtotal": 1, 
        "showInternal": 1, # Lista os imoveis inativos
        "pesquisa": json.dumps(montar_pesquisa(pagina, quantidade)),
    }


def tratar_data(valor: Optional[str]) -> Optional[str]:
    """Transforma datas inválidas e vazias para None."""
    if not valor or valor == "0000-00-00":
        return None
    return valor


def normalizar_item(im: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia e normaliza campos para a tabela Supabase `imoveis`."""
    return {
        "codigo": im.get("Codigo"),
        "categoria": im.get("Categoria"),
        "bairro": im.get("Bairro"),
        "status": im.get("Status"), 
        "orulo": im.get("Orulo"), # Util para realizar queries posteriores de acordo com o objetivo do serviço final
        "exibirnosite": im.get("ExibirNoSite"), 
        "dataatualizacao": tratar_data(im.get("DataAtualizacao")),
        "datadeativacao": tratar_data(im.get("DataDeAtivacao")),
        "datacadastro": tratar_data(im.get("DataCadastro")),
    }


def extrair_itens(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int, int]:
    """Extrai os itens e metadados de paginação da API."""
    itens: List[Dict[str, Any]] = [
        item for key, item in data.items()
        if key not in {"total", "paginas", "pagina", "quantidade"} and isinstance(item, dict)
    ]
    pagina_atual = int(data.get("pagina", 1))
    total_paginas = int(data.get("paginas", 1))
    return itens, pagina_atual, total_paginas


def listar_imoveis() -> List[Dict[str, Any]]:
    """
    Percorre a paginação da API e retorna todos os imóveis, comecando sempre pela primeira pagina de resultados
    """
    todos: List[Dict[str, Any]] = []
    session = sessao_http()

    # Requisição inicial para obter total de páginas
    resp = session.get(
        API_IMOVEIS_URL,
        headers=HEADERS,
        params=parametros_requisicao(1, PAGINACAO_QTD),
        timeout=TIMEOUT,
    )
    data = parse_json_resposta(resp)
    if "status" in data and "message" in data:
        raise RuntimeError(f"Erro API: {data.get('message')} (status {data.get('status')})")

    _, _, total_paginas = extrair_itens(data)

    for pagina in tqdm(range(1, total_paginas + 1), desc="Coletando páginas", unit="pág"):
        resp = session.get(
            API_IMOVEIS_URL,
            headers=HEADERS,
            params=parametros_requisicao(pagina, PAGINACAO_QTD),
            timeout=TIMEOUT,
        )
        data = parse_json_resposta(resp)
        if "status" in data and "message" in data:
            raise RuntimeError(f"Erro API (página {pagina}): {data.get('message')}")

        itens, _, _ = extrair_itens(data)
        todos.extend(itens)

    return todos


def conectar_supabase() -> Client:
    """Cliente Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def inserir_imoveis_supabase(imoveis: List[Dict[str, Any]], supabase: Client) -> None:
    """Upsert em lote na tabela `imoveis`."""
    if not imoveis:
        print("Nenhum imóvel para inserir.")
        return

    registros = [normalizar_item(im) for im in imoveis]
    print(f"Inserindo/atualizando {len(registros)} imóveis no Supabase...")
    res = supabase.table("imovel_local").upsert(registros, on_conflict=["codigo"]).execute()
    payload = res.model_dump()

    if payload.get("data") is not None:
        print(f"{len(payload['data'])} imóveis inseridos/atualizados com sucesso.")
    else:
        print("Erro Supabase:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    validar_ambiente()
    imoveis = listar_imoveis()
    print(f"Total coletado: {len(imoveis)}")
    if imoveis:
        print("Exemplo do primeiro imóvel:")
        print(json.dumps(imoveis[0], indent=2, ensure_ascii=False))
    supabase = conectar_supabase()
    inserir_imoveis_supabase(imoveis, supabase)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERRO] {e}")
        raise
