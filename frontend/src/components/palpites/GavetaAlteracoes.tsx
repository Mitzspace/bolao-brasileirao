import { forwardRef } from 'react';
import { ArrowRight, ChevronDown, Clock, Inbox, Monitor, MessageCircle, HelpCircle, User } from 'lucide-react';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import type { CanalPalpite, ItemHistoricoPalpite } from '@/types';

const ORIGEM: Record<CanalPalpite, { texto: string; classe: string; Icone: typeof Monitor }> = {
  painel: { texto: 'Painel admin', classe: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300', Icone: Monitor },
  whatsapp: { texto: 'WhatsApp', classe: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300', Icone: MessageCircle },
  desconhecida: { texto: 'Origem desconhecida', classe: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400', Icone: HelpCircle },
};

function Item({ item }: { item: ItemHistoricoPalpite }) {
  const origem = ORIGEM[item.canal];
  return (
    <li className="rounded-xl border border-gray-100 dark:border-gray-800 p-3 sm:p-4">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span className="font-semibold text-gray-900 dark:text-white text-sm">{item.acao}</span>
        <span className="text-gray-400">· {item.rodada}</span>
        <span className={`ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold ${origem.classe}`}>
          <origem.Icone className="w-3 h-3" />{origem.texto}
        </span>
      </div>
      <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
        <span className="inline-flex items-center gap-1"><User className="w-3 h-3" />{item.autor ?? 'Autor desconhecido'}</span>
        <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" />{item.quandoTexto ?? 'Data desconhecida'}</span>
        {item.recebidoEm && <span>Recebido em {item.recebidoEm}</span>}
      </p>
      <ul className="mt-2 divide-y divide-gray-50 dark:divide-gray-800/70">
        {item.mudancas.map((m, i) => (
          <li key={i} className="py-1.5 text-sm">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span className="flex-1 min-w-[8rem] text-gray-700 dark:text-gray-300 truncate">{m.jogo}</span>
              <span className="inline-flex items-center gap-1.5 tabular-nums">
                {m.antes !== null && <><span className="text-gray-400 line-through decoration-gray-300 dark:decoration-gray-600">{m.antes}</span><ArrowRight className="w-3 h-3 text-gray-400" /></>}
                <strong className="text-gray-900 dark:text-white">{m.depois ?? '—'}</strong>
                {m.antes === null && item.canal !== 'desconhecida' && <span className="text-[10px] font-semibold uppercase text-brand-600 dark:text-brand-400">novo</span>}
              </span>
            </div>
            {m.detalhes.map(d => <p key={d} className="text-xs text-gray-500 dark:text-gray-400">{d}</p>)}
          </li>
        ))}
      </ul>
      {item.textoWhatsapp && (
        <details className="mt-2 group">
          <summary className="cursor-pointer text-xs font-semibold text-brand-700 dark:text-brand-300 select-none">Ver mensagem original</summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words font-sans">{item.textoWhatsapp}</pre>
        </details>
      )}
    </li>
  );
}

interface Props {
  participacaoId: number;
  nome: string;
  aberta: boolean;
  onAlternar: () => void;
  /** Muda depois de salvar, para a gaveta buscar o histórico de novo. */
  versao: string;
}

/**
 * Gaveta no final da tela de palpites: recolhida por padrão; aberta, lista todas as alterações
 * nos palpites desta pessoa (todas as rodadas), da mais recente para a mais antiga. Só gestão.
 */
export const GavetaAlteracoes = forwardRef<HTMLElement, Props>(function GavetaAlteracoes({ participacaoId, nome, aberta, onAlternar, versao }, ref) {
  const caminho = aberta ? `/palpites/historico?participacao_id=${participacaoId}&v=${encodeURIComponent(versao)}` : null;
  const { dados, erro, recarregar } = useRecurso<{ itens: ItemHistoricoPalpite[] }>(caminho);
  return (
    <section ref={ref} id="gaveta-alteracoes" className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 scroll-mt-24">
      <button type="button" onClick={onAlternar} aria-expanded={aberta} aria-controls="gaveta-conteudo"
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left rounded-2xl hover:bg-gray-50 dark:hover:bg-gray-800/50">
        <Inbox className="w-5 h-5 text-gray-400 shrink-0" />
        <span className="flex-1 min-w-0">
          <span className="block font-semibold text-gray-900 dark:text-white">Gaveta</span>
          <span className="block text-xs text-gray-400 truncate">Histórico de alterações nos palpites de {nome}</span>
        </span>
        {aberta && dados && <span className="text-xs text-gray-400 shrink-0">{dados.itens.length} {dados.itens.length === 1 ? 'registro' : 'registros'}</span>}
        <ChevronDown className={`w-5 h-5 text-gray-400 shrink-0 transition-transform ${aberta ? 'rotate-180' : ''}`} />
      </button>
      {aberta && (
        <div id="gaveta-conteudo" className="px-3 sm:px-4 pb-4 animate-fade-in">
          {erro && !dados && <ErroCarga mensagem={erro} onTentar={recarregar} />}
          {!dados && !erro && <Carregando linhas={3} />}
          {dados && dados.itens.length === 0 && (
            <div className="flex flex-col items-center text-center py-8">
              <Inbox className="w-9 h-9 text-gray-300 dark:text-gray-600 mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Nenhuma alteração registrada para este participante.</p>
            </div>
          )}
          {dados && dados.itens.length > 0 && (
            <ol className="space-y-2">{dados.itens.map((item, i) => <Item key={`${item.quando}-${i}`} item={item} />)}</ol>
          )}
        </div>
      )}
    </section>
  );
});
