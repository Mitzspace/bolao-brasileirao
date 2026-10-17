import { useState } from 'react';
import { ArrowRight, Check, Info, ListOrdered, Plus, Trophy } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { DetalheBolao, statusBolao } from '@/components/boloes/DetalheBolao';
import { NovoBolao } from '@/components/boloes/NovoBolao';
import { useRecurso } from '@/lib/useRecurso';
import type { BoloesApi, StatusBolao, View } from '@/types';

const NOMES_ABAS: Partial<Record<View, string>> = {
  dashboard: 'Dashboard', jogos: 'Jogos', palpites: 'Lançar palpites', rodadas: 'Rodadas',
  participantes: 'Participantes', configuracoes: 'Configurações', campeonatos: 'Configurações',
};

type Filtro = 'todos' | StatusBolao;
const FILTROS: { id: Filtro; rotulo: string }[] = [
  { id: 'todos', rotulo: 'Todos' }, { id: 'ativo', rotulo: 'Em andamento' },
  { id: 'finalizado', rotulo: 'Finalizados' }, { id: 'desistido', rotulo: 'Desistidos' },
];

/**
 * Bolões do responsável (cards do Bolt), classificação completa e criação de bolão.
 * destino: aba que a pessoa tentou abrir sem bolão selecionado (abre depois de escolher).
 */
