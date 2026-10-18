import type { ReactNode } from 'react';
import { AlarmClock, CalendarClock, CheckCircle2, GitFork, History, ListOrdered, Table2, Users } from 'lucide-react';
import { JogoLinha } from '@/components/jogos/JogoLinha';
import { SeletorRodadas } from '@/components/rodadas/SeletorRodadas';
import { fasesDaChave } from '@/lib/chaveamento';
import type { JogoBase, RodadaResumo, TabelaApi } from '@/types';

/** Datas chegam no horário de Brasília sem fuso; a diferença usa o "agora" do servidor. */
function lerData(valor: string) {
  const [d, h = '00:00:00'] = valor.split('T');
  const [a, m, dia] = d.split('-').map(Number);
  const [hh, mm] = h.split(':').map(Number);
  return Date.UTC(a, m - 1, dia, hh, mm);
}

export interface RodadaAgenda {
  nome: string; numero: number | null; total: number; atual: boolean;
  inicio: string | null; inicioTexto: string | null; fimTexto: string | null; semHorario: number;
}

function situacaoRodada(rodada: RodadaAgenda, jogos: JogoBase[], agora: string) {
  const encerrados = jogos.filter(j => j.status === 'encerrado').length;
  if (jogos.length && encerrados === jogos.length) return { texto: 'Rodada encerrada', cor: 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' };
  if (!rodada.inicio) return { texto: 'Horários a definir', cor: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' };
  const minutos = Math.round((lerData(rodada.inicio) - lerData(agora)) / 60000);
  if (minutos <= 0) return { texto: 'Em andamento', cor: 'bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300' };
  const dias = Math.floor(minutos / 1440);
  const horas = Math.floor((minutos % 1440) / 60);
  const texto = dias > 0 ? `Começa em ${dias} ${dias === 1 ? 'dia' : 'dias'}${horas ? ` e ${horas} h` : ''}`
    : horas > 0 ? `Começa em ${horas} h ${minutos % 60} min` : `Começa em ${minutos} min`;
  return { texto, cor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' };
}

interface Props {
  agora: string;
  rodadas: RodadaResumo[];
  selecionadaId: number | null;
  atualId: number | null;
  onSelecionar: (id: number) => void;
  /** Volta para a rodada atual (aparece quando outra rodada está selecionada). */
  onIrAtual?: () => void;
  rodada: RodadaAgenda;
  jogos: JogoBase[];
  atrasados: (JogoBase & { rodadaNome: string })[];
  carregando?: boolean;
  /** Selo ao lado do título dos jogos (a gestão mostra o estado com palpites faltantes). */
  selo?: ReactNode;
  rodape?: ReactNode;
}

/** Aba Jogos do Bolt: carrossel de rodadas, destaque, jogos da rodada e jogos atrasados. */
export function AgendaRodada({ agora, rodadas, selecionadaId, atualId, onSelecionar, onIrAtual, rodada: r, jogos, atrasados,
  carregando = false, selo, rodape }: Props) {
  const situacao = situacaoRodada(r, jogos, agora);
  return (
    <>
      {/* Navegação rápida entre rodadas */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-3 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
        <SeletorRodadas rodadas={rodadas} selecionadaId={selecionadaId} atualId={atualId} onSelecionar={onSelecionar} />
      </div>

      {/* Destaque da rodada */}
      <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden animate-fade-in">
        <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4" />
        <div className="relative flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <p className="text-white/80 text-sm">{r.atual ? 'Rodada atual' : 'Rodada selecionada'}{r.numero ? ` · ${r.numero}/${r.total}` : ''}</p>
            <h2 className="text-2xl font-bold mt-1">{r.nome}</h2>
            <p className="text-white/90 text-sm mt-2 flex items-center gap-2">
              <CalendarClock className="w-4 h-4 shrink-0" />
              {r.inicioTexto ? <span>Início: <strong>{r.inicioTexto}</strong>{r.fimTexto && r.fimTexto !== r.inicioTexto ? <> · último jogo: {r.fimTexto}</> : null}</span> : 'Horários ainda não divulgados'}
            </p>
            {r.semHorario > 0 && r.inicioTexto && (
              <p className="text-white/70 text-xs mt-1">{r.semHorario} {r.semHorario === 1 ? 'jogo ainda sem horário' : 'jogos ainda sem horário'}</p>
            )}
          </div>
          <span className={`self-start sm:self-auto inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${situacao.cor}`}>{situacao.texto}</span>
        </div>
      </div>

      {/* Jogos da rodada */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-4">
          <h3 className="font-bold text-gray-900 dark:text-white truncate">Jogos — {r.nome}</h3>
          <div className="flex items-center gap-2 shrink-0">
            {!r.atual && atualId !== null && onIrAtual && (
              <button onClick={onIrAtual} className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline">Ir para a atual</button>
            )}
            {selo}
          </div>
        </div>
        <div className={`space-y-1 transition-opacity ${carregando ? 'opacity-50' : ''}`}>
          {jogos.length ? jogos.map((j, i) => <JogoLinha key={`${j.casa}-${j.fora}-${i}`} jogo={j} mostrarData />) : (
            <p className="text-sm text-gray-400 text-center py-8">Nenhum jogo cadastrado nesta rodada.</p>
          )}
        </div>
      </div>

      {/* Jogos atrasados */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-red-500" />
            <h3 className="font-bold text-gray-900 dark:text-white">Jogos atrasados</h3>
          </div>
          {atrasados.length > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
              <AlarmClock className="w-3 h-3" /> {atrasados.length}
            </span>
          )}
        </div>
        {atrasados.length === 0 ? (
          <div className="flex flex-col items-center py-6 text-center">
            <CheckCircle2 className="w-10 h-10 text-brand-300 mb-2" />
            <p className="text-sm text-gray-400">Nenhum jogo atrasado. Todas as rodadas anteriores têm resultado.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {atrasados.map((j, i) => (
              <div key={`${j.rodadaNome}-${j.casa}-${j.fora}-${i}`} className="rounded-xl border border-gray-100 dark:border-gray-800">
                <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase tracking-wide">{j.rodadaNome}</p>
                <JogoLinha jogo={j} />
              </div>
            ))}
          </div>
        )}
      </div>

      {rodape}
    </>
  );
}

export type VisaoJogos = 'jogos' | 'tabela' | 'grupos' | 'confrontos';

/** Alternância da aba Jogos (gestão e página pública): Jogos, mais Tabela ou Grupos e Confrontos conforme a competição. */
export function SeletorVisaoJogos({ visao, onMudar, rotuloTabela = 'Tabela agora', opcoes = ['jogos', 'tabela'] }: {
  visao: VisaoJogos; onMudar: (v: VisaoJogos) => void; rotuloTabela?: string; opcoes?: VisaoJogos[];
}) {
  const todas = {
    jogos: ['Jogos', ListOrdered], tabela: [rotuloTabela, Table2], grupos: ['Grupos', Users], confrontos: ['Confrontos', GitFork],
  } as const;
  return (
    <div role="tablist" aria-label="Visualização" className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit max-w-full overflow-x-auto scrollbar-thin">
      {opcoes.map(id => {
        const [label, Icon] = todas[id];
        return (
          <button key={id} role="tab" aria-selected={visao === id} onClick={() => onMudar(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${visao === id ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            <Icon className="w-4 h-4" />{label}
          </button>
        );
      })}
    </div>
  );
}

/** Abas disponíveis conforme a competição: "Grupos" se há mais de um grupo, "Confrontos" se há mata-mata. */
export function opcoesDaCompeticao(dados: TabelaApi | null): VisaoJogos[] {
  if (!dados) return ['jogos', 'tabela'];
  const chave = fasesDaChave(dados).fases.length > 0;
  const opcoes: VisaoJogos[] = ['jogos'];
  if (dados.grupos.length > 1) opcoes.push('grupos');
  else if (dados.grupos.length === 1 || !chave) opcoes.push('tabela');
  if (chave) opcoes.push('confrontos');
  return opcoes;
}
