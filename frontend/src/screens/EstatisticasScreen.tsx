import { useCallback, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { PainelEstatisticas } from '@/components/estatisticas/PainelEstatisticas';
import { DesempenhoParticipante } from '@/components/participantes/DesempenhoParticipante';
import { Drawer } from '@/components/ui/Drawer';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import type { EstatisticasApi } from '@/types';

/** Possíveis ganhadores do bolão selecionado. */
export function EstatisticasScreen() {
  const { dados, carregando, erro, recarregar } = useRecurso<EstatisticasApi>('/estatisticas');
  const [desempenho, setDesempenho] = useState<{ id: number; nome: string } | null>(null);
  const fechar = useCallback(() => setDesempenho(null), []);
  return (
    <div>
      <Header title="Estatísticas" subtitle="Possíveis ganhadores e desempenho" />
      <div className="p-4 md:p-8 pb-28 md:pb-8">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={4} />}
        {dados && (
          <PainelEstatisticas dados={dados}
            onAbrir={l => setDesempenho({ id: l.participacaoId, nome: l.nome })} />
        )}
      </div>
      <Drawer open={!!desempenho} onClose={fechar} title="Desempenho do participante" width="max-w-xl">
        {desempenho && dados && <DesempenhoParticipante key={desempenho.id} bolaoId={dados.bolao.id} participacaoId={desempenho.id} nome={desempenho.nome} />}
      </Drawer>
    </div>
  );
}
