/** Respostas da API pública (routes/publico.py). Nada aqui tem ids internos ou dados pessoais. */
import type { JogoBase, Regras } from '@/types';

export interface DadosPagina {
  bolao: { nome: string; campeonato: string; ano: number | null; tema?: string | null };
  apiBase: string;
}

export type SituacaoRodada = 'encerrada' | 'andamento' | 'agendada';
export interface RodadaPublica {
  numero: number; nome: string; situacao: SituacaoRodada; comResultado: number; jogos: number;
  /** true quando a rodada está liberada pelos organizadores (palpites e pontos visíveis). */
  palpitesLiberados: boolean;
}
export interface TabelaLiberada { numero: number; nome: string }

/** Mesmo formato do jogo da gestão, sem id. */
export type JogoPublico = JogoBase;

export interface ItemClassificacao {
  posicao: number; ref: string; nome: string; status: string; pontos: number; pontosPalpites: number; bonus: number;
  bonusPrimeiroGol: number; cravadas: number; acertos: number; variacao: number | null;
}

export type RegrasPublicas = Regras & { politicaEntrada: 'zero' | 'fora_da_conta' | string };

export interface InicioApi {
  bolao: DadosPagina['bolao'];
  tabela: TabelaLiberada | null;
  participantesAtivos: number;
  rodada: (RodadaPublica & { total: number }) | null;
  jogos: JogoPublico[];
  lideres: ItemClassificacao[] | null;
  variacaoReferencia: string | null;
  regras: RegrasPublicas;
}

export type ClassificacaoApi = { liberada: false } | {
  liberada: true; ate: TabelaLiberada; rodadas: { numero: number; nome: string }[];
  rodada: number | null; variacaoReferencia: string | null; itens: ItemClassificacao[];
};

export interface JogoAtrasadoPublico extends JogoPublico { rodadaNome: string }
export interface JogosApi {
  agora: string;
  rodadas: RodadaPublica[];
  rodada: (RodadaPublica & {
    total: number; atual: boolean; inicio: string | null; inicioTexto: string | null; fimTexto: string | null; semHorario: number;
  }) | null;
  atual: number | null;
  jogos: JogoPublico[];
  atrasados: JogoAtrasadoPublico[];
}

export interface PalpitePublico {
  nome: string; ref: string; status: string;
  situacao: 'valido' | 'sem_palpite' | 'nao_enviado' | 'fora_prazo';
  casa?: number; fora?: number; primeiroGol?: string; pontos?: number;
  penaltisCasa?: number; penaltisFora?: number;
}
export interface JogoComPalpites extends JogoPublico { numero: number; revelado: boolean; palpites?: PalpitePublico[] }
export interface PalpitesApi {
  rodadas: RodadaPublica[]; rodada: RodadaPublica | null; pontosLiberados: boolean; palpitesLiberados: boolean;
  tabela: TabelaLiberada | null; participantes: number; jogos: JogoComPalpites[];
}

export interface ParticipantesApi {
  tabela: TabelaLiberada | null;
  participantes: { nome: string; ref: string; status: string; posicao?: number | null; pontos?: number; cravadas?: number }[];
}

export interface EvolucaoPublica {
  numero: number; rodada: string; curto: string; pontos: number | null; cravadas: number;
  palpites: number; acumulado: number; posicao: number; participa: boolean;
}
/** GET /participantes/<ref>: desempenho até a rodada liberada. */
export type ParticipantePublicoApi = { ref: string; nome: string; status: string; tabela: TabelaLiberada | null } & (
  { liberada: false } | {
    liberada: true; posicao: number | null; variacao: number | null; variacaoReferencia: string | null;
    pontos: number; cravadas: number; acertos: number; bonus: number; evolucao: EvolucaoPublica[];
  });

/** Abre o painel de um participante (pela referência pública). */
export type AbrirParticipante = (p: { ref: string; nome: string }) => void;
