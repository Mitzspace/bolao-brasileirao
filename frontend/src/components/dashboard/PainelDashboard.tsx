import type { ReactNode } from 'react';
import { Calendar, Hourglass, Medal, TrendingUp, type LucideIcon } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Variacao } from '@/components/ui/Variacao';
import { JogoLinha } from '@/components/jogos/JogoLinha';
import type { JogoBase } from '@/types';

const colorMap = {
  brand: 'from-brand-500 to-brand-700 text-white',
  gold: 'from-gold-400 to-gold-600 text-white',
  blue: 'from-blue-500 to-blue-700 text-white',
  red: 'from-red-500 to-red-600 text-white',
  purple: 'from-purple-500 to-purple-700 text-white',
};
const medalColors = ['#fbbf24', '#cbd5e1', '#d97706'];

export interface IndicadorDashboard { label: string; value: ReactNode; icon: LucideIcon; color: keyof typeof colorMap }
export interface LiderDashboard {
  chave: string | number; avatarId: number; nome: string; posicao: number | null;
  cravadas: number; pontos: number; variacao: number | null;
}

interface Props {
  bolao: { nome: string; campeonato: string; ano: number | null };
  saudacao: string;
  rodadaNome?: string | null;
  /** Botão de ação no destaque (a gestão usa para "Lançar palpites"). */
  acao?: ReactNode;
  indicadores: readonly IndicadorDashboard[];
  /** null: classificação ainda não divulgada (página pública). */
  top5: LiderDashboard[] | null;
  /** Texto explicando a referência da variação de posição. */
  notaVariacao?: string | null;
  onVerClassificacao?: () => void;
  onAbrirLider?: (lider: LiderDashboard) => void;
  jogos: JogoBase[];
}

/** Dashboard do Bolt, compartilhado pela gestão e pela página pública (sem contexto do admin). */
export function PainelDashboard({ bolao, saudacao, rodadaNome, acao, indicadores, top5, notaVariacao,
  onVerClassificacao, onAbrirLider, jogos }: Props) {
  const aguardando = jogos.filter(j => j.status === 'aguardando').length;
  return (
    <>
      {/* Boas-vindas */}
      <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden animate-fade-in">
        <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4" />
        <div className="relative">
          <p className="text-white/80 text-sm">{saudacao}</p>
          <h2 className="text-2xl font-bold mt-1 break-words">{bolao.nome}</h2>
          <p className="text-white/80 text-sm mt-2">
            {bolao.campeonato} {bolao.ano ?? ''}{rodadaNome ? ` — ${rodadaNome}` : ''}
          </p>
          {acao}
        </div>
      </div>

      {/* Indicadores */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {indicadores.map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 animate-slide-up min-w-0">
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${colorMap[stat.color]} flex items-center justify-center mb-3`}>
                <Icon className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white truncate">{stat.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{stat.label}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top 5 */}
        <div className="min-w-0 lg:col-span-1 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-5 h-5 text-brand-600" />
            <h3 className="font-bold text-gray-900 dark:text-white truncate">Top 5 — {bolao.nome}</h3>
          </div>
          {notaVariacao && top5 && <p className="text-[11px] text-gray-400 mb-4">{notaVariacao}</p>}
          {top5 === null ? (
            <div className="flex flex-col items-center text-center py-6">
              <Hourglass className="w-9 h-9 text-gold-500 mb-2" />
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Classificação em breve</p>
              <p className="text-xs text-gray-400 mt-1">Os organizadores ainda não divulgaram a tabela.</p>
            </div>
          ) : top5.length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">Nenhum participante cadastrado.</p>
          ) : (
            <div className="space-y-1 mt-3">
              {top5.map((p, i) => {
                const conteudo = (
                  <>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${i < 3 ? 'text-white' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
                      style={i < 3 ? { backgroundColor: medalColors[i] } : {}}>
                      {p.posicao ?? i + 1}
                    </div>
                    <Avatar nome={p.nome} id={p.avatarId} />
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.nome}</p>
                      <p className="text-xs text-gray-400">{p.cravadas} {p.cravadas === 1 ? 'cravada' : 'cravadas'}</p>
                    </div>
                    <Variacao valor={p.variacao} />
                    <span className="text-sm font-bold text-brand-600 dark:text-brand-400 w-10 text-right">{p.pontos}</span>
                  </>
                );
                return onAbrirLider ? (
                  <button key={p.chave} onClick={() => onAbrirLider(p)}
                    className="w-full flex items-center gap-3 py-1.5 px-1 -mx-1 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    {conteudo}
                  </button>
                ) : <div key={p.chave} className="flex items-center gap-3 py-1.5">{conteudo}</div>;
              })}
            </div>
          )}
          {onVerClassificacao && top5 !== null && (
            <button onClick={onVerClassificacao} className="block w-full mt-4 text-center text-sm text-brand-600 dark:text-brand-400 font-medium hover:underline">
              Ver classificação completa
            </button>
          )}
        </div>

        {/* Jogos da rodada */}
        <div className="min-w-0 lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2 min-w-0">
              <Calendar className="w-5 h-5 text-brand-600 shrink-0" />
              <h3 className="font-bold text-gray-900 dark:text-white truncate">Jogos{rodadaNome ? ` — ${rodadaNome}` : ''}</h3>
            </div>
            {aguardando > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300 shrink-0">
                <span className="w-2 h-2 rounded-full bg-gold-500 animate-pulse" />
                {aguardando} aguardando resultado
              </span>
            )}
          </div>
          <div className="space-y-1">
            {jogos.length > 0 ? jogos.map((jogo, i) => <JogoLinha key={`${jogo.casa}-${jogo.fora}-${i}`} jogo={jogo} />) : (
              <div className="flex flex-col items-center py-8 text-center">
                <Medal className="w-10 h-10 text-gray-300 mb-2" />
                <p className="text-sm text-gray-400">Nenhum jogo cadastrado para a rodada.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
