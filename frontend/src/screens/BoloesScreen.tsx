import { useState } from 'react';
import { ArrowRight, Check, ListOrdered, Plus, Trophy } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { DetalheBolao, statusBolao } from '@/components/boloes/DetalheBolao';
import { NovoBolao } from '@/components/boloes/NovoBolao';
import { useRecurso } from '@/lib/useRecurso';
import type { BoloesApi } from '@/types';

/** Bolões do responsável (cards do Bolt), classificação completa e criação de bolão. */
export function BoloesScreen() {
  const { dados, parametros } = useApp();
  const [detalheId, setDetalheId] = useState<number | null>(parametros.bolaoId || null);
  const [novo, setNovo] = useState(false);
  const { dados: resumo } = useRecurso<BoloesApi>('/boloes');

  if (detalheId && dados.boloes.some(b => b.id === detalheId)) {
    return <DetalheBolao key={detalheId} bolaoId={detalheId} onTrocar={setDetalheId} onVoltar={() => setDetalheId(null)} />;
  }

  const info = new Map(resumo?.boloes.map(b => [b.id, b]) ?? []);
  // Campeonatos do mesmo bolão aparecem juntos, no mesmo card.
  const grupos = Object.values(dados.boloes.reduce<Record<number, typeof dados.boloes>>((acc, b) => {
    (acc[b.grupoId] ??= []).push(b);
    return acc;
  }, {}));

  return (
    <div>
      <Header
        title="Bolões"
        subtitle={`${grupos.length} ${grupos.length === 1 ? 'bolão' : 'bolões'} sob sua gestão`}
        actions={
          <button onClick={() => setNovo(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold transition-colors">
            <Plus className="w-4 h-4" /><span className="hidden sm:inline">Novo bolão</span>
          </button>
        }
      />
      <div className="p-4 md:p-8 pb-28 md:pb-8">
        {!dados.boloes.length ? (
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
            <EmptyState icon={<Trophy className="w-10 h-10" />} title="Nenhum bolão disponível" description="Crie seu primeiro bolão para começar a organizar os palpites"
              action={<button onClick={() => setNovo(true)} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 transition-colors"><Plus className="w-4 h-4" />Criar bolão</button>} />
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {grupos.map(grupo => {
              const principal = grupo[0];
              const atual = grupo.find(b => b.id === dados.bolaoAtualId);
              const foco = info.get((atual ?? principal).id);
              const status = foco ? statusBolao(foco.status) : null;
              return (
                <article key={principal.grupoId} onClick={() => setDetalheId((atual ?? principal).id)}
                  className={`group bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border flex flex-col cursor-pointer animate-slide-up transition-all hover:shadow-md hover:border-brand-200 dark:hover:border-brand-800 ${atual ? 'border-brand-300 dark:border-brand-700' : 'border-gray-100 dark:border-gray-800'}`}>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shrink-0"><Trophy className="w-6 h-6 text-white" /></div>
                    <div className="flex flex-wrap justify-end gap-1.5">
                      {atual && <Badge color="green" icon={<Check className="w-3 h-3" />}>Selecionado</Badge>}
                      {status && foco?.status !== 'ativo' && <Badge color={status.color}>{status.label}</Badge>}
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
                    <div className={`p-2 rounded-lg ${foco?.palpitesFaltantes ? 'bg-gold-50 dark:bg-gold-900/20' : 'bg-gray-50 dark:bg-gray-800'}`}>
                      <p className="text-xs text-gray-400">Faltam</p>
                      <p className={`text-sm font-bold ${foco?.palpitesFaltantes ? 'text-gold-600 dark:text-gold-400' : 'text-gray-700 dark:text-gray-300'}`}>{foco ? foco.palpitesFaltantes : '—'}</p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2" onClick={e => e.stopPropagation()}>
                    {grupo.map(b => (
                      <form key={b.id} action={dados.links.selecionar} method="POST">
                        <input type="hidden" name="csrf_token" value={dados.csrfToken} />
                        <input type="hidden" name="bolao_id" value={b.id} />
                        <input type="hidden" name="view" value="dashboard" />
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
        )}
      </div>
      <NovoBolao aberto={novo} onClose={() => setNovo(false)} />
    </div>
  );
}
