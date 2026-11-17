import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

/** Variação de posição na classificação (positivo = subiu), como uma pequena etiqueta colorida. */
export function Variacao({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="text-xs text-gray-300 dark:text-gray-600" title="Sem comparação">—</span>;
  if (valor === 0) {
    return (
      <span className="inline-flex items-center justify-center w-7 h-6 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-400" title="Manteve a posição">
        <Minus className="w-3.5 h-3.5" />
      </span>
    );
  }
  const subiu = valor > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 h-6 px-1.5 rounded-md text-xs font-bold ${subiu
      ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
      : 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'}`}
      title={subiu ? `Subiu ${valor} ${valor === 1 ? 'posição' : 'posições'}` : `Caiu ${-valor} ${valor === -1 ? 'posição' : 'posições'}`}>
      {subiu ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />}{Math.abs(valor)}
    </span>
  );
}
