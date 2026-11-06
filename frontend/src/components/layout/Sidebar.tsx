import { Trophy, Calendar, Users, Settings, LogOut, Moon, Sun, LayoutDashboard, CalendarClock, PencilLine, ListOrdered, BarChart3 } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { LogoApp } from '@/components/ui/LogoApp';

const grupos = [
  {
    titulo: 'Acompanhar',
    itens: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'tabela', label: 'Tabela de pontuação', icon: ListOrdered },
      { id: 'estatisticas', label: 'Estatísticas', icon: BarChart3 },
      { id: 'jogos', label: 'Jogos', icon: CalendarClock },
    ],
  },
  {
    titulo: 'Gestão',
    itens: [
      { id: 'palpites', label: 'Lançar palpites', icon: PencilLine },
      { id: 'rodadas', label: 'Rodadas', icon: Calendar },
      { id: 'participantes', label: 'Participantes', icon: Users },
    ],
  },
  {
    titulo: 'Sistema',
    itens: [
      { id: 'boloes', label: 'Bolões', icon: Trophy },
      { id: 'configuracoes', label: 'Configurações', icon: Settings },
    ],
  },
] as const;

export function Sidebar() {
  const { view, setView, logout, darkMode, toggleDarkMode, usuario, bolao } = useApp();
  if (!usuario) return null;

  return (
    <aside className="hidden md:flex flex-col w-64 h-screen bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-r border-gray-100 dark:border-gray-800 shrink-0">
      <div className="mx-3 mt-4 mb-3 px-3 py-3 flex items-center gap-3 rounded-2xl bg-gradient-to-br from-brand-50 to-gold-50/60 dark:from-brand-900/30 dark:to-gray-900 border border-brand-100/70 dark:border-brand-900/40">
        <LogoApp />
        <div className="min-w-0">
          <h1 className="font-bold text-gray-900 dark:text-white leading-tight truncate" title={bolao?.nome}>{bolao?.nome ?? 'Gestão de bolões'}</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{bolao ? `${bolao.campeonato} ${bolao.ano ?? ''}` : 'Gestão de bolões'}</p>
        </div>
      </div>

      <nav aria-label="Navegação principal" className="flex-1 overflow-y-auto scrollbar-thin px-3 py-2 space-y-5">
        {grupos.map(grupo => (
          <div key={grupo.titulo}>
            <p className="px-3 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{grupo.titulo}</p>
            <div className="space-y-0.5">
              {grupo.itens.map(item => {
                const Icon = item.icon;
                const active = (bolao ? view : 'boloes') === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setView(item.id)}
                    aria-current={active ? 'page' : undefined}
                    className={`group w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      active
                        ? 'bg-gradient-to-br from-brand-600 to-brand-500 text-white shadow-md shadow-brand-600/25'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100/80 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
                    }`}
                  >
                    <Icon className={`w-5 h-5 shrink-0 ${active ? '' : 'text-gray-400 group-hover:text-brand-600 dark:group-hover:text-brand-400'}`} />
                    <span className="truncate">{item.label}</span>
                    {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white/90" />}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
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
          <div className="w-9 h-9 rounded-full ring-2 ring-white dark:ring-gray-900 shadow-sm bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
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
