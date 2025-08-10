from __future__ import annotations

"""
Importa prontuários de imóveis da API Vista  e grava no Supabase.

Melhorias e profissionalizações:
- Tipagem, docstrings e comentários claros.
- Sessão HTTP com retries e timeout.
- Validação das variáveis de ambiente.
- Conversões/normalizações centralizadas (datas e booleanos).
- Paginação do Supabase com limites configuráveis.
- Coluna do código do imóvel configurável via .env (compatível com `codigo` ou `codigoimovel`).

Requisitos mínimos:
    pip install requests python-dotenv supabase tqdm
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter, Retry
from supabase import create_client, Client

# =========================
# Parâmetros de controle
# =========================

SLEEP_ENTRE_REQ = float(os.getenv("SLEEP_ENTRE_REQ", "0.4"))  # segundos entre requisições na API externa
MAX_RETRIES_API = int(os.getenv("MAX_RETRIES_API", "4"))      # tentativas por consulta
PAGINATION_LIMIT = int(os.getenv("PAGINATION_LIMIT", "1000"))  # lote de imóveis por consulta ao Supabase

# Nome da coluna que contém o código do imóvel na tabela `imoveis` (padrão: "codigo")
IMOVEIS_CODIGO_COL = os.getenv("IMOVEIS_CODIGO_COL", "codigo")

# =========================
# Ambiente (.env)
# =========================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_IMOVEIS_KEY = os.getenv("API_IMOVEIS_KEY")
API_IMOVEIS_URL = os.getenv("API_IMOVEIS_URL") #endpoint correto é /imoveis/detalhes  

HEADERS = {"Accept": "application/json"}


def validar_ambiente() -> None:
    """Garante a presença das variáveis obrigatórias do ambiente."""
    faltando = []
    for k, v in {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "API_IMOVEIS_KEY": API_IMOVEIS_KEY,
        "API_IMOVEIS_URL": API_IMOVEIS_URL,
    }.items():
        if not v:
            faltando.append(k)
    if faltando:
        raise EnvironmentError(f"Variáveis ausentes no .env: {', '.join(faltando)}")


def sessao_http() -> requests.Session:
    """Cria uma sessão HTTP com retries exponenciais e pool de conexões."""
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


def trata_boolean(valor: Any) -> Optional[bool]:
    """Converte valores comuns (sim/não/true/false) para booleano ou None."""
    if valor is None:
        return None
    s = str(valor).strip().lower()
    if s in {"sim", "true", "1"}:
        return True
    if s in {"nao", "não", "false", "0"}:
        return False
    return None


def trata_data(valor: Any) -> Optional[str]:
    """Normaliza datas inválidas para None (mantém strings válidas)."""
    if not valor or not isinstance(valor, str):
        return None
    v = valor.strip()
    if v in ("", "0000-00-00", "0000-00-00 00:00:00"):
        return None
    # Datas totalmente zeradas (edge cases)
    if v.replace("0", "").replace("-", "").replace(":", "").replace(" ", "") == "":
        return None
    return valor


def conectar_supabase() -> Client:
    """Cria o client do Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_codigos_imoveis(supabase: Client) -> List[str]:
    """
    Busca todos os códigos de imóveis na tabela `imoveis`, paginando conforme `PAGINATION_LIMIT`.

    A coluna utilizada é configurável via .env (`IMOVEIS_CODIGO_COL`), por padrão "codigo".
    """
    print("Buscando todos os códigos de imóveis no Supabase com paginação...")
    todos_codigos: List[str] = []
    pagina = 0
    limit = PAGINATION_LIMIT

    while True:
        # Range é inclusivo no Supabase: (from, to)
        inicio = pagina * limit
        fim = (pagina + 1) * limit - 1

        sel = f"{IMOVEIS_CODIGO_COL}"
        response = supabase.table("imoveis").select(sel).range(inicio, fim).execute()
        data = response.model_dump().get("data", [])

        codigos = [row.get(IMOVEIS_CODIGO_COL) for row in data if row.get(IMOVEIS_CODIGO_COL)]
        todos_codigos.extend(codigos)

        print(f"Página {pagina + 1} - códigos coletados: {len(codigos)}")
        if len(data) < limit:  # fim da paginação
            break
        pagina += 1

    print(f"Total de códigos encontrados: {len(todos_codigos)}")
    return todos_codigos


def busca_prontuarios_do_imovel(session: requests.Session, codigo_imovel: str) -> Optional[Dict[str, Any]]:
    """Consulta a API de detalhes com o campo `prontuarios` para um imóvel específico."""
    pesquisa = {
        "fields": [
            "Codigo",
            {
                "prontuarios": [
                    "Data", "Hora", "Assunto", "Texto", "Pendente", "Bairro", "Anunciado", "Retranca",
                    "Corretor", "PROPOSTA", "Status", "Datainicio", "VeiculoPublicado", "ValorProposta",
                    "BairroAnuncio", "StatusBatecao", "ValorBatido", "Privado", "Cliente", "Tipoanuncio",
                    "Titulado", "Statusdoimóvel", "CodigoCorretor",
                ]
            },
        ]
    }
    params = {
        "key": API_IMOVEIS_KEY,
        "pesquisa": json.dumps(pesquisa, ensure_ascii=False),
        "imovel": codigo_imovel,
    }

    tentativas = 0
    while tentativas < MAX_RETRIES_API:
        try:
            resp = session.get(API_IMOVEIS_URL, headers=HEADERS, params=params, timeout=25)

            # 400 específico: imóveis sem prontuários
            if resp.status_code == 400 and "prontuarios" in (resp.text or "").lower():
                print(f"Imóvel {codigo_imovel} sem prontuários (API 400). Pulando.")
                return None

            # Rate limit
            if resp.status_code == 429 or "too many connections" in (resp.text or "").lower():
                espera = 5 * (tentativas + 1)
                print(f"Rate limit para {codigo_imovel}. Aguardando {espera}s e tentando novamente...")
                time.sleep(espera)
                tentativas += 1
                continue

            if not resp.ok:
                print(f"HTTP {resp.status_code} ao consultar {codigo_imovel}: {resp.text[:200]}")
                tentativas += 1
                time.sleep(1 + 2 * tentativas)
                continue

            return resp.json()

        except Exception as e:
            print(f"Erro ao consultar {codigo_imovel}: {e}. Tentando novamente...")
            tentativas += 1
            time.sleep(1 + 2 * tentativas)

    print(f"Falha ao consultar {codigo_imovel} após {MAX_RETRIES_API} tentativas.")
    return None


