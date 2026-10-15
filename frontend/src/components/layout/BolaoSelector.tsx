import { useApp } from '@/context/AppContext';

export function BolaoSelector() {
  const { dados, view } = useApp();
  if (!dados.boloes.length) return null;
  return <form action={dados.links.selecionar} method="POST" className="space-y-2">
    <input type="hidden" name="csrf_token" value={dados.csrfToken} />
    <input type="hidden" name="view" value={view} />
    <label htmlFor="bolao-atual" className="block text-xs font-medium text-gray-500 dark:text-gray-400">Bolão selecionado</label>
    <div className="flex flex-col sm:flex-row gap-2">
      <select id="bolao-atual" name="bolao_id" defaultValue={dados.bolaoAtualId ?? ''} required className="min-w-0 flex-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm">
        <option value="" disabled>Selecione um bolão</option>
        {dados.boloes.map(b => <option key={b.id} value={b.id}>{b.nome} · {b.campeonato} {b.ano ?? ''}</option>)}
      </select>
      <button className="rounded-xl bg-brand-600 hover:bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white">Selecionar</button>
    </div>
  </form>;
}
