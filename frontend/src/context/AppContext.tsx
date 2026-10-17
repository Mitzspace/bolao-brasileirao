import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { views, type Bootstrap, type View } from '@/types';
import { configurarApi } from '@/lib/api';
import { useTema } from '@/lib/tema';

function hashView(): View {
  const value = window.location.hash.slice(1);
  if (value === 'campeonatos') return 'configuracoes'; // campeonatos ficam em Configurações
  return views.includes(value as View) ? value as View : 'dashboard';
}
const dataElement = document.getElementById('interface-data');
if (!dataElement?.textContent) throw new Error('Contexto da interface não disponível.');
const dados: Bootstrap = JSON.parse(dataElement.textContent);
configurarApi({ base: dados.apiBase, csrfToken: dados.csrfToken });

interface AppState {
  dados: Bootstrap;
  usuario: Bootstrap['usuario'];
  bolao: Bootstrap['boloes'][number] | undefined;
  view: View;
  setView: (view: View, parametros?: Record<string, number>) => void;
  /** Parâmetros passados na última navegação (ex.: rodada a abrir no lançamento). */
  parametros: Record<string, number>;
  darkMode: boolean;
  toggleDarkMode: () => void;
  logout: () => void;
}
const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [view, updateView] = useState<View>(hashView);
  // Gestão: claro por padrão (como antes); a escolha fica salva na mesma chave de sempre.
  const { escuro: darkMode, alternar: toggleDarkMode } = useTema('bolao-interface-theme', 'claro');
  const [parametros, setParametros] = useState<Record<string, number>>({});
  useEffect(() => {
    const change = () => updateView(hashView());
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  const setView = (next: View, novos: Record<string, number> = {}) => {
    setParametros(novos);
    window.location.hash = next;
    updateView(next);
    document.getElementById('conteudo')?.scrollTo({ top: 0 });
  };
  return <AppContext.Provider value={{
    dados, usuario: dados.usuario, bolao: dados.boloes.find(b => b.id === dados.bolaoAtualId),
    view, setView, parametros, darkMode, toggleDarkMode,
    logout: () => window.location.assign(dados.links.logout),
  }}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('AppProvider não encontrado.');
  return context;
}
