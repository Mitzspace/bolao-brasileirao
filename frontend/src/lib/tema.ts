import { useCallback, useEffect, useState } from 'react';

/**
 * Tema claro/escuro compartilhado pela gestão e pela página pública.
 *
 * - A escolha fica salva no navegador ('dark' | 'light'); sem escolha salva, vale o padrão
 *   de quem chama: 'sistema' (segue o celular/computador) ou 'claro'.
 * - Seguindo o sistema, a página acompanha a troca de tema do aparelho em tempo real.
 * - Também ajusta `color-scheme`, para seletores e barras de rolagem nativos combinarem.
 */
export type PadraoTema = 'sistema' | 'claro';

function lerSalvo(chave: string): boolean | null {
  try {
    const valor = localStorage.getItem(chave);
    return valor === 'dark' ? true : valor === 'light' ? false : null;
  } catch {
    return null;
  }
}

function sistemaEscuro(): boolean {
  try { return window.matchMedia('(prefers-color-scheme: dark)').matches; }
  catch { return false; }
}

export function aplicarTema(escuro: boolean) {
  const raiz = document.documentElement;
  raiz.classList.toggle('dark', escuro);
  raiz.style.colorScheme = escuro ? 'dark' : 'light';
}

export function useTema(chave: string, padrao: PadraoTema = 'sistema') {
  const [salvo, setSalvo] = useState<boolean | null>(() => lerSalvo(chave));
  const [doSistema, setDoSistema] = useState(sistemaEscuro);
  const escuro = salvo ?? (padrao === 'sistema' ? doSistema : false);

  useEffect(() => {
    if (padrao !== 'sistema') return;
    let midia: MediaQueryList;
    try { midia = window.matchMedia('(prefers-color-scheme: dark)'); }
    catch { return; }
    const mudar = () => setDoSistema(midia.matches);
    midia.addEventListener?.('change', mudar);
    return () => midia.removeEventListener?.('change', mudar);
  }, [padrao]);

  useEffect(() => { aplicarTema(escuro); }, [escuro]);

  const alternar = useCallback(() => {
    const novo = !escuro;
    setSalvo(novo);
    try { localStorage.setItem(chave, novo ? 'dark' : 'light'); }
    catch { /* Sem armazenamento, o tema vale só até fechar a página. */ }
  }, [chave, escuro]);

  return { escuro, alternar };
}

/** true quando a página está no tema escuro; acompanha a troca (para gráficos fora de contexto). */
export function useEscuroAtual(): boolean {
  const [escuro, setEscuro] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    const raiz = document.documentElement;
    const observador = new MutationObserver(() => setEscuro(raiz.classList.contains('dark')));
    observador.observe(raiz, { attributes: true, attributeFilter: ['class'] });
    return () => observador.disconnect();
  }, []);
  return escuro;
}
