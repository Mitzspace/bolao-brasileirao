export const views = ['dashboard', 'jogos', 'palpites', 'campeonatos', 'rodadas', 'participantes', 'boloes', 'configuracoes'] as const;
export type View = typeof views[number];

export interface Usuario { nome: string; email: string }

/** 'ativo' aparece na tela como "Em andamento". */
export type StatusBolao = 'ativo' | 'finalizado' | 'desistido';

export interface BolaoResumo {
  id: number;
  nome: string;
  status: StatusBolao;
  chave: string;
  campeonato: string;
  ano: number | null;
  /** Bolão principal do grupo: campeonatos do mesmo bolão têm o mesmo grupoId. */
  grupoId: number;
  /** Tema visual do campeonato ('copa-do-mundo'); null/ausente = visual padrão. */
  tema?: string | null;
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
  links: { login: string; logout: string; selecionar: string };
}

/** Resultado de services/escudos.escudo_time. */
export interface Escudo {
  fontes: string[];
  iniciais: string;
  /** Sigla de 3 letras usada no celular (ex.: FLA). */
  sigla: string;
}

export type StatusJogo = 'agendado' | 'aguardando' | 'encerrado';

export interface JogoApi {
  id: number;
  casa: string;
  fora: string;
  escudoCasa: Escudo;
  escudoFora: Escudo;
  data: string | null;
  /** Já formatado no horário de Brasília, ex.: "Qua 14/10 · 16:00". */
  dataTexto: string | null;
  classico: boolean;
  status: StatusJogo;
  golsCasa: number | null;
  golsFora: number | null;
  /** Mata-mata que pode ir aos pênaltis (palpite extra do placar dos pênaltis). */
  podePenaltis?: boolean;
  /** Placar da disputa de pênaltis, quando houve. */
  penaltisCasa?: number | null;
  penaltisFora?: number | null;
}

/** Sufixo do placar dos pênaltis, ex.: " (pên. 4 × 3)"; vazio se não houve. */
export function textoPenaltis(casa?: number | null, fora?: number | null): string {
  return casa != null && fora != null ? ` (pên. ${casa} × ${fora})` : '';
}

/** Jogo sem id: formato comum à gestão e à página pública (que não recebe ids do banco). */
export type JogoBase = Omit<JogoApi, 'id'>;

export interface ItemRanking {
  participacaoId: number;
  nome: string;
  status: 'ativo' | 'saiu' | 'removido' | 'desistente';
  posicao: number | null;
  /** > 0 subiu, < 0 caiu, 0 manteve, null sem comparação. */
  variacao: number | null;
  pontos: number;
  pontosPalpites: number;
  bonus: number;
  bonusPrimeiroGol: number;
  cravadas: number;
  acertosVencedor: number;
}

/** GET /interface/api/dashboard */
export interface DashboardApi {
  bolao: { id: number; nome: string; chave: string; campeonato: string; ano: number | null };
  participantesAtivos: number;
  /** Participantes com pelo menos um jogo em branco na rodada atual (mesmo que parcial). */
  palpitesFaltantes: number;
  /** Jogos em branco somados (todas as pessoas). */
  jogosFaltantes: number;
  pendentes: { id: number; nome: string; faltantes: number; total: number }[];
  rodada: { id: number; nome: string; aberta: boolean; numero: number | null; total: number; ultima: boolean } | null;
  jogos: JogoApi[];
  jogosEncerrados: number;
  top5: ItemRanking[];
  variacaoReferencia: string | null;
}

export interface JogoAtrasado extends JogoApi {
  rodadaId: number;
  rodadaNome: string;
}

export interface RodadaResumo { id: number; numero: number; nome: string; estado: EstadoRodada; faltantes: number }

