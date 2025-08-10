/**

 * Objetivo:
 *   Este arquivo implementa um endpoint de leitura (GET) que atua como  intermediário entre o front-end e a API do Vista (Vistahost), com o objetivo de mostrar a possibilidade de manipulacao de consultas complexas com a api da plataforma CRM.
 *   o objetivo especifico deste exemplo é o retorno de métricas agregadas de "negócios" por etapa/status
 *   em períodos distintos: "semana" e "mes".
 *
 * Assinatura do endpoint (App Router): rota final: https://endereco.com/api/negocio/lead/aberto/mes
 *   /api/negocios/[etapa]/[status]/[periodo]
 *
 * Parâmetros de rota:
 *   - etapa   : string (será normalizada, ex.: "captação" -> "Captação")
 *   - status  : string (será normalizada, regra especial: "aberto" -> "Em aberto")
 *   - periodo : "semana" | "mes"
 *
 * Retornos:
 *   - periodo = "semana":
 *       {
 *         total: number,                  // soma dos últimos 7 dias (inclui hoje)
 *         porDia: { [YYYY-MM-DD]: number } // contagem por dia (TZ America/Sao_Paulo)
 *       }
 *
 *   - periodo = "mes":
 *       {
 *         total: number,       // total agregado do último mês (retroativo)
 *         valorTotal: number   // campo repassado da API de origem (quando disponível)
 *       }
 *
 * Observações:
 *   - Datas são calculadas e formatadas com timezone "America/Sao_Paulo"
 *     para evitar discrepâncias quando o servidor está em UTC.
 *   - Em "semana", o endpoint consulta a API dia a dia (janela [D, D+1)).
 *   - Em caso de erro em um dos dias, assume-se total=0 naquele dia.
 *   - Em qualquer erro geral, responde 500 com { error }.
 *   - Se período for diferente de "semana" ou "mes", responde 400.
 *
 * Variáveis de ambiente necessárias:
 *   - VISTAHOST_BASE_URL: base da API (ex.: https://seudominio.vistahost.com.br)
 *   - VISTAHOST_KEY     : chave de acesso à API do Vista
 *
 * Exemplos de uso (curl):
 *   - Últimos 7 dias (etapa=Captação, status=Em aberto):
 *     curl -s https://seu-dominio.com/api/negocios/lead/aberto/semana
 *
 *   - Último mês (etapa=Proposta, status=Ganho):
 *     curl -s https://seu-dominio.com/api/negocios/proposta/ganho/mes
 *
 * Onde colocar este arquivo:
 *   app/api/negocios/[etapa]/[status]/[periodo]/route.ts
 *   (o Next.js criará o endpoint conforme a estrutura de pastas acima)
 * ---------------------------------------------------------------------------
 */

import { NextRequest } from 'next/server';

/**
 * Converte um Date para YYYY-MM-DD fixando timezone em America/Sao_Paulo.
 * Evita erros de fuso quando o servidor executa em UTC.
 */
function formatDateSP(date: Date): string {
  const parts = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date);
  const map: Record<string, string> = {};
  for (const p of parts) if (p.type !== 'literal') map[p.type] = p.value;
  return `${map.year}-${map.month}-${map.day}`;
}

/** Retorna uma nova data somando (ou subtraindo) 'days' a partir de 'base'. */
function addDays(base: Date, days: number): Date {
  const d = new Date(base.getTime());
  d.setDate(d.getDate() + days);
  return d;
}

