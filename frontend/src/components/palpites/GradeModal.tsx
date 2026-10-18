import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { useRecurso } from '@/lib/useRecurso';
import type { GradeApi } from '@/types';

/** Grade de palpites da rodada (participantes × jogos), no estilo da "planilha" do Bolt, somente leitura. */
export function GradeModal({ rodadaId, onClose }: { rodadaId: number | null; onClose: () => void }) {
  const showToast = useToast();
  const { dados, carregando, erro, recarregar } = useRecurso<GradeApi>(rodadaId ? `/rodadas/${rodadaId}/grade` : null);
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    if (!dados) return;
    try {
      await navigator.clipboard.writeText(dados.textoWhatsapp);
      setCopiado(true); showToast('Texto copiado para colar no WhatsApp.');
      setTimeout(() => setCopiado(false), 2000);
    } catch { showToast('Não foi possível copiar. Selecione o texto manualmente.', 'error'); }
  };

  return (
    <Modal open={rodadaId !== null} onClose={onClose} size="xl" title={dados ? `Grade de palpites — ${dados.rodada}` : 'Grade de palpites'}
      footer={dados ? (
        <button onClick={copiar} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#25D366] hover:bg-[#1fb857] text-white text-sm font-semibold">
          {copiado ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} Copiar resumo para o WhatsApp
        </button>
      ) : undefined}>
      {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {!dados && carregando && <Carregando linhas={4} />}
      {dados && (
        <div className="overflow-auto scrollbar-thin -mx-6 -my-5 max-h-[65vh]">
          <table className="text-sm border-separate border-spacing-0">
            <thead>
              <tr>
                <th className="sticky top-0 left-0 z-20 bg-gray-50 dark:bg-gray-800 text-left px-3 py-2 text-xs font-semibold text-gray-500 min-w-[9rem]">Jogo</th>
                {dados.participantes.map(p => (
                  <th key={p.id} className="sticky top-0 z-10 bg-gray-50 dark:bg-gray-800 px-2 py-2 text-xs font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">{p.nome}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dados.linhas.map(l => (
                <tr key={l.jogo.id}>
                  <td className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2 border-b border-gray-100 dark:border-gray-800">
                    <div className="flex items-center gap-1.5 whitespace-nowrap">
                      <TeamCrest nome={l.jogo.casa} escudo={l.jogo.escudoCasa} size="xs" />
                      <span className="text-xs font-semibold">{l.jogo.escudoCasa.sigla}</span>
                      <span className="text-xs font-bold text-gray-500">{l.jogo.golsCasa ?? ''}×{l.jogo.golsFora ?? ''}{l.jogo.penaltisCasa != null && l.jogo.penaltisFora != null ? ` (pên. ${l.jogo.penaltisCasa}×${l.jogo.penaltisFora})` : ''}</span>
                      <span className="text-xs font-semibold">{l.jogo.escudoFora.sigla}</span>
                      <TeamCrest nome={l.jogo.fora} escudo={l.jogo.escudoFora} size="xs" />
                    </div>
                  </td>
                  {dados.participantes.map(p => {
                    const c = l.celulas[String(p.id)];
                    const cor = !c ? 'text-gray-300' : c.situacao !== 'valido' ? 'bg-red-50 text-red-600 dark:bg-red-900/20'
                      : c.cravada ? 'bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-200 font-bold'
                      : c.vencedor ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300' : '';
                    return (
                      <td key={p.id} className={`px-2 py-2 text-center whitespace-nowrap border-b border-gray-100 dark:border-gray-800 ${cor}`}
                        title={c?.primeiroGol ? `1º gol: ${c.primeiroGol}` : undefined}>
                        {!c ? '—' : c.situacao === 'nao_enviado' ? 'N/E' : c.situacao === 'fora_prazo' ? 'F/P' : `${c.casa}×${c.fora}`}
                        {c?.situacao === 'valido' && c.penaltisCasa != null && c.penaltisFora != null && (
                          <span className="block text-[10px] opacity-80">pên. {c.penaltisCasa}×{c.penaltisFora}</span>
                        )}
                        {c?.pontos != null && <span className="block text-[10px] opacity-80">{c.pontos} pt{c.primeiroGol ? ' ★' : ''}</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr>
                <td className="sticky left-0 z-10 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-xs font-bold">Total da rodada</td>
                {dados.participantes.map(p => (
                  <td key={p.id} className="bg-gray-50 dark:bg-gray-800 px-2 py-2 text-center font-bold text-brand-700 dark:text-brand-300">
                    {p.pontos}{p.bonus ? <span className="block text-[10px] font-normal text-gray-500">+{p.bonus} crédito</span> : null}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
          <p className="px-6 py-3 text-xs text-gray-400">Verde forte: cravada · verde claro: acertou o resultado · N/E: não enviou · F/P: fora do prazo · ★ palpitou primeiro gol</p>
        </div>
      )}
    </Modal>
  );
}
