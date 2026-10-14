import { Trophy, Calendar, Users, Target, Settings } from 'lucide-react';
import { useApp } from '@/context/AppContext';

const navItems = [
  { id: 'campeonatos', label: 'Campeonatos', icon: Target },
  { id: 'rodadas', label: 'Rodadas', icon: Calendar },
  { id: 'participantes', label: 'Participantes', icon: Users },
  { id: 'boloes', label: 'Bolões', icon: Trophy },
  { id: 'configuracoes', label: 'Config', icon: Settings },
] as const;

export function BottomNav() {
  const { view, setView } = useApp();

  return (
    <nav aria-label="Navegação principal" className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-1 py-1.5 flex items-center justify-around safe-area-bottom">
      {navItems.map(item => {
        const Icon = item.icon;
        const active = view === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setView(item.id)}
            aria-current={active ? 'page' : undefined}
            className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-1.5 rounded-lg transition-colors ${active ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'}`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[9px] font-medium">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
