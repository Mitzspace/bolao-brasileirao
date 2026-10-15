import { Users, Calendar, Target, TrendingUp, AlertCircle, ArrowRight, CheckCircle2, Medal } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { Avatar } from '@/components/ui/Avatar';
import { Variacao } from '@/components/ui/Variacao';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { JogoLinha } from '@/components/jogos/JogoLinha';
import { useRecurso } from '@/lib/useRecurso';
import type { DashboardApi } from '@/types';

const colorMap = {
  brand: 'from-brand-500 to-brand-700 text-white',
  gold: 'from-gold-400 to-gold-600 text-white',
  blue: 'from-blue-500 to-blue-700 text-white',
  red: 'from-red-500 to-red-600 text-white',
};
const medalColors = ['#fbbf24', '#cbd5e1', '#d97706'];

export function Dashboard() {
  const { dados, carregando, erro, recarregar } = useRecurso<DashboardApi>('/dashboard');

  return (
    <div>
      <Header title="Dashboard" subtitle="Visão geral do bolão" />
      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={4} />}
        {dados && <Conteudo dados={dados} />}
      </div>
    </div>
  );
}

function Conteudo({ dados }: { dados: DashboardApi }) {
  const { setView, dados: { bolaoAtualId } } = useApp();
  const { rodada } = dados;
  const stats = [
    { label: 'Participantes ativos', value: dados.participantesAtivos, icon: Users, color: 'gold' },
    { label: 'Rodada atual', value: rodada?.numero ? `${rodada.numero}/${rodada.total}` : '—', icon: Calendar, color: 'blue' },
    { label: 'Palpites faltantes na rodada', value: dados.palpitesFaltantes, icon: AlertCircle, color: 'red' },
    { label: 'Jogos encerrados na rodada', value: `${dados.jogosEncerrados}/${dados.jogos.length}`, icon: CheckCircle2, color: 'brand' },
  ] as const;
  const aguardando = dados.jogos.filter(j => j.status === 'aguardando').length;

  return (
    <>
      {/* Boas-vindas */}
      <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden animate-fade-in">
        <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4" />
        <div className="relative">
          <p className="text-white/80 text-sm">Bem-vindo de volta!</p>
          <h2 className="text-2xl font-bold mt-1 break-words">{dados.bolao.nome}</h2>
          <p className="text-white/80 text-sm mt-2">
            {dados.bolao.campeonato} {dados.bolao.ano ?? ''}{rodada ? ` — ${rodada.nome}` : ''}
          </p>
          {(
            <button onClick={() => setView('palpites')} className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white text-brand-700 rounded-xl font-semibold text-sm hover:bg-brand-50 transition-colors">
              <Target className="w-4 h-4" />
              Lançar palpites da rodada atual
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Indicadores */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 animate-slide-up">
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${colorMap[stat.color]} flex items-center justify-center mb-3`}>
                <Icon className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
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
            <h3 className="font-bold text-gray-900 dark:text-white truncate">Top 5 — {dados.bolao.nome}</h3>
          </div>
          {dados.variacaoReferencia && (
            <p className="text-[11px] text-gray-400 mb-4">Variação em relação à classificação antes da {dados.variacaoReferencia}</p>
          )}
          {dados.top5.length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">Nenhum participante cadastrado.</p>
          ) : (
            <div className="space-y-3">
              {dados.top5.map((p, i) => (
                <div key={p.participacaoId} className="flex items-center gap-3">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${i < 3 ? 'text-white' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
                    style={i < 3 ? { backgroundColor: medalColors[i] } : {}}>
                    {p.posicao ?? i + 1}
                  </div>
                  <Avatar nome={p.nome} id={p.participacaoId} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.nome}</p>
                    <p className="text-xs text-gray-400">{p.cravadas} {p.cravadas === 1 ? 'cravada' : 'cravadas'}</p>
                  </div>
                  <Variacao valor={p.variacao} />
                  <span className="text-sm font-bold text-brand-600 dark:text-brand-400 w-10 text-right">{p.pontos}</span>
                </div>
              ))}
            </div>
          )}
          <button onClick={() => setView('boloes', { bolaoId: bolaoAtualId ?? 0 })} className="block w-full mt-4 text-center text-sm text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Ver classificação completa
          </button>
        </div>

        {/* Jogos da rodada */}
        <div className="min-w-0 lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2 min-w-0">
              <Calendar className="w-5 h-5 text-brand-600 shrink-0" />
              <h3 className="font-bold text-gray-900 dark:text-white truncate">Jogos{rodada ? ` — ${rodada.nome}` : ''}</h3>
            </div>
            {aguardando > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300 shrink-0">
                <span className="w-2 h-2 rounded-full bg-gold-500 animate-pulse" />
                {aguardando} aguardando resultado
              </span>
            )}
          </div>
          <div className="space-y-1">
            {dados.jogos.length > 0 ? dados.jogos.map(jogo => <JogoLinha key={jogo.id} jogo={jogo} />) : (
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
