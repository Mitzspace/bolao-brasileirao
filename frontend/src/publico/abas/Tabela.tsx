import { useState } from 'react';
import { HelpCircle, Hourglass, Trophy, Users } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { Podio } from '@/components/boloes/Podio';
import { TabelaClassificacao } from '@/components/boloes/TabelaClassificacao';
import { useRecurso } from '@/lib/useRecurso';
import type { ItemRanking } from '@/types';
import { cartao, idDoNome, Titulo } from '../comum';
import type { AbrirParticipante, ClassificacaoApi } from '../tipos';
type ClassificacaoComEliminacao = ClassificacaoApi & { eliminadosOcultos?: number };

/** Mensagem enquanto o admin não libera a classificação. */
export function TabelaEmBreve() {
  return (
    <div className={`${cartao} p-8 flex flex-col items-center text-center`}>
      <div className="w-16 h-16 rounded-2xl bg-gold-50 dark:bg-gold-900/20 flex items-center justify-center mb-4">
        <Hourglass className="w-8 h-8 text-gold-500" />
      </div>
      <h2 className="text-lg font-bold text-gray-900 dark:text-white">A classificação será divulgada em breve</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-sm">Enquanto isso, acompanhe os jogos e a tabela do campeonato.</p>
    </div>
  );
}

/** Classificação liberada pelo admin: geral até a rodada liberada ou de uma rodada, com as colunas da gestão. */
export function Tabela({ onAbrirParticipante, onRegras }: { onAbrirParticipante: AbrirParticipante; onRegras: () => void }) {
  const [rodada, setRodada] = useState('');
  const [ocultar, setOcultar] = useState(true);
  const params = new URLSearchParams();
  if (rodada) params.set('rodada', rodada);
  if (!ocultar) params.set('desistentes', 'mostrar');
  const { dados, carregando, erro, recarregar } = useRecurso<ClassificacaoComEliminacao>(`/classificacao?${params}`);

  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={4} />;
  if (!dados.liberada) return <TabelaEmBreve />;

  const geral = !dados.rodada;
  const podio = dados.itens.map(i => ({ ...i, participacaoId: idDoNome(i.nome), acertosVencedor: i.acertos })) as unknown as ItemRanking[];
  return (
    <section className={`${cartao} overflow-hidden`} aria-labelledby="titulo-tabela">
      <Titulo icone={<Trophy className="w-5 h-5" />} titulo="Classificação"
        extra={<Badge color="green">Até a {dados.ate.nome}</Badge>} />
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <select value={rodada} onChange={e => setRodada(e.target.value)} aria-label="Filtrar classificação"
          className="px-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
          <option value="">Geral (até a {dados.ate.nome})</option>
          {[...dados.rodadas].reverse().map(r => <option key={r.numero} value={r.numero}>Somente a {r.nome}</option>)}
        </select>
        <div className="flex items-center justify-between gap-3 sm:ml-auto">
          <Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" />
          <button onClick={onRegras} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/30">
            <HelpCircle className="w-4 h-4" /> Pontuação
          </button>
        </div>
      </div>
      <div className={`transition-opacity ${carregando ? 'opacity-60' : ''}`}>
        {!!dados.eliminadosOcultos && <p className="px-5 py-3 text-xs text-gray-500 dark:text-gray-400">{dados.eliminadosOcultos} participantes eliminados nas fases anteriores não aparecem no ranking.</p>}
        {dados.itens.length === 0 ? (
          <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação ainda" />
        ) : (
          <>
            <div className="p-5 bg-gradient-to-b from-brand-50 to-transparent dark:from-brand-900/20"><Podio ranking={podio} /></div>
            <TabelaClassificacao geral={geral} celular="colunas" colunas={['total', 'bonus', 'variacao']}
              dicaVariacao={dados.variacaoReferencia ? `Variação em relação à ${dados.variacaoReferencia}` : undefined}
              onAbrir={l => onAbrirParticipante({ ref: String(l.chave), nome: l.nome })}
              itens={dados.itens.map(i => ({ chave: i.ref, avatarId: idDoNome(i.nome), nome: i.nome, status: i.status,
                posicao: i.posicao, pontos: i.pontos, pontosPalpites: i.pontosPalpites, bonus: i.bonus,
                bonusPrimeiroGol: i.bonusPrimeiroGol, cravadas: i.cravadas, acertos: i.acertos, variacao: i.variacao }))} />
          </>
        )}
      </div>
    </section>
  );
}
