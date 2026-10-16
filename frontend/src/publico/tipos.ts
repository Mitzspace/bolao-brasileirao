/** Respostas da API pública (routes/publico.py). Nada aqui tem ids internos ou dados pessoais. */
import type { Escudo } from '@/types';

export interface DadosPagina {
  bolao: { nome: string; campeonato: string; ano: number | null };
  apiBase: string;
}

export type SituacaoRodada = 'encerrada' | 'andamento' | 'agendada';
export interface RodadaPublica { numero: number; nome: string; situacao: SituacaoRodada; comResultado: number; jogos: number }
export interface TabelaLiberada { numero: number; nome: string }

export interface JogoPublico {
  casa: string; fora: string; escudoCasa: Escudo; escudoFora: Escudo;
  data: string | null; dataTexto: string | null; classico: boolean;
  status: 'encerrado' | 'aguardando' | 'agendado';
  golsCasa: number | null; golsFora: number | null;
}

export interface ItemClassificacao {
  posicao: number; nome: string; status: string; pontos: number; pontosPalpites: number; bonus: number;
  cravadas: number; acertos: number; variacao: number | null;
}

export interface InicioApi {
  bolao: DadosPagina['bolao'];
  tabela: TabelaLiberada | null;
  participantesAtivos: number;
  rodada: (RodadaPublica & { total: number }) | null;
  jogos: JogoPublico[];
  lideres: ItemClassificacao[] | null;
}

export type ClassificacaoApi = { liberada: false } | {
  liberada: true; ate: TabelaLiberada; rodadas: { numero: number; nome: string }[];
  rodada: number | null; itens: ItemClassificacao[];
};

export interface JogosApi { rodadas: RodadaPublica[]; rodada: RodadaPublica | null; atual: number | null; jogos: JogoPublico[] }

export interface PalpitePublico {
  nome: string; status: string;
  situacao: 'valido' | 'sem_palpite' | 'nao_enviado' | 'fora_prazo';
  casa?: number; fora?: number; primeiroGol?: string; pontos?: number;
}
export interface JogoComPalpites extends JogoPublico { numero: number; revelado: boolean; palpites?: PalpitePublico[] }
export interface PalpitesApi {
  rodadas: RodadaPublica[]; rodada: RodadaPublica | null; pontosLiberados: boolean;
  tabela: TabelaLiberada | null; participantes: number; jogos: JogoComPalpites[];
}

export interface ParticipantesApi {
  tabela: TabelaLiberada | null;
  participantes: { nome: string; status: string; posicao?: number | null; pontos?: number; cravadas?: number }[];
}
