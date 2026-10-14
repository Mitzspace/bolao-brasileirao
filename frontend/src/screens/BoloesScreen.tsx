import { Trophy, ArrowRight, Plus, Check } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { EmptyState } from '@/components/ui/EmptyState';

/** Escolha do bolão (versão da Etapa 0; a tela completa vem na Etapa 6). */
export function BoloesScreen() {
  const { dados } = useApp();
  return (
    <div>
      <Header
        title="Bolões"
        subtitle={`${dados.boloes.length} ${dados.boloes.length === 1 ? 'bolão' : 'bolões'} sob sua gestão`}
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
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Selecione o bolão que você quer gerenciar.</p>
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {dados.boloes.map(b => {
                const atual = b.id === dados.bolaoAtualId;
                return (
                  <article key={b.id} className={`bg-white dark:bg-gray-900 rounded-2xl shadow-sm border p-5 flex flex-col animate-slide-up transition-all hover:shadow-md ${atual ? 'border-brand-300 dark:border-brand-700' : 'border-gray-100 dark:border-gray-800'}`}>
                    <div className="flex items-center justify-between gap-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center text-white shadow-md"><Trophy className="w-6 h-6" /></div>
                      {atual && <span className="inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2.5 py-0.5 bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300"><Check className="w-3 h-3" /> Selecionado</span>}
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white break-words">{b.nome}</h2>
                    <p className="text-sm text-gray-500 mt-1">{b.campeonato} {b.ano ?? ''}</p>
                    <p className="text-xs text-gray-400 mt-1">{b.chave}</p>
                    <form action={dados.links.selecionar} method="POST" className="mt-5">
                      <input type="hidden" name="csrf_token" value={dados.csrfToken} />
                      <input type="hidden" name="bolao_id" value={b.id} />
                      <input type="hidden" name="view" value="dashboard" />
                      <button className="button-primary w-full">{atual ? 'Abrir bolão' : 'Entrar no bolão'} <ArrowRight className="w-4 h-4" /></button>
                    </form>
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