/** GET /interface/api/jogos */
export interface AgendaApi {
  agora: string;
  rodada: {
    id: number; nome: string; aberta: boolean; numero: number | null; total: number; atual: boolean;
    inicio: string | null; inicioTexto: string | null; fimTexto: string | null; semHorario: number;
    anteriorId: number | null; proximaId: number | null;
  } | null;
  rodadaAtualId: number | null;
  rodadas: RodadaResumo[];
  jogos: JogoApi[];
  atrasados: JogoAtrasado[];
  horarios: { fonte: string; configurado: boolean; ultimaAtualizacao: string | null };
}

/** POST /interface/api/horarios/atualizar */
export interface AtualizacaoHorarios {
  status: 'ok' | 'recente' | 'sem_token' | 'sem_codigo' | 'erro';
  mensagem?: string;
  horariosAtualizados?: number;
}

/** Calculado pelos jogos: fechada (todos com resultado), pendente (iniciada e faltando palpite), aberta. */
export type EstadoRodada = 'aberta' | 'pendente' | 'fechada' | 'sem_jogos';

export interface RodadaGestao {
  id: number;
  nome: string;
  aberta: boolean;
  estado: EstadoRodada;
  faltantes: number;
  jogos: number;
  comResultado: number;
  podeExcluir: boolean;
}

/** Provedor de jogos e resultados. */
export type FonteApi = 'football-data' | 'api-football' | 'espn';

/** GET /interface/api/campeonato */
export interface CampeonatoApi {
  campeonato: { id: number; nome: string; ano: number | null; codigoApi: string; fonteApi?: FonteApi; totalRodadas: number; rodadasConcluidas: number };
  rodadas: RodadaGestao[];
  campeonatosDoBolao: { bolaoId: number; nome: string; ano: number | null; atual: boolean }[];
  adminGlobal: boolean;
  links: Record<string, never>;
}

export interface ZonaTabela { nome: string; cor: string; de: number; ate: number }

export interface LinhaTabela {
  posicao: number; time: string; timeCompleto: string; sigla: string; escudo: Escudo;
  pontos: number; jogos: number; vitorias: number; empates: number; derrotas: number;
  golsPro: number; golsContra: number; saldo: number; zona: ZonaTabela | null;
}

/** GET /interface/api/tabela */
export interface TabelaApi {
  sucesso: boolean;
  erro: string | null;
  aviso: string | null;
  fonteCache: boolean;
  horarioCache: string;
  competicao: string;
  /** Nome do provedor (football-data.org, ESPN…); ausente em respostas de erro. */
  fonte?: string;
  grupos: { nome: string; linhas: LinhaTabela[] }[];
  legendas: ZonaTabela[];
  mataMata: { nome: string; jogos: { id?: number; casa: string; fora: string; gols_casa: number | null; gols_fora: number | null; status: string; horario: string | null }[] }[];
  /** Jogos importados (ESPN), por rodada/fase; vazio nas outras fontes. */
  confrontos: { nome: string; jogos: JogoBase[] }[];
}

export interface JogoGestao extends JogoApi {
  rodadaId: number;
  encerrado: boolean;
  primeiroGol: string | null;
  /** Valor para <input type="datetime-local">, no horário de Brasília. */
  dataInput: string;
  palpites: number;
  podeExcluir: boolean;
  /** Clássicos: nomes de primeiro gol que os participantes palpitaram. */
  sugestoesPrimeiroGol: { nome: string; palpites: number }[];
}

/** GET /interface/api/rodadas */
export interface GestaoRodadasApi {
  rodadas: RodadaResumo[];
  rodadaAtualId: number | null;
  rodada: (RodadaResumo & { participantes: number }) | null;
  jogos: JogoGestao[];
  regras: Regras;
}

/** Regras de pontuação de um bolão. */
export interface Regras {
  comumExato: number; comumResultado: number; classicoExato: number; classicoResultado: number; primeiroGol: number;
  penaltisExato: number; penaltisVencedor: number;
}
export const REGRAS_PADRAO: Regras = {
  comumExato: 3, comumResultado: 1, classicoExato: 5, classicoResultado: 3, primeiroGol: 2, penaltisExato: 3, penaltisVencedor: 1,
};

