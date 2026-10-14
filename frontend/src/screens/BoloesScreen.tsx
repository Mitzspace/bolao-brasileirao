import { Trophy, ArrowRight, Plus, Check } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { EmptyState } from '@/components/ui/EmptyState';

/** Escolha do bolão (versão da Etapa 0; a tela completa vem na Etapa 6). */
export function BoloesScreen() {
  const { dados } = useApp();
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
          <a href={dados.links.criarBolao} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors">
            <Plus className="w-4 h-4" /> <span className="hidden sm:inline">Novo bolão</span>
          </a>
        }
      />
      <div className="p-4 md:p-8 pb-28 md:pb-8">
        {!dados.boloes.length ? (
          <EmptyState icon={<Trophy className="w-10 h-10" />} title="Nenhum bolão disponível" description="Sua conta ainda não é responsável por nenhum bolão." />
        ) : (
          <>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Selecione o bolão e o campeonato que você quer gerenciar.</p>
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {grupos.map(grupo => {
                const principal = grupo[0];
                const atual = grupo.some(b => b.id === dados.bolaoAtualId);
                return (
                  <article key={principal.grupoId} className={`bg-white dark:bg-gray-900 rounded-2xl shadow-sm border p-5 flex flex-col animate-slide-up transition-all hover:shadow-md ${atual ? 'border-brand-300 dark:border-brand-700' : 'border-gray-100 dark:border-gray-800'}`}>
                    <div className="flex items-center justify-between gap-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center text-white shadow-md"><Trophy className="w-6 h-6" /></div>
                      {atual && <span className="inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2.5 py-0.5 bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300"><Check className="w-3 h-3" /> Selecionado</span>}
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white break-words">{principal.nome}</h2>
                    <p className="text-xs text-gray-400 mt-1">{principal.chave} · {grupo.length} {grupo.length === 1 ? 'campeonato' : 'campeonatos'}</p>
                    <div className="mt-4 space-y-2">
                      {grupo.map(b => (
                        <form key={b.id} action={dados.links.selecionar} method="POST">
                          <input type="hidden" name="csrf_token" value={dados.csrfToken} />
                          <input type="hidden" name="bolao_id" value={b.id} />
                          <input type="hidden" name="view" value="dashboard" />
                          <button className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors ${b.id === dados.bolaoAtualId ? 'bg-brand-600 hover:bg-brand-700 text-white' : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:text-brand-700'}`}>
                            <span className="truncate">{b.campeonato} {b.ano ?? ''}</span>
                            <ArrowRight className="w-4 h-4 shrink-0" />
                          </button>
                        </form>
                      ))}
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
