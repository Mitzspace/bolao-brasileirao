/**
 * Cliente da API Flask (routes/api.py).
 * Usa a mesma sessão do sistema (cookie) e envia o token CSRF em toda gravação.
 *
 * Desempenho e segurança contra cliques repetidos:
 * - GETs ficam guardados em memória (cache) e são reaproveitados ao voltar para uma
 *   aba; a tela mostra o que já tinha e atualiza em segundo plano (useRecurso).
 * - Qualquer gravação (POST/PUT/PATCH/DELETE) limpa o cache inteiro, para nenhuma
 *   tela mostrar dado antigo depois de salvar.
 * - Duas gravações idênticas ao mesmo tempo (duplo clique, Enter + clique) viram uma só.
 * - Toda requisição tem tempo limite e mensagem clara de rede/tempo esgotado.
 * - O número de requisições em andamento alimenta a barra de progresso global.
 */

export class ApiError extends Error {
  status: number;
  dados: Record<string, unknown>;
  /** true quando a resposta não chegou (sem rede ou tempo esgotado). */
  semResposta: boolean;
  constructor(status: number, mensagem: string, dados: Record<string, unknown> = {}, semResposta = false) {
    super(mensagem);
    this.status = status;
    this.dados = dados;
    this.semResposta = semResposta;
  }
}

let base = '/interface/api';
let csrfToken = '';

export function configurarApi(opcoes: { base: string; csrfToken: string }) {
  base = opcoes.base.replace(/\/$/, '');
  csrfToken = opcoes.csrfToken;
}

type Metodo = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** O Render Free pode levar até ~1 min para acordar; depois disso, desistimos. */
export const TEMPO_LIMITE_MS = 75_000;
/** A partir daqui a barra de progresso avisa que o servidor pode estar acordando. */
export const AVISO_LENTO_MS = 6_000;

// ---------- Requisições em andamento (barra de progresso) ----------
type Ouvinte = (emAndamento: number, desde: number | null) => void;
let emAndamento = 0;
let desde: number | null = null;
const ouvintes = new Set<Ouvinte>();

function avisar() { ouvintes.forEach(o => o(emAndamento, desde)); }
function iniciar() { if (emAndamento++ === 0) desde = Date.now(); avisar(); }
function terminar() { if (--emAndamento <= 0) { emAndamento = 0; desde = null; } avisar(); }

export function acompanharRequisicoes(ouvinte: Ouvinte): () => void {
  ouvintes.add(ouvinte);
  ouvinte(emAndamento, desde);
  return () => { ouvintes.delete(ouvinte); };
}

// ---------- Cache de leituras ----------
const cache = new Map<string, unknown>();
const leiturasEmAndamento = new Map<string, Promise<unknown>>();
const gravacoesEmAndamento = new Map<string, Promise<unknown>>();
let geracao = 0; // muda a cada gravação: leituras antigas não voltam a ocupar o cache

export function lerDoCache<T>(caminho: string): T | undefined {
  return cache.get(caminho) as T | undefined;
}

export function limparCache() {
  cache.clear();
  leiturasEmAndamento.clear();
  geracao++;
}

async function requisitar<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (metodo !== 'GET') {
    headers['X-CSRFToken'] = csrfToken;
    headers['Content-Type'] = 'application/json';
  }
  const controle = new AbortController();
  const relogio = window.setTimeout(() => controle.abort(), TEMPO_LIMITE_MS);
  iniciar();
  let resposta: Response;
  try {
    resposta = await fetch(base + caminho, {
      method: metodo,
      headers,
      credentials: 'same-origin',
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: controle.signal,
    });
  } catch {
    const esgotado = controle.signal.aborted;
    const gravacao = metodo !== 'GET';
    const mensagem = esgotado
      ? (gravacao
        ? 'O servidor demorou demais para responder. A gravação pode ter sido concluída: confira a tela antes de salvar de novo.'
        : 'O servidor demorou demais para responder. Tente novamente em instantes.')
      : (gravacao
        ? 'Sem conexão com o servidor. Confira se a gravação aparece na tela antes de salvar de novo.'
        : 'Sem conexão com o servidor. Verifique sua internet e tente novamente.');
    throw new ApiError(0, mensagem, {}, true);
  } finally {
    window.clearTimeout(relogio);
    terminar();
  }
  const tipo = resposta.headers.get('Content-Type') ?? '';
  const dados = tipo.includes('application/json') ? await resposta.json() : null;
  if (!resposta.ok) {
    if (resposta.status === 401) {
      // Sessão expirada: volta para o login da nova interface.
      window.location.reload();
    }
    const mensagem = (dados && typeof dados.erro === 'string') ? dados.erro : 'Erro inesperado no servidor.';
    throw new ApiError(resposta.status, mensagem, dados ?? {});
  }
  return dados as T;
}

function ler<T>(caminho: string): Promise<T> {
  const pendente = leiturasEmAndamento.get(caminho);
  if (pendente) return pendente as Promise<T>;
  const minhaGeracao = geracao;
  const pedido = requisitar<T>('GET', caminho)
    .then(dados => {
      if (minhaGeracao === geracao) cache.set(caminho, dados);
      return dados;
    })
    .finally(() => {
      if (leiturasEmAndamento.get(caminho) === pedido) leiturasEmAndamento.delete(caminho);
    });
  leiturasEmAndamento.set(caminho, pedido);
  return pedido;
}

function gravar<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const chave = `${metodo} ${caminho} ${JSON.stringify(corpo ?? null)}`;
  const pendente = gravacoesEmAndamento.get(chave);
  if (pendente) return pendente as Promise<T>; // duplo clique: mesma gravação, uma requisição
  limparCache();
  const pedido = requisitar<T>(metodo, caminho, corpo).finally(() => {
    gravacoesEmAndamento.delete(chave);
    limparCache(); // inclui leituras feitas enquanto a gravação estava em andamento
  });
  gravacoesEmAndamento.set(chave, pedido);
  return pedido;
}

export const api = {
  get: <T>(caminho: string) => ler<T>(caminho),
  post: <T>(caminho: string, corpo?: unknown) => gravar<T>('POST', caminho, corpo ?? {}),
  put: <T>(caminho: string, corpo?: unknown) => gravar<T>('PUT', caminho, corpo ?? {}),
  patch: <T>(caminho: string, corpo?: unknown) => gravar<T>('PATCH', caminho, corpo ?? {}),
  delete: <T>(caminho: string) => gravar<T>('DELETE', caminho),
};
