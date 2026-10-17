import { useState } from 'react';
import { TabelaOficial } from '@/components/campeonatos/TabelaOficial';
import { AgendaRodada, SeletorVisaoJogos, type VisaoJogos } from '@/components/jogos/AgendaRodada';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import { rodadasDoSeletor } from '../comum';
import type { JogosApi } from '../tipos';

/** Mesma aba Jogos da gestão (rodada, horários e jogos atrasados) + tabela do campeonato. */
export function Jogos({ rotuloTabela }: { rotuloTabela: string }) {
  const [visao, setVisao] = useState<VisaoJogos>('jogos');
  const [numero, setNumero] = useState<number | null>(null);
  const { dados, carregando, erro, recarregar } = useRecurso<JogosApi>(numero ? `/jogos?rodada=${numero}` : '/jogos');
  const r = dados?.rodada;
  return (
    <div className="space-y-6">
      <SeletorVisaoJogos visao={visao} onMudar={setVisao} rotuloTabela={rotuloTabela} />
      {visao === 'tabela' && <TabelaOficial />}
      {visao === 'jogos' && erro && !dados && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {visao === 'jogos' && !dados && !erro && <Carregando linhas={5} />}
      {visao === 'jogos' && dados && r && (
        <AgendaRodada
          agora={dados.agora}
          rodadas={rodadasDoSeletor(dados.rodadas)}
          selecionadaId={numero ?? r.numero}
          atualId={dados.atual}
          onSelecionar={n => setNumero(n === dados.atual ? null : n)}
          onIrAtual={() => setNumero(null)}
          rodada={r}
          jogos={dados.jogos}
          atrasados={dados.atrasados}
          carregando={carregando}
          rodape={<p className="text-xs text-gray-400 text-center">Horários de Brasília.</p>}
        />
      )}
      {visao === 'jogos' && dados && !r && <p className="text-sm text-gray-400 text-center py-12">Nenhuma rodada cadastrada neste campeonato.</p>}
    </div>
  );
}
