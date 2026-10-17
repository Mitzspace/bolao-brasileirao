import { lazy, Suspense } from 'react';
import { Award, Flame, Target, TrendingUp } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Variacao } from '@/components/ui/Variacao';

const GraficoPontos = lazy(() => import('./GraficoPontos'));

/** Uma rodada na evolução do participante (gestão e página pública). */
export interface PontoEvolucao {
  chave: string | number;
  rodada: string;
  curto: string;
  /** null: fora desta rodada (entrou depois ou desistiu). */
  pontos: number | null;
  cravadas: number;
  palpites: number;
  acumulado: number;
  posicao: number;
  participa: boolean;
}

export interface ResumoDesempenho { pontos: number; cravadas: number; posicao: number | null; variacao: number | null }

/** Melhor rodada: mais pontos; no empate, a mais antiga (e quantas empataram). */
export function melhorRodada(evolucao: PontoEvolucao[]) {
  let melhor: PontoEvolucao | null = null;
  for (const e of evolucao) if (e.pontos !== null && (melhor === null || e.pontos > (melhor.pontos ?? -1))) melhor = e;
  if (!melhor || !melhor.pontos) return null;
  const empates = evolucao.filter(e => e.pontos === melhor!.pontos).length - 1;
  return { rodada: melhor, empates };
}

interface Props {
  resumo: ResumoDesempenho;
  evolucao: PontoEvolucao[] | null;
  carregando?: boolean;
  erro?: string | null;
  onTentar?: () => void;
  /** Texto quando ainda não há rodadas com resultado (ou divulgadas). */
  semDados?: string;
}

/** Cartões de desempenho, melhor rodada, gráfico por rodada e histórico (gestão e página pública). */
export function PainelDesempenho({ resumo, evolucao, carregando = false, erro, onTentar, semDados = 'Ainda não há resultados lançados.' }: Props) {
  const melhor = evolucao ? melhorRodada(evolucao) : null;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-xl bg-brand-50 dark:bg-brand-900/20 text-center">
          <TrendingUp className="w-5 h-5 text-brand-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-gray-900 dark:text-white">{resumo.pontos}</p>
          <p className="text-xs text-gray-400">Pontos totais</p>
        </div>
        <div className="p-3 rounded-xl bg-gold-50 dark:bg-gold-900/20 text-center">
          <Award className="w-5 h-5 text-gold-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-gray-900 dark:text-white">{resumo.cravadas}</p>
          <p className="text-xs text-gray-400">Placares exatos</p>
        </div>
        <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-center">
          <Target className="w-5 h-5 text-blue-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-gray-900 dark:text-white flex items-center justify-center gap-1.5">
            {resumo.posicao ? `${resumo.posicao}º` : '—'} <Variacao valor={resumo.variacao} />
          </p>
          <p className="text-xs text-gray-400">Posição</p>
        </div>
      </div>

      {erro && <ErroCarga mensagem={erro} onTentar={onTentar ?? (() => undefined)} />}
      {!evolucao && carregando && <Carregando linhas={3} />}
      {evolucao && (
        <>
          {/* Melhor rodada (item visível na gestão e no link público) */}
          <div className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-gold-50 to-white dark:from-gold-900/20 dark:to-gray-900 border border-gold-200/70 dark:border-gold-800/40">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-gold-400 to-gold-600 text-white flex items-center justify-center shrink-0">
              <Flame className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gold-700 dark:text-gold-300 uppercase tracking-wide">Melhor rodada</p>
              {melhor ? (
                <>
                  <p className="text-sm font-bold text-gray-900 dark:text-white truncate">{melhor.rodada.rodada}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {melhor.rodada.cravadas} {melhor.rodada.cravadas === 1 ? 'placar exato' : 'placares exatos'}
                    {melhor.empates > 0 && ` · empatada com ${melhor.empates} ${melhor.empates === 1 ? 'outra rodada' : 'outras rodadas'}`}
                  </p>
                </>
              ) : <p className="text-sm text-gray-500 dark:text-gray-400">Ainda sem pontos em nenhuma rodada.</p>}
            </div>
            {melhor && (
              <div className="text-right shrink-0">
                <p className="text-2xl font-extrabold text-gold-600 dark:text-gold-400 leading-none">{melhor.rodada.pontos}</p>
                <p className="text-[11px] text-gray-400">pontos</p>
              </div>
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Pontuação por rodada</h4>
            {evolucao.length ? (
              <Suspense fallback={<div className="h-[200px] rounded-lg bg-gray-50 dark:bg-gray-900 animate-pulse" />}>
                <GraficoPontos evolucao={evolucao} />
              </Suspense>
            ) : <p className="text-sm text-gray-400 py-8 text-center">{semDados}</p>}
          </div>

          {evolucao.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Histórico por rodada</h4>
              <div className="space-y-2">
                {[...evolucao].reverse().map((h, i, lista) => {
                  const anterior = lista[i + 1];
                  const destaque = melhor && h.chave === melhor.rodada.chave;
                  return (
                    <div key={h.chave} className={`flex items-center gap-3 p-3 rounded-xl border ${destaque ? 'border-gold-300 dark:border-gold-700/60' : 'border-gray-100 dark:border-gray-800'} ${h.participa ? '' : 'opacity-60'}`}>
                      <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-600 dark:text-gray-400 shrink-0">{h.curto}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{h.participa ? `${h.palpites} ${h.palpites === 1 ? 'palpite lançado' : 'palpites lançados'}` : 'Fora desta rodada'}</p>
                        <p className="text-xs text-gray-400 flex items-center gap-1.5 flex-wrap">
                          {h.cravadas} {h.cravadas === 1 ? 'placar exato' : 'placares exatos'} · {h.posicao}º no geral
                          {anterior && <Variacao valor={anterior.posicao - h.posicao} />}
                        </p>
                      </div>
                      {h.pontos !== null && <Badge color={h.cravadas > 0 ? 'green' : h.pontos > 0 ? 'yellow' : 'gray'}>{h.pontos} pts</Badge>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
