import { Users, Calendar, Target, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
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
    { label: 'Palpites faltantes na rodada', value: dados.palpitesFaltantes, icon: AlertCircle, color: 'red' },
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
    />
  );
}
