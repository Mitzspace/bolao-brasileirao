import { Users, Calendar, Target, AlertCircle, ArrowRight, CheckCircle2, ChevronRight } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { PainelDashboard, type IndicadorDashboard } from '@/components/dashboard/PainelDashboard';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import type { DashboardApi } from '@/types';

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
  const indicadores: IndicadorDashboard[] = [
    { label: 'Participantes ativos', value: dados.participantesAtivos, icon: Users, color: 'gold' },
    { label: 'Rodada atual', value: rodada?.numero ? `${rodada.numero}/${rodada.total}` : '—', icon: Calendar, color: 'blue' },
    // Faltante = participante com algum jogo em branco na rodada (mesmo que tenha mandado parte).
    { label: 'Participantes com palpite faltando', value: dados.palpitesFaltantes, icon: AlertCircle, color: 'red' },
    { label: 'Jogos encerrados na rodada', value: `${dados.jogosEncerrados}/${dados.jogos.length}`, icon: CheckCircle2, color: 'brand' },
  ];

  return (
    <PainelDashboard
      bolao={dados.bolao}
      saudacao="Bem-vindo de volta!"
      rodadaNome={rodada?.nome}
      acao={(
        <button onClick={() => setView('palpites')} className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white text-brand-700 rounded-xl font-semibold text-sm hover:bg-brand-50 transition-colors">
          <Target className="w-4 h-4" />
          Lançar palpites da rodada atual
          <ArrowRight className="w-4 h-4" />
        </button>
      )}
      indicadores={indicadores}
      top5={dados.top5.map(p => ({ chave: p.participacaoId, avatarId: p.participacaoId, nome: p.nome, posicao: p.posicao,
        cravadas: p.cravadas, pontos: p.pontos, variacao: p.variacao }))}
      notaVariacao={dados.variacaoReferencia ? `Variação em relação à classificação antes da ${dados.variacaoReferencia}` : null}
      onVerClassificacao={() => setView('boloes', { bolaoId: bolaoAtualId ?? 0 })}
      jogos={dados.jogos}
      extra={rodada && dados.pendentes.length > 0 ? (
        <section className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <h3 className="font-bold text-gray-900 dark:text-white">Palpites faltantes — {rodada.nome}</h3>
            <span className="text-xs text-gray-400">{dados.pendentes.length} {dados.pendentes.length === 1 ? 'participante' : 'participantes'} · {dados.jogosFaltantes} {dados.jogosFaltantes === 1 ? 'jogo em branco' : 'jogos em branco'}</span>
          </div>
          <ul className="flex flex-wrap gap-2">
            {dados.pendentes.map(p => (
              <li key={p.id}>
                <button onClick={() => setView('palpites', { rodadaId: rodada.id, participacaoId: p.id })}
                  title={`Abrir os palpites de ${p.nome}`}
                  className="inline-flex items-center gap-1.5 rounded-full border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 pl-3 pr-2 py-1.5 text-xs font-medium text-red-700 dark:text-red-300 hover:border-red-300 dark:hover:border-red-800">
                  <span className="max-w-[10rem] truncate">{p.nome}</span>
                  <span className="text-red-500/80">{p.faltantes === p.total ? 'nenhum palpite' : `faltam ${p.faltantes} de ${p.total}`}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : undefined}
    />
  );
}
