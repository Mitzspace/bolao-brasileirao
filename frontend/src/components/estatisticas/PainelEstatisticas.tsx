import { useState } from 'react';
import { ChevronDown, Info, Trophy, Users } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import type { EstatisticasApi, LinhaEstatisticas } from '@/types';

const cartao = 'bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800';

function numero(valor: number | null | undefined, casas = 1) {
  return valor === null || valor === undefined ? '—' : valor.toLocaleString('pt-BR', { maximumFractionDigits: casas });
}

const AVISOS: Partial<Record<EstatisticasApi['situacao'], string>> = {
  sem_resultados: 'A estimativa começa quando houver pontos: sem isso, não há diferença entre os participantes para comparar.',
  sem_participantes: 'Nenhum participante ativo na disputa.',
  sem_jogos: 'Todos os jogos cadastrados já têm resultado: quem lidera a classificação fica com 100%. Se novas fases forem importadas, a disputa volta a ser estimada.',
  encerrado: 'Bolão finalizado: não há mais o que estimar. Veja abaixo o desempenho de cada participante.',
  desistido: 'Este bolão foi marcado como desistido, então não há ganhador a estimar. Veja abaixo o desempenho de cada participante.',
};

/** Texto da chance: nunca afirma 0% ou 100% enquanto a matemática ainda deixa a disputa aberta. */
function textoChance(l: LinhaEstatisticas, simulada: boolean, outrosNaDisputa: boolean) {
  if (l.probabilidade === null) return '—';
  if (simulada && l.probabilidade === 0 && !l.semChance) return '<0,1%';
  if (simulada && l.probabilidade === 100 && outrosNaDisputa) return '>99,9%';
  return `${numero(l.probabilidade)}%`;
}

function Linha({ linha, simulada, outrosNaDisputa, aberta, onAlternar, onAbrir }: {
  linha: LinhaEstatisticas; simulada: boolean; outrosNaDisputa: boolean; aberta: boolean; onAlternar: () => void;
  onAbrir: () => void;
}) {
  const d = linha.desempenho;
  const detalhes: [string, string, string?][] = [
    ...(simulada ? [
      ['Chance de pódio', `${numero(linha.chancePodio)}%`, 'entre os 3 primeiros'],
      ['Pontos projetados', numero(linha.pontosProjetados, 0), 'média das simulações'],
    ] as [string, string, string][] : []),
    ['Máximo possível', numero(linha.pontosMaximos, 0), 'acertando tudo'],
    ['Aproveitamento', d.aproveitamento === null ? '—' : `${numero(d.aproveitamento)}%`, 'dos pontos de placar'],
    ['Média por jogo', numero(d.mediaPorJogo, 2), `em ${d.jogos} ${d.jogos === 1 ? 'jogo' : 'jogos'}`],
    ['Últimas rodadas', numero(d.mediaRecente, 2), 'por jogo, até 5 rodadas'],
    ['Cravadas', String(linha.cravadas), 'placares exatos'],
    ['Resultados', String(linha.acertos), 'vencedor ou empate'],
    ['Melhor rodada', d.melhorRodada ? `${d.melhorRodada.pontos} pts` : '—', d.melhorRodada?.nome],
  ];
  return (
    <li>
      <button type="button" onClick={onAlternar} aria-expanded={aberta}
        className="w-full text-left px-4 sm:px-5 py-3.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
        <div className="flex items-center gap-3 min-w-0">
          <span className="hidden min-[400px]:block shrink-0"><Avatar nome={linha.nome} id={linha.participacaoId} /></span>
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">{linha.nome}</span>
              {linha.semChance && <Badge color="gray" size="sm">Sem chance</Badge>}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {linha.posicao}º · {linha.pontos} pts{linha.distanciaLider > 0 ? ` · a ${linha.distanciaLider} do líder` : linha.posicao === 1 ? ' · líder' : ' · empatado com o líder'}
            </p>
          </div>
          <span className="text-lg font-bold tabular-nums text-gray-900 dark:text-white shrink-0">{textoChance(linha, simulada, outrosNaDisputa)}</span>
          <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${aberta ? 'rotate-180' : ''}`} aria-hidden="true" />
        </div>
        {linha.probabilidade !== null && (
          <div className="mt-2 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden" aria-hidden="true">
            <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.min(100, linha.probabilidade)}%` }} />
          </div>
        )}
      </button>
      {aberta && (
        <div className="px-4 sm:px-5 pb-4 animate-fade-in">
          <dl className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {detalhes.map(([rotulo, valor, dica]) => (
              <div key={rotulo} className="min-w-0 rounded-xl bg-gray-50 dark:bg-gray-800/60 px-3 py-2">
                <dt className="text-xs text-gray-500 dark:text-gray-400">{rotulo}</dt>
                <dd className="text-sm font-bold text-gray-900 dark:text-white tabular-nums">{valor}
                  {dica && <span className="block text-[11px] font-normal text-gray-500 dark:text-gray-400 truncate" title={dica}>{dica}</span>}
                </dd>
              </div>
            ))}
          </dl>
          <button type="button" onClick={onAbrir} className="mt-2 text-xs font-semibold text-brand-700 dark:text-brand-300 hover:underline">
            Ver desempenho por rodada
          </button>
        </div>
      )}
    </li>
  );
}

