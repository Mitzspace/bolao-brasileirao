import { useEffect, useState } from 'react';
import { CalendarClock, LayoutDashboard, PencilLine, Trophy, Users } from 'lucide-react';
import { Inicio } from './abas/Inicio';
import { Jogos } from './abas/Jogos';
import { Palpites } from './abas/Palpites';
import { Participantes } from './abas/Participantes';
import type { DadosPagina } from './tipos';

const ABAS = [
  { id: 'inicio', label: 'Início', longo: 'Dashboard e tabela', icon: LayoutDashboard },
  { id: 'jogos', label: 'Jogos', longo: 'Jogos', icon: CalendarClock },
  { id: 'palpites', label: 'Palpites', longo: 'Palpites', icon: PencilLine },
  { id: 'participantes', label: 'Participantes', longo: 'Participantes', icon: Users },
] as const;
type Aba = typeof ABAS[number]['id'];

function abaDoEndereco(): Aba {
  const valor = window.location.hash.slice(1);
  return (ABAS.find(a => a.id === valor)?.id) ?? 'inicio';
}

/** Página pública do bolão: somente leitura, 4 abas, pensada para o celular. */
export function AppPublico({ dados }: { dados: DadosPagina }) {
  const [aba, setAba] = useState<Aba>(abaDoEndereco);
  useEffect(() => {
    const mudar = () => setAba(abaDoEndereco());
    window.addEventListener('hashchange', mudar);
    return () => window.removeEventListener('hashchange', mudar);
  }, []);
  const ir = (nova: Aba) => {
    window.location.hash = nova;
    setAba(nova);
    window.scrollTo({ top: 0 });
  };
  const b = dados.bolao;

  return (
    <div className="min-h-screen min-h-dvh pb-24 md:pb-10">
      <header className="sticky top-0 z-30 bg-white/85 dark:bg-gray-900/85 backdrop-blur-md border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shrink-0">
            <Trophy className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-gray-900 dark:text-white leading-tight truncate">{b.nome}</h1>
            <p className="text-xs text-gray-400 truncate">{b.campeonato} {b.ano ?? ''} · consulta</p>
          </div>
        </div>
        <nav aria-label="Seções" className="hidden md:block max-w-5xl mx-auto px-6">
          <div className="flex gap-1 -mb-px">
            {ABAS.map(a => {
              const Icon = a.icon;
              const ativa = aba === a.id;
              return (
                <button key={a.id} onClick={() => ir(a.id)} aria-current={ativa ? 'page' : undefined}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${ativa ? 'border-brand-600 text-brand-700 dark:text-brand-300' : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}`}>
                  <Icon className="w-4 h-4" />{a.longo}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-6 py-5 animate-fade-in" key={aba}>
        {aba === 'inicio' && <Inicio />}
        {aba === 'jogos' && <Jogos />}
        {aba === 'palpites' && <Palpites />}
        {aba === 'participantes' && <Participantes />}
      </main>

      <nav aria-label="Seções" className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-1 py-1.5 flex items-center justify-around safe-area-bottom">
        {ABAS.map(a => {
          const Icon = a.icon;
          const ativa = aba === a.id;
          return (
            <button key={a.id} onClick={() => ir(a.id)} aria-current={ativa ? 'page' : undefined}
              className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-1.5 rounded-lg transition-colors ${ativa ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'}`}>
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{a.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