/** GET /interface/api/rodadas/:id/classificacao */
export interface ClassificacaoRodadaApi { rodada: string; ranking: ItemRanking[] }

export type SituacaoPalpite = 'valido' | 'nao_enviado' | 'fora_prazo';

export interface JogoLancamento extends JogoApi {
  numero: number;
  iniciado: boolean;
  palpite: {
    casa: number | null; fora: number | null; primeiroGol: string; situacao: SituacaoPalpite;
    penaltisCasa: number | null; penaltisFora: number | null;
    guardado: boolean; pontos: number | null;
  } | null;
}

/** GET /interface/api/palpites */
export interface LancamentoApi {
  rodadas: RodadaResumo[];
  rodada: (RodadaResumo & { id: number }) | null;
  participantes: { id: number; nome: string; status: string; faltantes: number }[];
  pessoa: {
    id: number; nome: string; status: string; anteriorId: number | null; proximaId: number | null;
    /** Todos os jogos da rodada preenchidos: a tela abre fechada (botão Editar). */
    completo: boolean;
    /** Último lançamento feito pela mensagem do WhatsApp (aviso no topo), ou null. */
    whatsapp: { quandoTexto: string; rodada: string; autor: string | null } | null;
  } | null;
  jogos: JogoLancamento[];
}

/** GET /interface/api/palpites/historico — gaveta de alterações (só gestão). */
export type CanalPalpite = 'painel' | 'whatsapp' | 'desconhecida';
export interface ItemHistoricoPalpite {
  quando: string | null;
  quandoTexto: string | null;
  autor: string | null;
  canal: CanalPalpite;
  acao: string;
  rodada: string;
  recebidoEm: string | null;
  textoWhatsapp: string | null;
  mudancas: { jogo: string; antes: string | null; depois: string | null; detalhes: string[] }[];
}

/** POST /interface/api/palpites/previa-whatsapp */
export interface PreviaWhatsapp {
  linhas: { texto: string; jogo_id: number | null; casa: string; fora: string; primeiro_gol: string; avisos: string[] }[];
  jogos: { id: number; nome: string; avisos: string[]; bloqueado: boolean; primeiro_gol_permitido: boolean; pode_penaltis: boolean }[];
  reconhecido: boolean;
  token: string;
}

/** GET /interface/api/rodadas/:id/grade */
export interface GradeApi {
  rodada: string;
  participantes: { id: number; nome: string; pontos: number; cravadas: number; bonus: number }[];
  linhas: {
    jogo: JogoApi;
    celulas: Record<string, {
      casa: number; fora: number; primeiroGol: string; situacao: SituacaoPalpite; pontos: number | null; cravada: boolean; vencedor: boolean;
      penaltisCasa: number | null; penaltisFora: number | null; pontosPenaltis: number;
    } | null>;
  }[];
  textoWhatsapp: string;
}

/** GET /interface/api/participantes */
export type StatusParticipacao = 'ativo' | 'desistente' | 'removido' | 'saiu';
export interface ParticipanteApi {
  id: number;
  nome: string;
  email: string;
  observacao: string;
  status: StatusParticipacao;
  responsavel: boolean;
  temConta: boolean;
  rodadaEntrada: { id: number; nome: string } | null;
  rodadaDesistencia: { id: number; nome: string } | null;
  motivoDesistencia: string;
  pontos: number;
  palpites: number;
  cravadas: number;
  posicao: number | null;
  variacao: number | null;
  duplicado: boolean;
  souEu: boolean;
}
export interface ParticipantesApi {
  participantes: ParticipanteApi[];
  contagens: { todos: number; ativos: number; desistentes: number };
  rodadas: { id: number; nome: string }[];
  rodadaPadraoId: number | null;
  politicaEntrada: 'zero' | 'fora_da_conta' | string;
  regraDesistencia: string;
  variacaoReferencia: string | null;
}

