import { useEffect, useState } from 'react';
import { BarChart3, Calendar, CalendarClock, LayoutDashboard, ListOrdered, MoreHorizontal, PencilLine, Settings, Trophy, Users } from 'lucide-react';
import { useApp } from '@/context/AppContext';

const navItems = [
  { id: 'jogos', label: 'Jogos', icon: CalendarClock },
  { id: 'palpites', label: 'Palpites', icon: PencilLine },
  { id: 'tabela', label: 'Tabela', icon: ListOrdered },
  { id: 'estatisticas', label: 'Estatísticas', icon: BarChart3 },
  { id: 'boloes', label: 'Bolões', icon: Trophy },
] as const;

/** Não cabem todas as abas na largura do celular: as demais ficam no botão "Mais". */
const maisItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'rodadas', label: 'Rodadas', icon: Calendar },
  { id: 'participantes', label: 'Participantes', icon: Users },
  { id: 'configuracoes', label: 'Configurações', icon: Settings },
] as const;

export function BottomNav() {
  const { view, setView, bolao } = useApp();
  const [mais, setMais] = useState(false);
  const atual = bolao ? view : 'boloes';
  const noMais = maisItems.some(item => item.id === atual);

  useEffect(() => {
    if (!mais) return;
    const fechar = (e: KeyboardEvent) => { if (e.key === 'Escape') setMais(false); };
    window.addEventListener('keydown', fechar);
    return () => window.removeEventListener('keydown', fechar);
  }, [mais]);

  const botao = 'flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-1.5 rounded-lg transition-colors';
  const cor = (ativo: boolean) => (ativo ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400');

  return (
    <>
      {mais && <button aria-label="Fechar menu" tabIndex={-1} onClick={() => setMais(false)} className="md:hidden fixed inset-0 z-30 cursor-default" />}
      <nav aria-label="Navegação principal" className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-1 py-1.5 flex items-center justify-around safe-area-bottom">
        {navItems.map(item => {
          const Icon = item.icon;
          const active = atual === item.id;
          return (
            <button key={item.id} onClick={() => { setMais(false); setView(item.id); }} aria-current={active ? 'page' : undefined}
              className={`${botao} ${cor(active)}`}>
              <Icon className="w-5 h-5" />
              <span className="text-[9px] font-medium">{item.label}</span>
            </button>
          );
        })}
        <button onClick={() => setMais(!mais)} aria-expanded={mais} aria-haspopup="true" className={`${botao} ${cor(noMais || mais)}`}>
          <MoreHorizontal className="w-5 h-5" />
          <span className="text-[9px] font-medium">Mais</span>
        </button>
        {mais && (
          <div className="absolute bottom-full right-2 mb-2 w-52 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 shadow-xl p-1.5 animate-fade-in">
            {maisItems.map(item => {
              const Icon = item.icon;
              const active = atual === item.id;
              return (
                <button key={item.id} onClick={() => { setMais(false); setView(item.id); }} aria-current={active ? 'page' : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${active ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
                  <Icon className="w-5 h-5 shrink-0" />{item.label}
                </button>
              );
            })}
          </div>
        )}
      </nav>
    </>
  );
}
