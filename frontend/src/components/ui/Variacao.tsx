import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

/** Variação de posição na classificação (positivo = subiu). */
export function Variacao({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="text-xs text-gray-300 dark:text-gray-600" title="Sem comparação">—</span>;
  if (valor === 0) return <span className="inline-flex items-center text-xs text-gray-400" title="Manteve a posição"><Minus className="w-3.5 h-3.5" /></span>;
  const subiu = valor > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${subiu ? 'text-brand-600 dark:text-brand-400' : 'text-red-500'}`}
      title={subiu ? `Subiu ${valor} ${valor === 1 ? 'posição' : 'posições'}` : `Caiu ${-valor} ${valor === -1 ? 'posição' : 'posições'}`}>
      {subiu ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />}{Math.abs(valor)}
    </span>
  );
}
