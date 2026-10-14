import { useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { infoEstado } from './EstadoRodada';
import type { RodadaResumo } from '@/types';

interface Props {
  rodadas: RodadaResumo[];
  selecionadaId: number | null;
  atualId: number | null;
  onSelecionar: (id: number) => void;
}

/**
 * Carrossel de rodadas: setas + números roláveis com o estado de cada rodada.
 * No celular basta deslizar a faixa; a rodada escolhida fica sempre centralizada.
 */
export function SeletorRodadas({ rodadas, selecionadaId, atualId, onSelecionar }: Props) {
  const faixa = useRef<HTMLDivElement>(null);
  const indice = rodadas.findIndex(r => r.id === selecionadaId);

  useEffect(() => {
    const botao = faixa.current?.querySelector<HTMLElement>(`[data-rodada="${selecionadaId}"]`);
    botao?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
  }, [selecionadaId]);

  const ir = (delta: number) => {
    const alvo = rodadas[indice + delta];
    if (alvo) onSelecionar(alvo.id);
  };
  const seta = 'shrink-0 w-9 h-9 rounded-xl flex items-center justify-center border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors';

  return (
    <div className="flex items-center gap-2">
      <button onClick={() => ir(-1)} disabled={indice <= 0} aria-label="Rodada anterior" className={seta}><ChevronLeft className="w-5 h-5" /></button>
      <div ref={faixa} role="tablist" aria-label="Rodadas" className="flex-1 min-w-0 flex gap-1.5 overflow-x-auto no-scrollbar scroll-smooth snap-x py-1 px-0.5">
        {rodadas.map(r => {
          const ativa = r.id === selecionadaId;
          return (
            <button key={r.id} data-rodada={r.id} role="tab" aria-selected={ativa} onClick={() => onSelecionar(r.id)}
              title={`${r.nome} · ${infoEstado[r.estado].texto}`}
              className={`relative snap-center shrink-0 min-w-[2.75rem] h-11 px-2 rounded-xl text-sm font-bold transition-all ${
                ativa ? 'bg-brand-600 text-white shadow-md scale-105'
                  : r.estado === 'pendente' ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 ring-1 ring-red-200 dark:ring-red-800'
                  : r.estado === 'fechada' ? 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                  : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 ring-1 ring-gray-200 dark:ring-gray-700'
              }`}>
              {r.numero}
              <span className={`absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full ${ativa ? 'bg-white' : infoEstado[r.estado].ponto} ${r.id === atualId ? '' : 'opacity-70'}`} />
              {r.id === atualId && !ativa && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-gold-400 ring-2 ring-white dark:ring-gray-900" title="Rodada atual" />}
            </button>
          );
        })}
      </div>
      <button onClick={() => ir(1)} disabled={indice < 0 || indice >= rodadas.length - 1} aria-label="Próxima rodada" className={seta}><ChevronRight className="w-5 h-5" /></button>
    </div>
  );
}
