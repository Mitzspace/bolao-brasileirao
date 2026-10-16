import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { acompanharRequisicoes, AVISO_LENTO_MS } from '@/lib/api';

/** Espera curta antes de mostrar a barra, para respostas rápidas não piscarem. */
const ATRASO_MS = 120;

/**
 * Barra fina no topo da tela enquanto houver requisição em andamento (troca de aba,
 * salvamento...). Se demorar, avisa que o servidor gratuito pode estar acordando.
 */
export function BarraProgresso() {
  const [ativo, setAtivo] = useState(false);
  const [lento, setLento] = useState(false);

  useEffect(() => {
    let mostrar: number | undefined;
    let avisoLento: number | undefined;
    const limpar = () => { window.clearTimeout(mostrar); window.clearTimeout(avisoLento); };
    const parar = acompanharRequisicoes((quantas, desde) => {
      limpar();
      if (quantas === 0 || desde === null) { setAtivo(false); setLento(false); return; }
      const passou = Date.now() - desde;
      if (passou >= ATRASO_MS) setAtivo(true);
      else mostrar = window.setTimeout(() => setAtivo(true), ATRASO_MS - passou);
      if (passou >= AVISO_LENTO_MS) setLento(true);
      else avisoLento = window.setTimeout(() => setLento(true), AVISO_LENTO_MS - passou);
    });
    return () => { limpar(); parar(); };
  }, []);

  return (
    <>
      <div aria-hidden={!ativo}
        className={`fixed top-0 inset-x-0 z-[110] h-1 overflow-hidden pointer-events-none transition-opacity duration-200 ${ativo ? 'opacity-100' : 'opacity-0'}`}>
        <div className="h-full w-full bg-brand-100 dark:bg-brand-900/40">
          <div className="h-full w-2/5 bg-brand-500 rounded-full animate-progresso" />
        </div>
      </div>
      <div role="status" aria-live="polite" className="sr-only">{ativo ? 'Carregando…' : ''}</div>
      {ativo && lento && (
        <div role="status" className="fixed top-[5.25rem] left-1/2 -translate-x-1/2 z-[110] flex items-center gap-2 px-4 py-2 rounded-full bg-gray-900/90 dark:bg-gray-800/95 text-white text-xs font-medium shadow-lg animate-fade-in max-w-[calc(100vw-2rem)]">
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span>Demorando mais que o normal: o servidor gratuito pode estar acordando (até 1 min)…</span>
        </div>
      )}
    </>
  );
}
