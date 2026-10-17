import { Trophy, Calendar, Users, Settings, LogOut, Moon, Sun, LayoutDashboard, CalendarClock, PencilLine } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { LogoApp } from '@/components/ui/LogoApp';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'jogos', label: 'Jogos', icon: CalendarClock },
  { id: 'palpites', label: 'Lançar palpites', icon: PencilLine },
  { id: 'rodadas', label: 'Rodadas', icon: Calendar },
  { id: 'participantes', label: 'Participantes', icon: Users },
  { id: 'boloes', label: 'Bolões', icon: Trophy },
  { id: 'configuracoes', label: 'Configurações', icon: Settings },
] as const;

export function Sidebar() {
  const { view, setView, logout, darkMode, toggleDarkMode, usuario, bolao } = useApp();
  if (!usuario) return null;

  return (
    <aside className="hidden md:flex flex-col w-64 h-screen bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 shrink-0">
      <div className="px-5 py-5 flex items-center gap-3">
        <LogoApp />
        <div className="min-w-0">
          <h1 className="font-bold text-gray-900 dark:text-white leading-tight truncate">{bolao?.nome ?? 'Gestão de bolões'}</h1>
          <p className="text-xs text-gray-400 truncate">{bolao ? `${bolao.campeonato} ${bolao.ano ?? ''}` : 'Gestão de bolões'}</p>
        </div>
      </div>

      <nav aria-label="Navegação principal" className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(item => {
          const Icon = item.icon;
          const active = (bolao ? view : 'boloes') === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              aria-current={active ? 'page' : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                active
                  ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {item.label}
              {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-500" />}
            </button>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-gray-100 dark:border-gray-800 space-y-1">
        <button
          onClick={toggleDarkMode}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          {darkMode ? 'Modo claro' : 'Modo escuro'}
        </button>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Sair
        </button>
      </div>

      <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
            {usuario.nome.split(' ').filter(Boolean).map(n => n[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{usuario.nome}</p>
            <p className="text-xs text-gray-400 truncate">{usuario.email}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
