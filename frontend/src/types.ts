export const views = ['dashboard', 'campeonatos', 'rodadas', 'participantes', 'boloes', 'configuracoes'] as const;
export type View = typeof views[number];

export interface Usuario { nome: string; email: string }

export interface BolaoResumo {
  id: number;
  nome: string;
  chave: string;
  campeonato: string;
  ano: number | null;
}

export interface Mensagem {
  tipo: 'success' | 'error' | 'info';
  texto: string;
}

/** Dados iniciais gravados pelo Flask em templates/interface.html. */
export interface Bootstrap {
  usuario: Usuario | null;
  boloes: BolaoResumo[];
  bolaoAtualId: number | null;
  csrfToken: string;
  apiBase: string;
  mensagens: Mensagem[];
  links: Partial<Record<View | 'palpites' | 'ranking' | 'tabela', string>> & {
    login: string; logout: string; selecionar: string; criarBolao: string;
    recuperarSenha: string; boloes: string;
  };
}

/** Resultado de services/escudos.escudo_time. */
export interface Escudo {
  fontes: string[];
  iniciais: string;
}

/** GET /interface/api/contexto */
export interface ContextoApi {
  usuario: { id: number; nome: string; email: string; adminGlobal: boolean };
  bolao: (BolaoResumo & { campeonatoId: number }) | null;
}
