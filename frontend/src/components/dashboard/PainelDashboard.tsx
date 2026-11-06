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
  /** Conteúdo extra logo abaixo dos indicadores (a gestão mostra quem tem palpite faltando). */
  extra?: ReactNode;
}

/** Dashboard do Bolt, compartilhado pela gestão e pela página pública (sem contexto do admin). */
export function PainelDashboard({ bolao, saudacao, rodadaNome, acao, indicadores, top5, notaVariacao,
  onVerClassificacao, onAbrirLider, jogos, extra }: Props) {
  const aguardando = jogos.filter(j => j.status === 'aguardando').length;
  return (
    <>
      {/* Boas-vindas */}
      <div className="bg-gradient-to-r from-brand-600 via-brand-700 to-brand-800 rounded-3xl p-6 md:p-8 text-white shadow-lg shadow-brand-900/20 relative overflow-hidden animate-fade-in">
        <div aria-hidden="true" className="absolute inset-y-0 right-0 w-1/2 hidden sm:block linhas-campo opacity-80 [mask-image:linear-gradient(90deg,transparent,black_40%)]" />
        <div aria-hidden="true" className="absolute -top-16 -right-10 w-56 h-56 bg-white/10 rounded-full blur-2xl" />
        <div aria-hidden="true" className="absolute -bottom-20 left-1/3 w-56 h-56 bg-gold-400/20 rounded-full blur-3xl" />
        <div className="relative">
          <p className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold text-white/90 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-300" />{saudacao}
          </p>
          <h2 className="text-2xl md:text-3xl font-extrabold mt-3 break-words">{bolao.nome}</h2>
          <p className="text-white/80 text-sm mt-1.5">
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
            <div key={stat.label} className="relative overflow-hidden bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 animate-slide-up min-w-0 cartao-elevavel">
              <div aria-hidden="true" className={`absolute -top-8 -right-8 w-24 h-24 rounded-full bg-gradient-to-br ${colorMap[stat.color]} opacity-[0.08]`} />
              <div className={`relative w-11 h-11 rounded-xl bg-gradient-to-br ${colorMap[stat.color]} flex items-center justify-center mb-3 shadow-md`}>
                <Icon className="w-5 h-5" />
              </div>
              <p className="relative text-2xl md:text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white truncate">{stat.value}</p>
              <p className="relative text-xs font-medium text-gray-500 dark:text-gray-400 mt-0.5">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {extra}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top 5 */}
        <div className="min-w-0 lg:col-span-1 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center shrink-0"><TrendingUp className="w-[18px] h-[18px] text-brand-600 dark:text-brand-400" /></span>
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
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${i < 3 ? 'text-white shadow-sm ring-2 ring-white dark:ring-gray-900' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
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
                    className={`w-full flex items-center gap-3 py-1.5 px-2 -mx-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${i === 0 ? 'bg-gold-50/70 dark:bg-gold-900/10' : ''}`}>
                    {conteudo}
                  </button>
                ) : <div key={p.chave} className={`flex items-center gap-3 py-1.5 px-2 -mx-2 rounded-xl ${i === 0 ? 'bg-gold-50/70 dark:bg-gold-900/10' : ''}`}>{conteudo}</div>;
              })}
            </div>
          )}
          {onVerClassificacao && top5 !== null && (
            <button onClick={onVerClassificacao} className="block w-full mt-4 py-2 rounded-xl text-center text-sm text-brand-700 dark:text-brand-300 font-semibold bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/40 transition-colors">
              Ver classificação completa
            </button>
          )}
        </div>

        {/* Jogos da rodada */}
        <div className="min-w-0 lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center shrink-0"><Calendar className="w-[18px] h-[18px] text-brand-600 dark:text-brand-400" /></span>
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
