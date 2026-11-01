import { useCallback, useState } from 'react';
import { Users } from 'lucide-react';
import { DesempenhoParticipante } from '@/components/participantes/DesempenhoParticipante';
import { Drawer } from '@/components/ui/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { Switch } from '@/components/ui/Form';
import { useRecurso } from '@/lib/useRecurso';
import type { ClassificacaoBolaoApi } from '@/types';
import { Podio } from './Podio';
import { TabelaClassificacao } from './TabelaClassificacao';

export type ClassificacaoComEliminacao = ClassificacaoBolaoApi & { eliminadosOcultos?: number };

/** Classificação do bolão com os filtros da tela (geral ou por rodada, ocultar desistentes). */
export function useClassificacao(bolaoId: number) {
  const [rodadaId, setRodadaId] = useState('');
  // Desistentes ficam ocultos por padrão (pedido do bolão); o switch mostra quando preciso.
  const [ocultar, setOcultar] = useState(true);
  const params = new URLSearchParams();
  if (rodadaId) params.set('rodada_id', rodadaId);
  if (ocultar) params.set('ocultar_desistentes', '1');
  const recurso = useRecurso<ClassificacaoComEliminacao>(`/boloes/${bolaoId}/classificacao?${params}`);
  return { ...recurso, rodadaId, setRodadaId, ocultar, setOcultar };
}

/** Filtros, pódio e tabela de pontuação; o nome do participante abre o desempenho dele. */
export function CartaoClassificacao({ bolaoId, dados, rodadaId, setRodadaId, ocultar, setOcultar }: {
  bolaoId: number; dados: ClassificacaoComEliminacao; rodadaId: string; setRodadaId: (id: string) => void;
  ocultar: boolean; setOcultar: (ocultar: boolean) => void;
}) {
  const [desempenho, setDesempenho] = useState<{ id: number; nome: string } | null>(null);
  const fecharDesempenho = useCallback(() => setDesempenho(null), []);
  return (
    <>
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden animate-slide-up">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <select value={rodadaId} onChange={e => setRodadaId(e.target.value)} aria-label="Classificação"
            className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
            <option value="">Classificação geral</option>
            {dados.rodadas.map(r => <option key={r.id} value={r.id}>Somente a {r.nome}</option>)}
          </select>
          <div className="sm:ml-auto"><Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" /></div>
        </div>

        {!!dados.eliminadosOcultos && <p className="px-5 py-3 text-xs text-gray-500 dark:text-gray-400">{dados.eliminadosOcultos} participantes eliminados nas fases anteriores não aparecem no ranking.</p>}
        {dados.ranking.length === 0 ? (
          <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação" description="Cadastre participantes e lance resultados para ver a classificação." />
        ) : (
          <>
            <div className="p-5 bg-gradient-to-b from-brand-50 to-transparent dark:from-brand-900/20">
              <Podio ranking={dados.ranking} />
            </div>
            <TabelaClassificacao geral={!dados.rodadaId}
              onAbrir={l => setDesempenho({ id: Number(l.chave), nome: l.nome })}
              dicaVariacao={dados.variacaoReferencia ? `Variação após a ${dados.variacaoReferencia}` : undefined}
              itens={dados.ranking.map(p => ({ chave: p.participacaoId, avatarId: p.participacaoId, nome: p.nome, status: p.status,
                posicao: p.posicao, pontos: p.pontos, pontosPalpites: p.pontosPalpites, bonus: p.bonus,
                bonusPrimeiroGol: p.bonusPrimeiroGol, cravadas: p.cravadas, acertos: p.acertosVencedor, variacao: p.variacao }))} />
          </>
        )}
      </div>
      <Drawer open={!!desempenho} onClose={fecharDesempenho} title="Desempenho do participante" width="max-w-xl">
        {desempenho && <DesempenhoParticipante key={`${bolaoId}-${desempenho.id}`} bolaoId={bolaoId} participacaoId={desempenho.id} nome={desempenho.nome} />}
      </Drawer>
    </>
  );
}
