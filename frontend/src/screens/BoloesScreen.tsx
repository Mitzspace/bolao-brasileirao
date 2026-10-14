import { Trophy, ArrowRight, Plus } from 'lucide-react';
import { useApp } from '@/context/AppContext';

export function BoloesScreen() {
  const { dados } = useApp();
  return <section className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-gray-500 dark:text-gray-400">Selecione o bolão que você quer gerenciar.</p>
      <a href={dados.links.criarBolao} className="button-primary"><Plus className="w-4 h-4" /> Criar bolão</a>
    </div>
    {!dados.boloes.length && <div className="panel p-6"><h2 className="font-bold">Nenhum bolão disponível</h2><p className="mt-2 text-sm text-gray-500">Sua conta ainda não tem um bolão disponível para gestão.</p></div>}
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {dados.boloes.map(b => <article key={b.id} className="panel p-5 flex flex-col animate-slide-up">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="w-11 h-11 bg-brand-50 dark:bg-brand-900/30 rounded-xl flex items-center justify-center text-brand-600"><Trophy className="w-6 h-6" /></div>
          {b.id === dados.bolaoAtualId && <span className="text-xs rounded-full px-2 py-1 bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300">Selecionado</span>}
        </div>
        <h2 className="text-lg font-bold break-words">{b.nome}</h2>
        <p className="text-sm text-gray-500 mt-1">{b.campeonato} {b.ano ?? ''}</p>
        <p className="text-xs text-gray-400 mt-1">{b.chave}</p>
        <form action={dados.links.selecionar} method="POST" className="mt-5">
          <input type="hidden" name="csrf_token" value={dados.csrfToken} />
          <input type="hidden" name="bolao_id" value={b.id} />
          <input type="hidden" name="view" value="dashboard" />
          <button className="button-primary w-full">Entrar no bolão <ArrowRight className="w-4 h-4" /></button>
        </form>
      </article>)}
    </div>
  </section>;
}
