import { type ReactNode } from 'react';
import { Moon, Sun } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { SeletorCampeonato } from '@/components/campeonatos/SeletorCampeonato';
import { LogoApp } from '@/components/ui/LogoApp';

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const { darkMode, toggleDarkMode, setView } = useApp();

  return (
    <header className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-100 dark:border-gray-800 px-4 md:px-8 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => setView('dashboard')} aria-label="Abrir Dashboard" className="md:hidden shrink-0 rounded-xl">
            <LogoApp />
          </button>
          <div className="min-w-0">
            <h1 className="text-lg md:text-xl font-bold text-gray-900 dark:text-white truncate">{title}</h1>
            {subtitle && <p className="text-xs md:text-sm text-gray-400 truncate">{subtitle}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SeletorCampeonato />
          {actions}
          <button
            onClick={toggleDarkMode}
            aria-label={darkMode ? 'Ativar modo claro' : 'Ativar modo escuro'}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-500"
          >
            {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </header>
  );
}
