import { useState } from 'react';
import { Check, Clock, Copy, Info, MessageCircle } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { Formatado } from '@/components/boloes/CompartilharClassificacao';
import { useRecurso } from '@/lib/useRecurso';
import type { ModeloPalpitesApi } from '@/types';

function Balao({ texto }: { texto: string }) {
  return (
    <div className="relative ml-auto max-w-[92%] w-fit rounded-xl rounded-tr-sm bg-[#d9fdd3] dark:bg-[#005c4b] px-3 py-2 shadow-sm">
      <p className="text-[13.5px] leading-[1.45] text-[#111b21] dark:text-[#e9edef] whitespace-pre-wrap break-words select-text">
        <Formatado texto={texto} />
      </p>
    </div>
  );
}

const botaoVerde = 'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#25D366] hover:bg-[#1fb857] text-white font-semibold transition-colors disabled:opacity-50';
const botaoClaro = 'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-[#25D366] text-[#128c4a] dark:text-[#4ade80] font-semibold hover:bg-[#25D366]/10 transition-colors disabled:opacity-50';

/** Prévia em balão do WhatsApp do modelo de palpites da rodada, com "Copiar" (modelo e prazo separados). */
export function ModeloPalpites({ rodadaId, onClose }: { rodadaId: number | null; onClose: () => void }) {
  const showToast = useToast();
  const [copiado, setCopiado] = useState<'modelo' | 'prazo' | null>(null);
  const { dados, carregando, erro, recarregar } = useRecurso<ModeloPalpitesApi>(rodadaId ? `/rodadas/${rodadaId}/modelo-palpites` : null);

  const copiar = async (qual: 'modelo' | 'prazo', texto: string, aviso: string) => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(qual); showToast(aviso);
      setTimeout(() => setCopiado(atual => atual === qual ? null : atual), 2000);
    } catch { showToast('Não foi possível copiar. Selecione o texto da prévia.', 'error'); }
  };

  return (
    <Modal open={rodadaId !== null} onClose={onClose} title="Modelo de palpites" size="md"
      footer={dados ? (
        <div className="w-full space-y-2">
          {dados.prazo && (
            <button onClick={() => copiar('prazo', dados.prazo!, 'Prazo copiado. Envie antes do modelo.')} className={botaoClaro}>
              {copiado === 'prazo' ? <Check className="w-5 h-5" /> : <Clock className="w-5 h-5" />} Copiar prazo
            </button>
          )}
          <button onClick={() => copiar('modelo', dados.texto, 'Modelo copiado. Cole no grupo do WhatsApp.')} disabled={!dados.texto} className={botaoVerde}>
            {copiado === 'modelo' ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />} Copiar modelo
          </button>
        </div>
      ) : undefined}>
      {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {!dados && carregando && <Carregando linhas={3} />}
      {dados && (
        <div className="space-y-4">
          {dados.omitidos > 0 && (
            <div role="status" className="flex items-start gap-2 rounded-xl border border-gold-200 dark:border-gold-800/50 bg-gold-50 dark:bg-gold-900/20 p-3 text-sm text-gold-800 dark:text-gold-200">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <p>{dados.omitidos === 1 ? '1 jogo já começou e ficou de fora do modelo.' : `${dados.omitidos} jogos já começaram e ficaram de fora do modelo.`}</p>
            </div>
          )}
          {!dados.texto ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Todos os jogos de {dados.rodada} já começaram: não há o que palpitar.</p>
          ) : (
            <div className="rounded-2xl p-4 bg-[#efeae2] dark:bg-[#0b141a] space-y-3">
              <div className="flex items-center gap-2 text-xs font-medium text-[#54656f] dark:text-[#8696a0]">
                <MessageCircle className="w-4 h-4" /> Prévia das mensagens
              </div>
              {dados.prazo && <Balao texto={dados.prazo} />}
              <Balao texto={dados.texto} />
            </div>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {'★'} marca os clássicos: o participante escreve o autor do 1º gol depois dela. Envie o prazo primeiro e o modelo em seguida.
          </p>
        </div>
      )}
    </Modal>
  );
}
