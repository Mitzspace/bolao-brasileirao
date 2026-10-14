import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { views, type Bootstrap, type View } from '@/types';

function hashView(): View {
  const value = window.location.hash.slice(1);
  return views.includes(value as View) ? value as View : 'dashboard';
}
function initialTheme(): boolean {
  try { return localStorage.getItem('bolao-interface-theme') === 'dark'; }
  catch { return false; }
}
const dataElement = document.getElementById('interface-data');
if (!dataElement?.textContent) throw new Error('Contexto da interface não disponível.');
const dados: Bootstrap = JSON.parse(dataElement.textContent);

interface AppState {
  dados: Bootstrap;
  usuario: Bootstrap['usuario'];
  bolao: Bootstrap['boloes'][number] | undefined;
  view: View;
  setView: (view: View) => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
  logout: () => void;
}
const AppContext = createContext<AppState | null>(null);
export function AppProvider({ children }: { children: ReactNode }) {
  const [view, updateView] = useState<View>(hashView);
  const [darkMode, setDarkMode] = useState(initialTheme);
  useEffect(() => {
    const change = () => updateView(hashView());
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    try { localStorage.setItem('bolao-interface-theme', darkMode ? 'dark' : 'light'); }
    catch { /* O tema continua funcionando quando o armazenamento é indisponível. */ }
  }, [darkMode]);
  const setView = (next: View) => { window.location.hash = next; updateView(next); };
  return <AppContext.Provider value={{
    dados, usuario: dados.usuario, bolao: dados.boloes.find(b => b.id === dados.bolaoAtualId),
    view, setView, darkMode, toggleDarkMode: () => setDarkMode(value => !value),
    logout: () => window.location.assign(dados.links.logout),
  }}>{children}</AppContext.Provider>;
}
export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('AppProvider não encontrado.');
  return context;
}
