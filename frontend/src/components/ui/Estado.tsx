import { AlertCircle, RotateCw } from 'lucide-react';
import { Skeleton } from './EmptyState';

/** Placeholder de carregamento no formato dos cards do Bolt. */
export function Carregando({ linhas = 3 }: { linhas?: number }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Carregando">
      {Array.from({ length: linhas }, (_, i) => <Skeleton key={i} className="h-20 w-full rounded-2xl" />)}
    </div>
  );
}

/** Falha ao carregar dados, com opção de tentar de novo. */
export function ErroCarga({ mensagem, onTentar }: { mensagem: string; onTentar?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center py-12 text-center bg-white dark:bg-gray-900 rounded-2xl border border-red-100 dark:border-red-900/40">
      <div className="w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-3">
        <AlertCircle className="w-7 h-7 text-red-600" />
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-300 max-w-sm">{mensagem}</p>
      {onTentar && (
        <button onClick={onTentar} className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
          <RotateCw className="w-4 h-4" /> Tentar novamente
        </button>
      )}
    </div>
  );
}
