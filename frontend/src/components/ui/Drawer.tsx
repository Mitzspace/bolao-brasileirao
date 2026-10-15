import { type ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  width?: string;
  footer?: ReactNode;
}

export function Drawer({ open, onClose, title, children, width = 'max-w-lg', footer }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    // Com uma janela aberta por cima do painel, o Esc fecha só a janela.
    const fecharComEsc = (e: KeyboardEvent) => { if (e.key === 'Escape' && !document.querySelector('[data-janela-modal]')) onClose(); };
    window.addEventListener('keydown', fecharComEsc);
    return () => { document.body.style.overflow = anterior; window.removeEventListener('keydown', fecharComEsc); };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex animate-fade-in">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-label={title} className={`relative ml-auto h-full w-full ${width} bg-white dark:bg-gray-900 shadow-2xl animate-slide-in-right flex flex-col`}>
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800 shrink-0">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">{title}</h2>
            <button onClick={onClose} aria-label="Fechar" className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        )}
        <div className="px-6 py-5 overflow-y-auto scrollbar-thin flex-1">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-end gap-3 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