export interface PalpiteGuardado { id: number; rodada: string; jogo: string; palpite: string; primeiroGol: string; jaGuardado: boolean }

/** GET /interface/api/participantes/:id */
export interface DetalheParticipanteApi {
  evolucao: { rodadaId: number; rodada: string; curto: string; pontos: number | null; cravadas: number; palpites: number; acumulado: number; posicao: number; participa: boolean }[];
  historico: { acao: string; autor: string; quando: string; mudancas: [string, string | null, string | null][] }[];
  guardados: PalpiteGuardado[];
}

/** GET /interface/api/boloes/:id/participantes/:pid/desempenho */
export interface DesempenhoParticipanteApi {
  nome: string;
  status: StatusParticipacao;
  resumo: { pontos: number; cravadas: number; posicao: number | null; variacao: number | null };
  variacaoReferencia: string | null;
  evolucao: DetalheParticipanteApi['evolucao'];
}

export type AcaoDesistencia = 'registrar' | 'corrigir' | 'reativar' | 'restaurar';
export interface PreviaDesistencia {
  previa: { acao: AcaoDesistencia; rodada: string | null; motivo: string; posteriores: PalpiteGuardado[]; restauraveis: PalpiteGuardado[] };
  token: string;
}

/** GET /interface/api/boloes */
export interface BoloesApi {
  boloes: {
    id: number; nome: string; chave: string; grupoId: number; campeonato: string; ano: number | null;
    status: StatusBolao; participantesAtivos: number; rodada: string | null;
    /** Participantes com algum jogo em branco na rodada atual. */
    palpitesFaltantes: number;
  }[];
}

/** GET /interface/api/boloes/:id/classificacao */
export interface ClassificacaoBolaoApi {
  bolao: { id: number; nome: string; chave: string; campeonato: string; ano: number | null; status: StatusBolao };
  campeonatosDoBolao: { bolaoId: number; nome: string; ano: number | null }[];
  rodadas: { id: number; nome: string }[];
  rodadaId: number | null;
  variacaoReferencia: string | null;
  ranking: ItemRanking[];
  textoWhatsapp: string;
  regras: Regras & { politicaEntrada: 'zero' | 'fora_da_conta' };
}

/** GET /interface/api/boloes/fontes */
export interface ModeloCompeticao {
  chave: string;
  rotulo: string;
  nome: string;
  codigo_api: string;
  fonte_api?: FonteApi;
  eliminacao: boolean;
  /** Estágio a partir do qual importar por padrão (ex.: LAST_32 na Copa do Brasil). */
  fase_inicial?: string;
  descricao: string;
  aviso: string | null;
}

export interface FontesBolaoApi {
  modelos: ModeloCompeticao[];
  fontes: { id: number; nome: string; campeonato: string; ano: number | null }[];
  pessoas: { id: number; nome: string; status: string }[];
}

/** GET /interface/api/responsaveis */
export interface ResponsaveisApi {
  responsaveis: { id: number; nome: string; email: string; souEu: boolean; semAcesso: boolean }[];
  participantesSemConta: { id: number; nome: string }[];
}

/** GET /interface/api/boloes/:id/publico — configuração do link público. */
export interface PublicoConfigApi {
  link: string | null;
  rodadaLiberada: { id: number; nome: string } | null;
  sugerida: { id: number; nome: string } | null;
  rodadas: { id: number; nome: string; jogos: number; comResultado: number; completa: boolean }[];
}

/** GET /interface/api/rodadas/:id/modelo-palpites */
export interface ModeloPalpitesApi {
  rodada: string;
  /** Modelo pronto para o WhatsApp (vazio quando todos os jogos já começaram). */
  texto: string;
  /** Ex.: "Palpites até sáb 18/10, 16h"; null quando nenhum jogo restante tem horário. */
  prazo: string | null;
  incluidos: number;
  /** Jogos que já começaram e ficaram fora do modelo. */
  omitidos: number;
}
