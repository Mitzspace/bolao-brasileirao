import { useState } from 'react';
import { Check, ChevronDown, Trophy } from 'lucide-react';
import { useApp } from '@/context/AppContext';

/** Troca entre os campeonatos do mesmo bolão (aparece quando há mais de um). */
export function SeletorCampeonato() {
  const { dados, bolao, view } = useApp();
  const [aberto, setAberto] = useState(false);
  if (!bolao) return null;
  const doGrupo = dados.boloes.filter(b => b.grupoId === bolao.grupoId);
  if (doGrupo.length < 2) return null;

  return (
    <div className="relative">
      <button onClick={() => setAberto(v => !v)} aria-haspopup="listbox" aria-expanded={aberto} aria-label={`Campeonato: ${bolao.campeonato}`}
        className="flex items-center gap-1.5 max-w-[11rem] sm:max-w-[16rem] px-3 py-2 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-semibold hover:bg-brand-100 dark:hover:bg-brand-900/50 transition-colors">
        <Trophy className="w-4 h-4 shrink-0" />
        <span className="truncate hidden sm:inline">{bolao.campeonato}</span>
        <ChevronDown className={`w-4 h-4 shrink-0 transition-transform ${aberto ? 'rotate-180' : ''}`} />
      </button>
      {aberto && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setAberto(false)} />
          <div role="listbox" className="absolute right-0 top-11 z-40 w-64 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 py-1.5 animate-scale-in">
            <p className="px-3 py-1.5 text-[11px] font-semibold uppercase text-gray-400">Campeonatos do bolão</p>
            {doGrupo.map(b => (
              <form key={b.id} action={dados.links.selecionar} method="POST">
                <input type="hidden" name="csrf_token" value={dados.csrfToken} />
                <input type="hidden" name="bolao_id" value={b.id} />
                <input type="hidden" name="view" value={view} />
                <button role="option" aria-selected={b.id === bolao.id}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <span className="flex-1 truncate">{b.campeonato} {b.ano ?? ''}</span>
                  {b.id === bolao.id && <Check className="w-4 h-4 text-brand-600" />}
                </button>
              </form>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