/** Possíveis ganhadores: a chance é sempre apresentada como estimativa. */
export function PainelEstatisticas({ dados, onAbrir }: { dados: EstatisticasApi; onAbrir: (linha: LinhaEstatisticas) => void }) {
  const [aberta, setAberta] = useState<number | null>(null);
  const simulada = dados.situacao === 'simulada';
  const favorito = dados.participantes[0];
  const temChance = !!favorito && favorito.probabilidade !== null;
  const naDisputa = dados.participantes.filter(l => !l.semChance).length;
  const fora = [
    dados.eliminados > 0 && `${dados.eliminados} ${dados.eliminados === 1 ? 'eliminado' : 'eliminados'} em cortes já concluídos`,
    dados.desistentes > 0 && `${dados.desistentes} ${dados.desistentes === 1 ? 'desistente' : 'desistentes'}`,
  ].filter(Boolean).join(' e ');

  return (
    <div className="space-y-5">
      {simulada ? (
        <div className="flex items-start gap-3 rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50 dark:bg-blue-900/20 p-4 text-sm text-blue-900 dark:text-blue-100">
          <Info className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="space-y-1 min-w-0">
            <p><strong className="font-semibold">É uma estimativa, não uma previsão.</strong> Simulamos {numero(dados.simulacoes, 0)} vezes {dados.jogosRestantes === 1 ? 'o jogo que falta' : `os ${dados.jogosRestantes} jogos que faltam`}, repetindo o histórico de acertos de cada participante e as regras do bolão{dados.copa ? ', inclusive pênaltis e cortes de eliminação' : ''}.</p>
            {dados.copa && <p className="text-xs opacity-80">Só entram os jogos já cadastrados: fases ainda não importadas não contam.</p>}
            {dados.poucosDados && <p className="text-xs font-semibold">Ainda há poucos jogos encerrados ({dados.jogosEncerrados}): a estimativa pode mudar bastante.</p>}
          </div>
        </div>
      ) : (
        <div role="status" className="flex items-start gap-3 rounded-2xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 p-4 text-sm text-gray-700 dark:text-gray-200">
          <Info className="w-5 h-5 shrink-0 mt-0.5" /><p>{AVISOS[dados.situacao]}</p>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <div className={`${cartao} col-span-2 lg:col-span-1 p-4 min-w-0`}>
          <p className="text-xs text-gray-500 dark:text-gray-400">{simulada ? 'Favorito' : temChance ? 'Ganhador' : 'Líder'}</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white truncate flex items-center gap-2">
            <Trophy className="w-4 h-4 text-gold-500 shrink-0" /><span className="truncate">{favorito?.nome ?? '—'}</span>
          </p>
          {temChance && <p className="text-xs text-gray-500 dark:text-gray-400">{textoChance(favorito, simulada, naDisputa > 1)} de chance</p>}
        </div>
        <div className={`${cartao} p-4`}>
          <p className="text-xs text-gray-500 dark:text-gray-400">Jogos restantes</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">{dados.jogosRestantes}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{dados.rodadasRestantes} {dados.rodadasRestantes === 1 ? 'rodada' : 'rodadas'}</p>
        </div>
        <div className={`${cartao} p-4`}>
          <p className="text-xs text-gray-500 dark:text-gray-400">Na disputa</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">{naDisputa}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">de {dados.participantes.length} {dados.participantes.length === 1 ? 'participante' : 'participantes'}</p>
        </div>
      </div>

      <section className={`${cartao} overflow-hidden`} aria-labelledby="titulo-ganhadores">
        <div className="px-4 sm:px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 id="titulo-ganhadores" className="font-bold text-gray-900 dark:text-white">{temChance ? 'Chance de ganhar o bolão' : 'Desempenho dos participantes'}</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Toque em um participante para ver o desempenho.</p>
        </div>
        {dados.participantes.length === 0 ? (
          <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na disputa" />
        ) : (
          <ul className="divide-y divide-gray-50 dark:divide-gray-800">
            {dados.participantes.map(l => (
              <Linha key={l.participacaoId} linha={l} simulada={simulada} outrosNaDisputa={naDisputa > 1}
                aberta={aberta === l.participacaoId} onAlternar={() => setAberta(aberta === l.participacaoId ? null : l.participacaoId)}
                onAbrir={() => onAbrir(l)} />
            ))}
          </ul>
        )}
        {fora && <p className="px-4 sm:px-5 py-3 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-800">Fora da disputa: {fora}.</p>}
      </section>
    </div>
  );
}
