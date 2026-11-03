import { lazy, Suspense } from 'react';
import { Award, ChevronRight, Flame, Star, Target, TrendingUp } from 'lucide-react';
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
  /** Pontos de bônus da rodada (1º gol e créditos da planilha), já incluídos em pontos. */
  bonus?: number;
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
  /** Abre a rodada (palpites da pessoa nela); sem isso, o histórico é só leitura. */
  onAbrirRodada?: (ponto: PontoEvolucao) => void;
}

/** "+2 de bônus" com estrela, para o histórico e o gráfico. */
export function SeloBonus({ pontos }: { pontos: number }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-gold-700 dark:text-gold-300 font-semibold">
      <Star className="w-3 h-3 fill-current" aria-hidden />+{pontos} de bônus
    </span>
  );
}

/** Cartões de desempenho, melhor rodada, gráfico por rodada e histórico (gestão e página pública). */
export function PainelDesempenho({ resumo, evolucao, carregando = false, erro, onTentar, semDados = 'Ainda não há resultados lançados.', onAbrirRodada }: Props) {
  const melhor = evolucao ? melhorRodada(evolucao) : null;
  const comBonus = evolucao ? evolucao.filter(e => e.participa && (e.bonus ?? 0) > 0) : [];
  const totalBonus = comBonus.reduce((soma, e) => soma + (e.bonus ?? 0), 0);
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

          {/* Em quais rodadas saíram os bônus (1º gol e créditos da planilha) */}
          <div className="p-4 rounded-xl border border-gray-100 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <Star className="w-4 h-4 text-gold-500 fill-current" aria-hidden />
              <h4 className="flex-1 text-sm font-semibold text-gray-700 dark:text-gray-300">Rodadas com bônus</h4>
              {totalBonus > 0 && <span className="text-xs font-bold text-gold-700 dark:text-gold-300">{totalBonus} pts</span>}
            </div>
            {comBonus.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {comBonus.map(e => {
                  const conteudo = <><span>{e.rodada}</span><span className="text-gold-700 dark:text-gold-300">+{e.bonus}</span></>;
                  const estilo = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gold-50 dark:bg-gold-900/30 text-gray-800 dark:text-gray-200 border border-gold-200/70 dark:border-gold-800/40';
                  return onAbrirRodada ? (
                    <button key={e.chave} type="button" onClick={() => onAbrirRodada(e)} title={`Abrir a ${e.rodada}`}
                      className={`${estilo} hover:bg-gold-100 dark:hover:bg-gold-900/50 transition-colors`}>{conteudo}</button>
                  ) : <span key={e.chave} className={estilo}>{conteudo}</span>;
                })}
              </div>
            ) : <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Nenhum bônus até agora.</p>}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Pontuação por rodada</h4>
            {evolucao.length ? (
              <Suspense fallback={<div className="h-[200px] rounded-lg bg-gray-50 dark:bg-gray-900 animate-pulse" />}>
                <GraficoPontos evolucao={evolucao} onAbrirRodada={onAbrirRodada} />
              </Suspense>
            ) : <p className="text-sm text-gray-400 py-8 text-center">{semDados}</p>}
          </div>

          {evolucao.length > 0 && (
            <div>
              <h4 className={`text-sm font-semibold text-gray-700 dark:text-gray-300 ${onAbrirRodada ? 'mb-1' : 'mb-3'}`}>Histórico por rodada</h4>
              {onAbrirRodada && <p className="text-xs text-gray-400 mb-3">Toque numa rodada para ver os palpites dela.</p>}
              <div className="space-y-2">
                {[...evolucao].reverse().map((h, i, lista) => {
                  const anterior = lista[i + 1];
                  const destaque = melhor && h.chave === melhor.rodada.chave;
                  const bonus = h.participa ? (h.bonus ?? 0) : 0;
                  const classe = `w-full text-left flex items-center gap-3 p-3 rounded-xl border ${destaque ? 'border-gold-300 dark:border-gold-700/60' : 'border-gray-100 dark:border-gray-800'} ${h.participa ? '' : 'opacity-60'}`;
                  const conteudo = (
                    <>
                      <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-600 dark:text-gray-400 shrink-0">{h.curto}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{h.participa ? `${h.palpites} ${h.palpites === 1 ? 'palpite lançado' : 'palpites lançados'}` : 'Fora desta rodada'}</p>
                        <p className="text-xs text-gray-400 flex items-center gap-1.5 flex-wrap">
                          {h.cravadas} {h.cravadas === 1 ? 'placar exato' : 'placares exatos'} · {h.posicao}º no geral
                          {anterior && <Variacao valor={anterior.posicao - h.posicao} />}
                        </p>
                        {bonus > 0 && <p className="text-xs mt-0.5"><SeloBonus pontos={bonus} /></p>}
                      </div>
                      {h.pontos !== null && <Badge color={h.cravadas > 0 ? 'green' : h.pontos > 0 ? 'yellow' : 'gray'}>{h.pontos} pts</Badge>}
                      {onAbrirRodada && <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" aria-hidden />}
                    </>
                  );
                  return onAbrirRodada ? (
                    <button key={h.chave} type="button" onClick={() => onAbrirRodada(h)} aria-label={`Abrir a ${h.rodada}`}
                      className={`${classe} hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors`}>{conteudo}</button>
                  ) : <div key={h.chave} className={classe}>{conteudo}</div>;
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
