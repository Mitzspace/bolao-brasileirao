import { useState, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Modal } from './Modal';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  /** Pode ser assíncrono: o diálogo só fecha se a operação terminar sem erro. */
  onConfirm: () => void | Promise<unknown>;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

export function ConfirmDialog({ open, onClose, onConfirm, title, message, confirmLabel = 'Confirmar', cancelLabel = 'Cancelar', danger }: ConfirmDialogProps) {
  const [ocupado, setOcupado] = useState(false);

  const confirmar = async () => {
    setOcupado(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      // O erro já foi avisado por quem chamou; o diálogo continua aberto.
    } finally {
      setOcupado(false);
    }
  };

  return (
    <Modal open={open} onClose={ocupado ? () => undefined : onClose} size="sm">
      <div className="flex flex-col items-center text-center">
        <div className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 ${danger ? 'bg-red-100 dark:bg-red-900/30' : 'bg-gold-100 dark:bg-gold-900/30'}`}>
          <AlertTriangle className={`w-7 h-7 ${danger ? 'text-red-600' : 'text-gold-600'}`} />
        </div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
        <div className="text-sm text-gray-500 dark:text-gray-400 mb-6">{message}</div>
        <div className="flex gap-3 w-full">
          <button onClick={onClose} disabled={ocupado} className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-60">
            {cancelLabel}
          </button>
          <button onClick={confirmar} disabled={ocupado} className={`flex-1 px-4 py-2.5 rounded-xl text-white font-medium transition-colors disabled:opacity-60 flex items-center justify-center ${danger ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-600 hover:bg-brand-700'}`}>
            {ocupado ? <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
