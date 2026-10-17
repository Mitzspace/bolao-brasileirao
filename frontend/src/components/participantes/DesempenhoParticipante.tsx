import { Avatar } from '@/components/ui/Avatar';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import type { DesempenhoParticipanteApi } from '@/types';
import { PainelDesempenho } from './PainelDesempenho';
import { StatusBadge } from './StatusBadge';

/**
 * Desempenho de um participante aberto pela classificação do bolão (gestão):
 * o mesmo painel que o participante vê no link público, sem dados de gestão.
 */
export function DesempenhoParticipante({ bolaoId, participacaoId, nome }: { bolaoId: number; participacaoId: number; nome: string }) {
  const { dados, carregando, erro, recarregar } = useRecurso<DesempenhoParticipanteApi>(`/boloes/${bolaoId}/participantes/${participacaoId}/desempenho`);
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Avatar nome={dados?.nome ?? nome} id={participacaoId} size="lg" />
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white break-words">{dados?.nome ?? nome}</h3>
          {dados && <div className="mt-1"><StatusBadge status={dados.status} /></div>}
        </div>
      </div>
      {erro && !dados && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {!dados && !erro && <Carregando linhas={3} />}
      {dados && (
        <PainelDesempenho resumo={dados.resumo} evolucao={dados.evolucao.map(e => ({ ...e, chave: e.rodadaId }))}
          carregando={carregando} erro={erro} onTentar={recarregar} />
      )}
    </div>
  );
}
