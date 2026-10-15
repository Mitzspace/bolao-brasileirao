import { Fragment, useState } from 'react';
import { Check, Copy, MessageCircle } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import type { ClassificacaoBolaoApi } from '@/types';

/** Mostra *negrito* como o WhatsApp mostra. */
function Formatado({ texto }: { texto: string }) {
  return <>{texto.split(/(\*[^*\n]+\*)/g).map((parte, i) =>
    parte.startsWith('*') && parte.endsWith('*') && parte.length > 2
      ? <strong key={i}>{parte.slice(1, -1)}</strong> : <Fragment key={i}>{parte}</Fragment>)}</>;
}

const LEGENDA = [
  ['🟩', '1º ao 4º'], ['🟨', '5º'], ['🟦', '6º ao 10º'], ['⬜', 'meio da tabela'], ['🟥', 'últimos 4'],
];

/** Prévia da mensagem do grupo (balão do WhatsApp) e botão de copiar. */
export function CompartilharClassificacao({ dados, aberto, onClose }: { dados: ClassificacaoBolaoApi; aberto: boolean; onClose: () => void }) {
  const showToast = useToast();
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(dados.textoWhatsapp);
      setCopiado(true); showToast('Classificação copiada. Cole no grupo do WhatsApp.');
      setTimeout(() => setCopiado(false), 2000);
    } catch { showToast('Não foi possível copiar. Selecione o texto da prévia.', 'error'); }
  };

  return (
    <Modal open={aberto} onClose={onClose} title="Compartilhar classificação" size="md"
      footer={
        <button onClick={copiar} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#25D366] hover:bg-[#1fb857] text-white font-semibold transition-colors">
          {copiado ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />} Copiar para o WhatsApp
        </button>
      }>
      <div className="space-y-4">
        <div className="rounded-2xl p-4 bg-[#efeae2] dark:bg-[#0b141a]">
          <div className="flex items-center gap-2 mb-3 text-xs font-medium text-[#54656f] dark:text-[#8696a0]">
            <MessageCircle className="w-4 h-4" /> Prévia da mensagem
          </div>
          <div className="relative ml-auto max-w-[92%] w-fit rounded-xl rounded-tr-sm bg-[#d9fdd3] dark:bg-[#005c4b] px-3 py-2 shadow-sm">
            <p className="text-[13.5px] leading-[1.45] text-[#111b21] dark:text-[#e9edef] whitespace-pre-wrap break-words select-text">
              <Formatado texto={dados.textoWhatsapp} />
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
          {LEGENDA.map(([cor, faixa]) => <span key={faixa}>{cor} {faixa}</span>)}
        </div>
      </div>
    </Modal>
  );
}
