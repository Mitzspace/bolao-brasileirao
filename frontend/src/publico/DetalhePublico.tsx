import { Hourglass } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { PainelDesempenho } from '@/components/participantes/PainelDesempenho';
import { useRecurso } from '@/lib/useRecurso';
import { idDoNome } from './comum';
import type { ParticipantePublicoApi } from './tipos';

/**
 * Desempenho de um participante na página pública: pontos totais, posição, pontuação por rodada,
 * histórico e melhor rodada (o mesmo painel da gestão). Só até a rodada liberada; sem dados pessoais.
 */
export function DetalhePublico({ refPublica, nome }: { refPublica: string; nome: string }) {
  const { dados, carregando, erro, recarregar } = useRecurso<ParticipantePublicoApi>(`/participantes/${encodeURIComponent(refPublica)}`);
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Avatar nome={dados?.nome ?? nome} id={idDoNome(dados?.nome ?? nome)} size="lg" />
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white break-words">{dados?.nome ?? nome}</h3>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {dados?.status === 'desistente' ? <Badge color="yellow">Desistente</Badge> : <Badge color="green">Ativo</Badge>}
            {dados?.tabela && <Badge color="gray">Até a {dados.tabela.nome}</Badge>}
          </div>
        </div>
      </div>

      {erro && !dados && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {!dados && !erro && <Carregando linhas={3} />}
      {dados && !dados.liberada && (
        <div className="p-6 rounded-xl bg-gold-50 dark:bg-gold-900/20 text-center">
          <Hourglass className="w-8 h-8 text-gold-500 mx-auto mb-2" />
          <p className="font-semibold text-gray-900 dark:text-white">Pontuação em breve</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Os organizadores ainda não divulgaram a classificação.</p>
        </div>
      )}
      {dados?.liberada && (
        <PainelDesempenho
          resumo={{ pontos: dados.pontos, cravadas: dados.cravadas, posicao: dados.posicao, variacao: dados.variacao }}
          evolucao={dados.evolucao.map(e => ({ ...e, chave: e.numero }))}
          carregando={carregando}
          semDados="Ainda não há rodadas com resultado divulgadas."
        />
      )}
    </div>
  );
}
