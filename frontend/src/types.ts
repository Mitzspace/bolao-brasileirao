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
export interface Bootstrap {
  usuario: Usuario | null;
  boloes: BolaoResumo[];
  bolaoAtualId: number | null;
  csrfToken: string;
  mensagens: string[];
  links: Partial<Record<View | 'palpites' | 'ranking' | 'tabela', string>> & {
    login: string; logout: string; selecionar: string; criarBolao: string;
    recuperarSenha: string; boloes: string;
  };
}