/** Normaliza o status: "aberto" -> "Em aberto"; demais capitalizam a 1ª letra. */
function normalizeStatus(s: string): string {
  const lower = s.toLowerCase();
  if (lower === 'aberto') return 'Em aberto';
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** Normaliza a etapa: apenas capitaliza a 1ª letra. */
function normalizeEtapa(e: string): string {
  const lower = e.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/**
 * Monta a URL de consulta à API do Vista.
 * IMPORTANTE: não expomos domínio/URL no código — usamos variável de ambiente.
 */
const buildUrl = (pesquisa: any) => {
  const base = process.env.VISTAHOST_BASE_URL?.replace(/\/+$/, '') ?? '';
  const key = process.env.VISTAHOST_KEY ?? '';
  // Endpoint final chamado externamente pelo Next:
  //   `${VISTAHOST_BASE_URL}/negocios/listar?key=${VISTAHOST_KEY}&codigo_pipe=1&showtotal=1&pesquisa=...`
  return `${base}/negocios/listar?key=${key}&codigo_pipe=1&showtotal=1&pesquisa=${encodeURIComponent(
    JSON.stringify(pesquisa)
  )}`;
};

/**
 * Handler GET do Next.js App Router.
 *
 * - Rota: /api/negocio/[etapa]/[status]/[periodo]
 * - Vide cabeçalho deste arquivo para detalhes completos.
 */
export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ etapa: string; status: string; periodo: string }> }
) {
  // Em rotas dinâmicas no App Router, ctx.params é uma Promise.
  const { etapa, status, periodo } = await ctx.params;

  // Validação mínima dos 3 parâmetros dinâmicos.
  if (!etapa || !status || !periodo) {
    return Response.json(
      { error: 'Parâmetros inválidos. Use /:etapa/:status/:periodo' },
      { status: 400 }
    );
  }

  const now = new Date(); // Momento base da requisição (TZ do servidor)

  // -------------------------------------------------------------------------
  // PERÍODO: "semana" => últimos 7 dias com quebra por dia
  // -------------------------------------------------------------------------
  if (periodo.toLowerCase() === 'semana') {
    try {
      const porDia: Record<string, number> = {};

      // Loop diário: hoje-6, ..., hoje-1, hoje
      // (startStr/endStr mantidos como referência; a consulta é feita dia a dia)
      const startStr = formatDateSP(addDays(now, -6));
      const endStr = formatDateSP(now);

      for (let i = 6; i >= 0; i--) {
        const day = addDays(now, -i);
        const diaStr = formatDateSP(day);
        const nextDayStr = formatDateSP(addDays(day, 1));

        const pesquisaDia = {
          fields: ['Codigo', 'DataInicial', 'NomeEtapa', 'Status'],
          filter: {
            NomeEtapa: normalizeEtapa(etapa),
            Status: normalizeStatus(status),
            DataInicial: [diaStr, nextDayStr], // janela [D, D+1)
          },
          order: { DataInicial: 'desc' },
          paginacao: { pagina: 1, quantidade: 50 }, // defensivo; API retorna "total"
        };

        const urlDia = buildUrl(pesquisaDia);
        let total = 0;

        try {
          const resDia = await fetch(urlDia, { headers: { Accept: 'application/json' } });
          if (!resDia.ok) throw new Error(`Erro na API de origem: ${resDia.status}`);
          const dataDia = await resDia.json();
          total = Number(dataDia?.total ?? 0);
        } catch {
          // Resiliência: se falhar um dia, contabiliza 0
          total = 0;
        }

        porDia[diaStr] = total;
      }

      const totalSemana = Object.values(porDia).reduce((acc, n) => acc + Number(n || 0), 0);

      return Response.json({
        total: totalSemana,
        porDia,
      });
    } catch (err: any) {
      return Response.json({ error: err.message }, { status: 500 });
    }
  }

  // -------------------------------------------------------------------------
  // PERÍODO: "mes" => últimos ~30/31 dias até HOJE (agregado)
  // -------------------------------------------------------------------------
  if (periodo.toLowerCase() === 'mes') {
    const inicio = new Date(now);
    inicio.setMonth(inicio.getMonth() - 1);

    const startStr = formatDateSP(inicio);
    const endStr = formatDateSP(now);

    const pesquisa = {
      fields: ['Codigo', 'DataInicial', 'NomeEtapa', 'Status'],
      filter: {
        NomeEtapa: normalizeEtapa(etapa),
        Status: normalizeStatus(status),
        DataInicial: [startStr, endStr],
      },
      order: { DataInicial: 'desc' },
      paginacao: { pagina: 1, quantidade: 50 },
    };

    const url = buildUrl(pesquisa);

    try {
      const res = await fetch(url, { headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`Erro na API de origem: ${res.status}`);
      const data = await res.json();
      // Repasse direto de total/valorTotal fornecidos pela API
      return Response.json({ total: data.total, valorTotal: data.valorTotal });
    } catch (err: any) {
      return Response.json({ error: err.message }, { status: 500 });
    }
  }

  // -------------------------------------------------------------------------
  // Período inválido
  // -------------------------------------------------------------------------
  return Response.json({ error: 'Período inválido. Use "semana" ou "mes".' }, { status: 400 });
}
