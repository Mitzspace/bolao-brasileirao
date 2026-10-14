/**
 * Cliente da API Flask (routes/api.py).
 * Usa a mesma sessão do sistema (cookie) e envia o token CSRF em toda gravação.
 */

export class ApiError extends Error {
  status: number;
  dados: Record<string, unknown>;
  constructor(status: number, mensagem: string, dados: Record<string, unknown> = {}) {
    super(mensagem);
    this.status = status;
    this.dados = dados;
  }
}

let base = '/interface/api';
let csrfToken = '';

export function configurarApi(opcoes: { base: string; csrfToken: string }) {
  base = opcoes.base.replace(/\/$/, '');
  csrfToken = opcoes.csrfToken;
}

type Metodo = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

async function requisitar<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (metodo !== 'GET') {
    headers['X-CSRFToken'] = csrfToken;
    headers['Content-Type'] = 'application/json';
  }
  let resposta: Response;
  try {
    resposta = await fetch(base + caminho, {
      method: metodo,
      headers,
      credentials: 'same-origin',
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    throw new ApiError(0, 'Sem conexão com o servidor. Verifique sua internet e tente novamente.');
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

export const api = {
  get: <T>(caminho: string) => requisitar<T>('GET', caminho),
  post: <T>(caminho: string, corpo?: unknown) => requisitar<T>('POST', caminho, corpo ?? {}),
  put: <T>(caminho: string, corpo?: unknown) => requisitar<T>('PUT', caminho, corpo ?? {}),
  patch: <T>(caminho: string, corpo?: unknown) => requisitar<T>('PATCH', caminho, corpo ?? {}),
  delete: <T>(caminho: string) => requisitar<T>('DELETE', caminho),
};
