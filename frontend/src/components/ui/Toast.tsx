import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import { CheckCircle2, AlertCircle, Info, X, XCircle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';
interface Toast { id: string; message: string; type: ToastType; }

const ToastContext = createContext<{ showToast: (message: string, type?: ToastType) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const contador = useRef(0);

  const showToast = useCallback((message: string, type: ToastType = 'success') => {
    const id = `toast-${++contador.current}`;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), type === 'error' ? 6000 : 3500);
  }, []);

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-brand-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertCircle className="w-5 h-5 text-gold-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div aria-live="polite" className="fixed bottom-20 md:bottom-6 right-4 left-4 sm:left-auto z-[100] space-y-2 pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-xl shadow-lg px-4 py-3 sm:min-w-[280px] animate-slide-up pointer-events-auto border border-gray-100 dark:border-gray-700"
          >
            {icons[t.type]}
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200 flex-1">{t.message}</span>
            <button onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))} aria-label="Fechar aviso" className="text-gray-400 hover:text-gray-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('ToastProvider não encontrado.');
  return ctx.showToast;
}