export function BoloesScreen({ destino }: { destino?: View } = {}) {
  const { dados, parametros } = useApp();
  const [detalheId, setDetalheId] = useState<number | null>(parametros.bolaoId || null);
  const [novo, setNovo] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>('ativo');
  const { dados: resumo } = useRecurso<BoloesApi>('/boloes');

  if (detalheId && dados.boloes.some(b => b.id === detalheId)) {
    return <DetalheBolao key={detalheId} bolaoId={detalheId} onTrocar={setDetalheId} onVoltar={() => setDetalheId(null)} />;
  }

  const info = new Map(resumo?.boloes.map(b => [b.id, b]) ?? []);
  // Campeonatos do mesmo bolão aparecem juntos, no mesmo card.
  const todosGrupos = Object.values(dados.boloes.reduce<Record<number, typeof dados.boloes>>((acc, b) => {
    (acc[b.grupoId] ??= []).push(b);
    return acc;
  }, {}));
  // A situação é a mesma em todos os campeonatos do bolão; em andamento aparece primeiro (ordem estável).
  const situacao = (grupo: typeof dados.boloes) => grupo[0].status;
  const contagem: Record<Filtro, number> = {
    todos: todosGrupos.length,
    ativo: todosGrupos.filter(g => situacao(g) === 'ativo').length,
    finalizado: todosGrupos.filter(g => situacao(g) === 'finalizado').length,
    desistido: todosGrupos.filter(g => situacao(g) === 'desistido').length,
  };
  const grupos = [...todosGrupos]
    .filter(g => filtro === 'todos' || situacao(g) === filtro)
    .sort((a, b) => Number(situacao(b) === 'ativo') - Number(situacao(a) === 'ativo'));

  return (
    <div>
      <Header
        title="Bolões"
        subtitle={`${todosGrupos.length} ${todosGrupos.length === 1 ? 'bolão' : 'bolões'} sob sua gestão`}
        actions={
          <button onClick={() => setNovo(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold transition-colors">
            <Plus className="w-4 h-4" /><span className="hidden sm:inline">Novo bolão</span>
          </button>
        }
      />
      <div className="p-4 md:p-8 pb-28 md:pb-8">
        {!dados.bolaoAtualId && dados.boloes.length > 0 && (
          <div role="status" className="mb-5 flex items-start gap-3 rounded-2xl border border-gold-200 dark:border-gold-800/50 bg-gold-50 dark:bg-gold-900/20 p-4 text-sm text-gold-800 dark:text-gold-200 animate-fade-in">
            <Info className="w-5 h-5 shrink-0 mt-0.5" />
            <p>
              <strong className="font-semibold">Escolha qual bolão você quer gerenciar.</strong>{' '}
              {destino && NOMES_ABAS[destino]
                ? <>Depois de tocar em <em>Gerenciar</em>, a aba <strong>{NOMES_ABAS[destino]}</strong> abre automaticamente.</>
                : <>As abas Dashboard, Jogos, Palpites, Rodadas, Participantes e Configurações ficam disponíveis depois de escolher.</>}
            </p>
          </div>
        )}
        {!dados.boloes.length ? (
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
            <EmptyState icon={<Trophy className="w-10 h-10" />} title="Nenhum bolão disponível" description="Crie seu primeiro bolão para começar a organizar os palpites"
              action={<button onClick={() => setNovo(true)} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 transition-colors"><Plus className="w-4 h-4" />Criar bolão</button>} />
          </div>
        ) : (
          <>
          <div role="tablist" aria-label="Filtrar por situação" className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 overflow-x-auto no-scrollbar w-fit max-w-full mb-5">
            {FILTROS.map(f => (
              <button key={f.id} role="tab" aria-selected={filtro === f.id} onClick={() => setFiltro(f.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${filtro === f.id ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500'}`}>
                {f.rotulo}
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${filtro === f.id ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' : 'bg-gray-200 dark:bg-gray-700 text-gray-500'}`}>{contagem[f.id]}</span>
              </button>
            ))}
          </div>
          {grupos.length === 0 && (
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
              <EmptyState icon={<Trophy className="w-10 h-10" />} title="Nenhum bolão nesta situação"
                description={filtro === 'ativo' ? 'Nenhum bolão em andamento. Veja todos ou crie um novo bolão.' : 'Mude o filtro para ver os outros bolões.'}
                action={<button onClick={() => setFiltro('todos')} className="px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 transition-colors">Ver todos</button>} />
            </div>
          )}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {grupos.map(grupo => {
              const principal = grupo[0];
              const atual = grupo.find(b => b.id === dados.bolaoAtualId);
              const foco = info.get((atual ?? principal).id);
              const status = statusBolao(situacao(grupo));
              return (
                <article key={principal.grupoId} onClick={() => setDetalheId((atual ?? principal).id)}
                  className={`group bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border flex flex-col cursor-pointer animate-slide-up transition-all hover:shadow-md hover:border-brand-200 dark:hover:border-brand-800 ${atual ? 'border-brand-300 dark:border-brand-700' : 'border-gray-100 dark:border-gray-800'}`}>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shrink-0"><Trophy className="w-6 h-6 text-white" /></div>
                    <div className="flex flex-wrap justify-end gap-1.5">
                      {atual && <Badge color="green" icon={<Check className="w-3 h-3" />}>Selecionado</Badge>}
                      <Badge color={status.color}>{status.label}</Badge>
                    </div>
                  </div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg break-words">{principal.nome}</h3>
                  {(() => {
                    const legenda = grupo.length === 1 ? `${principal.campeonato} ${principal.ano ?? ''}`.trim() : `${grupo.length} campeonatos`;
                    // Sem repetir quando o nome do bolão já é o do campeonato.
                    return <p className="text-sm text-gray-400 mb-4 min-h-[1.25rem]">{legenda !== principal.nome ? legenda : ''}</p>;
                  })()}

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800">
                      <p className="text-xs text-gray-400">Particip.</p>
                      <p className="text-sm font-bold text-gray-700 dark:text-gray-300">{foco?.participantesAtivos ?? '—'}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800 min-w-0">
                      <p className="text-xs text-gray-400">Rodada</p>
                      <p className="text-sm font-bold text-gray-700 dark:text-gray-300 truncate" title={foco?.rodada ?? undefined}>{foco?.rodada?.replace(/\s*Rodada/i, '') ?? '—'}</p>
                    </div>
                    <div title="Participantes com algum jogo em branco na rodada atual (mesma regra do Dashboard)"
                      className={`p-2 rounded-lg ${foco?.palpitesFaltantes ? 'bg-gold-50 dark:bg-gold-900/20' : 'bg-gray-50 dark:bg-gray-800'}`}>
                      <p className="text-xs text-gray-400">Faltam</p>
                      <p className={`text-sm font-bold ${foco?.palpitesFaltantes ? 'text-gold-600 dark:text-gold-400' : 'text-gray-700 dark:text-gray-300'}`}>{foco ? foco.palpitesFaltantes : '—'}</p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2" onClick={e => e.stopPropagation()}>
                    {grupo.map(b => (
                      <form key={b.id} action={dados.links.selecionar} method="POST">
                        <input type="hidden" name="csrf_token" value={dados.csrfToken} />
                        <input type="hidden" name="bolao_id" value={b.id} />
                        <input type="hidden" name="view" value={destino && NOMES_ABAS[destino] ? destino : 'dashboard'} />
                        <button className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors ${b.id === dados.bolaoAtualId ? 'bg-brand-600 hover:bg-brand-700 text-white' : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:text-brand-700'}`}>
                          <span className="truncate">{b.id === dados.bolaoAtualId ? 'Gerenciando' : 'Gerenciar'}{grupo.length > 1 ? ` · ${b.campeonato} ${b.ano ?? ''}` : ' este bolão'}</span>
                          <ArrowRight className="w-4 h-4 shrink-0" />
                        </button>
                      </form>
                    ))}
                    <button onClick={() => setDetalheId((atual ?? principal).id)} className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">
                      <ListOrdered className="w-4 h-4" /> Ver classificação
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
          </>
        )}
      </div>
      <NovoBolao aberto={novo} onClose={() => setNovo(false)} />
    </div>
  );
}
