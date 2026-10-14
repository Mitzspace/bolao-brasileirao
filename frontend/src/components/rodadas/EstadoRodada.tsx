import { AlertTriangle, CheckCircle2, CircleDot, MinusCircle } from 'lucide-react';
import type { EstadoRodada } from '@/types';

export const infoEstado: Record<EstadoRodada, { texto: string; classe: string; ponto: string }> = {
  pendente: { texto: 'Pendente', classe: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 ring-1 ring-red-300 dark:ring-red-800', ponto: 'bg-red-500' },
  aberta: { texto: 'Aberta', classe: 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300', ponto: 'bg-brand-500' },
  fechada: { texto: 'Fechada', classe: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400', ponto: 'bg-gray-400' },
  sem_jogos: { texto: 'Sem jogos', classe: 'bg-gray-50 text-gray-400 dark:bg-gray-900 dark:text-gray-500', ponto: 'bg-gray-200' },
};

const icones = { pendente: AlertTriangle, aberta: CircleDot, fechada: CheckCircle2, sem_jogos: MinusCircle };

/** Selo do estado da rodada; "Pendente" mostra quantos palpites faltam. */
export function EstadoRodadaBadge({ estado, faltantes }: { estado: EstadoRodada; faltantes?: number }) {
  const info = infoEstado[estado];
  const Icon = icones[estado];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${info.classe}`}
      title={estado === 'pendente' ? `Rodada iniciada com ${faltantes ?? 0} palpites faltando` : undefined}>
      <Icon className={`w-3 h-3 ${estado === 'pendente' ? 'animate-pulse' : ''}`} />
      {info.texto}{estado === 'pendente' && faltantes ? ` · ${faltantes}` : ''}
    </span>
  );
}