def inserir_prontuarios_supabase(supabase: Client, prontuarios: Dict[str, Any], codigo_imovel: str) -> None:
    """Insere/atualiza prontuários no Supabase (tabela `imovel_prontuario`)."""
    if not prontuarios:
        print(f"Nenhum prontuário para inserir ({codigo_imovel}).")
        return

    registros: List[Dict[str, Any]] = []
    for cod, p in prontuarios.items():
        # Código do prontuário pode estar na chave ou no campo "Codigo" do objeto
        codigo_prontuario_raw = p.get("Codigo", cod) if isinstance(p, dict) else cod

        # Valores monetários: converte strings para float quando possível
        def to_float(v: Any) -> Optional[float]:
            if v in (None, ""):
                return None
            try:
                return float(v)
            except Exception:
                return None

        item = {
            "codigo_imovel": codigo_imovel,
            "codigo_prontuario": int(codigo_prontuario_raw) if str(codigo_prontuario_raw).isdigit() else None,
            "data": trata_data(p.get("Data")) if isinstance(p, dict) else None,
            "hora": p.get("Hora") if isinstance(p, dict) else None,
            "assunto": p.get("Assunto") if isinstance(p, dict) else None,
            "texto": p.get("Texto") if isinstance(p, dict) else None,
            "pendente": trata_boolean(p.get("Pendente")) if isinstance(p, dict) else None,
            "bairro": p.get("Bairro") if isinstance(p, dict) else None,
            "anunciado": trata_boolean(p.get("Anunciado")) if isinstance(p, dict) else None,
            "retranca": p.get("Retranca") if isinstance(p, dict) else None,
            "corretor": p.get("Corretor") if isinstance(p, dict) else None,
            "proposta": trata_boolean(p.get("PROPOSTA")) if isinstance(p, dict) else None,
            "status": p.get("Status") if isinstance(p, dict) else None,
            "datainicio": trata_data(p.get("Datainicio")) if isinstance(p, dict) else None,
            "veiculopublicado": p.get("VeiculoPublicado") if isinstance(p, dict) else None,
            "valorproposta": to_float(p.get("ValorProposta")) if isinstance(p, dict) else None,
            "bairroanuncio": p.get("BairroAnuncio") if isinstance(p, dict) else None,
            "statusbatecao": p.get("StatusBatecao") if isinstance(p, dict) else None,
            "valorbatido": to_float(p.get("ValorBatido")) if isinstance(p, dict) else None,
            "privado": trata_boolean(p.get("Privado")) if isinstance(p, dict) else None,
            "cliente": p.get("Cliente") if isinstance(p, dict) else None,
            "tipoanuncio": p.get("Tipoanuncio") if isinstance(p, dict) else None,
            "titulado": p.get("Titulado") if isinstance(p, dict) else None,
            "statusdoimovel": p.get("Statusdoimóvel") if isinstance(p, dict) else None,
            "codigocorretor": p.get("CodigoCorretor") if isinstance(p, dict) else None,
        }
        registros.append(item)

    try:
        print(f"Upsert de {len(registros)} prontuários (imóvel {codigo_imovel})...")
        res = supabase.table("imovel_prontuario").upsert(registros).execute()
        payload = res.model_dump()
        if payload.get("data") is not None:
            print(f"{len(payload['data'])} prontuários inseridos/atualizados ({codigo_imovel}).")
        else:
            print("Resposta inesperada do Supabase:", payload)
    except Exception as e:
        print(f"Erro ao inserir prontuários ({codigo_imovel}): {e}")


def processa_todos_os_imoveis() -> None:
    """Fluxo principal: lê códigos de `imoveis`, consulta API e grava prontuários."""
    validar_ambiente()
    supabase = conectar_supabase()
    session = sessao_http()

    codigos = get_codigos_imoveis(supabase)
    for i, codigo_imovel in enumerate(codigos, start=1):
        print(f"\n[{i}/{len(codigos)}] Consultando prontuários do imóvel {codigo_imovel}...")
        dados = busca_prontuarios_do_imovel(session, codigo_imovel)
        if not dados:
            continue

        prontuarios = dados.get("prontuarios") if isinstance(dados, dict) else None
        if prontuarios:
            inserir_prontuarios_supabase(supabase, prontuarios, codigo_imovel)
        else:
            print(f"Imóvel {codigo_imovel} sem prontuários para importar.")

        time.sleep(SLEEP_ENTRE_REQ)  # educado com a API


if __name__ == "__main__":
    try:
        processa_todos_os_imoveis()
    except Exception as exc:
        print(f"[ERRO] Execução interrompida: {exc}")
        raise
