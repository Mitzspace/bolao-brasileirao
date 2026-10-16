import { Fragment, useEffect, useState } from 'react';
import { BookOpen, Check, ChevronDown, ChevronRight, Globe, Share2, Shield, Trophy, Users } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { Variacao } from '@/components/ui/Variacao';
import { useRecurso } from '@/lib/useRecurso';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EditorRegras, paraEdicao, validarRegras, type RegrasEditaveis } from './EditorRegras';
import type { ClassificacaoBolaoApi } from '@/types';
import { CompartilharClassificacao } from './CompartilharClassificacao';
import { CORES_MEDALHA, Podio } from './Podio';
import { LinkPublico } from './LinkPublico';

type Aba = 'classificacao' | 'regras' | 'publico';

export function statusBolao(status: string) {
  return status === 'ativo' ? { label: 'Ativo', color: 'green' as const }
    : { label: status.charAt(0).toUpperCase() + status.slice(1), color: 'gray' as const };
}

/** Detalhe do bolão no estilo do Bolt: classificação completa (geral ou por rodada) e regras. */
export function DetalheBolao({ bolaoId, onTrocar, onVoltar }: { bolaoId: number; onTrocar: (id: number) => void; onVoltar: () => void }) {
  const [aba, setAba] = useState<Aba>('classificacao');
  const [rodadaId, setRodadaId] = useState('');
  // Desistentes ficam ocultos por padrão (pedido do bolão); o switch mostra quando preciso.
  const [ocultar, setOcultar] = useState(true);
  const [compartilhar, setCompartilhar] = useState(false);
  const [aberta, setAberta] = useState<number | null>(null);
  const params = new URLSearchParams();
  if (rodadaId) params.set('rodada_id', rodadaId);
  if (ocultar) params.set('ocultar_desistentes', '1');
  const { dados, carregando, erro, recarregar } = useRecurso<ClassificacaoBolaoApi>(`/boloes/${bolaoId}/classificacao?${params}`);

  const trocar = (id: number) => { setRodadaId(''); onTrocar(id); };
  const geral = !dados?.rodadaId;
  const lider = dados?.ranking[0];
  const ativos = dados?.ranking.filter(i => i.status === 'ativo').length ?? 0;
  const status = dados ? statusBolao(dados.bolao.status) : null;
  const abas: { id: Aba; label: string; icon: typeof Trophy }[] = [
    { id: 'classificacao', label: 'Classificação', icon: Trophy },
    { id: 'regras', label: 'Regras', icon: BookOpen },
    { id: 'publico', label: 'Link público', icon: Globe },
  ];

  return (
    <div>
      <Header
        title={dados?.bolao.nome ?? 'Bolão'}
        subtitle={dados ? `${dados.bolao.campeonato} ${dados.bolao.ano ?? ''}` : undefined}
        actions={dados ? (
          <button onClick={() => setCompartilhar(true)} aria-label="Compartilhar classificação"
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-semibold hover:bg-brand-100 transition-colors">
            <Share2 className="w-4 h-4" /><span className="hidden sm:inline">Compartilhar</span>
          </button>
        ) : undefined}
      />

      <div className="p-4 md:p-8 pb-28 md:pb-8 space-y-5">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={4} />}

        {dados && status && (
          <>
            {dados.campeonatosDoBolao.length > 1 && (
              <div className="flex flex-wrap gap-2" role="group" aria-label="Campeonatos do bolão">
                {dados.campeonatosDoBolao.map(c => (
                  <button key={c.bolaoId} onClick={() => trocar(c.bolaoId)} aria-pressed={c.bolaoId === bolaoId}
                    className={`px-3.5 py-2 rounded-xl text-sm font-semibold transition-colors ${c.bolaoId === bolaoId ? 'bg-brand-600 text-white shadow-sm' : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-brand-300'}`}>
                    {c.nome} {c.ano ?? ''}
                  </button>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-white dark:bg-gray-900 rounded-xl p-4 border border-gray-100 dark:border-gray-800">
                <p className="text-xs text-gray-400">Participantes</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{ativos}</p>
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-4 border border-gray-100 dark:border-gray-800 min-w-0">
                <p className="text-xs text-gray-400">Líder</p>
                <p className="text-lg font-bold text-gold-600 dark:text-gold-400 truncate">{lider ? lider.nome : '—'}</p>
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-4 border border-gray-100 dark:border-gray-800">
                <p className="text-xs text-gray-400">Pontos do líder</p>
                <p className="text-lg font-bold text-brand-600 dark:text-brand-400">{lider ? lider.pontos : '—'}</p>
              </div>
              <div className="bg-white dark:bg-gray-900 rounded-xl p-4 border border-gray-100 dark:border-gray-800">
                <p className="text-xs text-gray-400 mb-1">Status</p>
                <Badge color={status.color}>{status.label}</Badge>
              </div>
            </div>

            <div role="tablist" className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 overflow-x-auto no-scrollbar w-fit max-w-full">
              {abas.map(t => {
                const Icon = t.icon;
                return (
                  <button key={t.id} role="tab" aria-selected={aba === t.id} onClick={() => setAba(t.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${aba === t.id ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500'}`}>
                    <Icon className="w-4 h-4" />{t.label}
                  </button>
                );
              })}
            </div>

            {aba === 'classificacao' && (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden animate-slide-up">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                  <select value={rodadaId} onChange={e => setRodadaId(e.target.value)} aria-label="Classificação"
                    className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
                    <option value="">Classificação geral</option>
                    {dados.rodadas.map(r => <option key={r.id} value={r.id}>Somente a {r.nome}</option>)}
                  </select>
                  <div className="sm:ml-auto"><Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" /></div>
                </div>

                {dados.ranking.length === 0 ? (
                  <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação" description="Cadastre participantes e lance resultados para ver a classificação." />
                ) : (
                  <>
                    <div className="p-5 bg-gradient-to-b from-brand-50 to-transparent dark:from-brand-900/20">
                      <Podio ranking={dados.ranking} />
                    </div>
                    <div className="overflow-x-auto scrollbar-thin">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-100 dark:border-gray-800">
                            <th className="text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase">#</th>
                            <th className="text-left py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase">Participante</th>
                            <th className="hidden sm:table-cell text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase" title="Pontos dos placares, sem o bônus">Pontos</th>
                            <th className="hidden sm:table-cell text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase" title="Bônus de primeiro gol">Bônus</th>
                            <th className="text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase" title="Placares exatos">Cravadas</th>
                            <th className="hidden sm:table-cell text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase" title="Vencedor ou empate correto, sem placar exato">Resultados</th>
                            <th className="text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase">Total</th>
                            {geral && <th className="text-center py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase" title={dados.variacaoReferencia ? `Variação após a ${dados.variacaoReferencia}` : undefined}>Var.</th>}
                            <th className="sm:hidden w-8"><span className="sr-only">Detalhes</span></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                          {dados.ranking.map((p, i) => {
                            const expandida = aberta === p.participacaoId;
                            // Bônus = primeiro gol (lançado no sistema + créditos importados); Pontos + Bônus = Total.
                            const bonus = p.bonus + p.bonusPrimeiroGol;
                            const pontosPlacar = p.pontosPalpites - p.bonusPrimeiroGol;
                            return (
                            <Fragment key={p.participacaoId}>
                            <tr onClick={() => setAberta(expandida ? null : p.participacaoId)} aria-expanded={expandida}
                              className={`hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer sm:cursor-default ${p.status !== 'ativo' ? 'opacity-70' : ''}`}>
                              <td className="py-3 px-1.5 sm:px-3 text-center">
                                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mx-auto ${i < 3 ? 'text-white' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
                                  style={i < 3 ? { backgroundColor: CORES_MEDALHA[i] } : {}}>{p.posicao ?? i + 1}</div>
                              </td>
                              <td className="py-3 px-1.5 sm:px-3">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="hidden min-[400px]:block"><Avatar nome={p.nome} id={p.participacaoId} /></span>
                                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[7.5rem] sm:max-w-none">{p.nome}</span>
                                  {p.status === 'desistente' && <Badge color="yellow" size="sm">Desistente</Badge>}
                                </div>
                              </td>
                              <td className="hidden sm:table-cell py-3 px-1.5 sm:px-3 text-center text-sm text-gray-600 dark:text-gray-400">
                                {pontosPlacar}
                              </td>
                              <td className="hidden sm:table-cell py-3 px-1.5 sm:px-3 text-center text-sm">{bonus > 0 ? <span className="font-bold text-gold-600">+{bonus}</span> : <span className="text-gray-400">0</span>}</td>
                              <td className="py-3 px-1.5 sm:px-3 text-center text-sm text-gray-600 dark:text-gray-400">{p.cravadas}</td>
                              <td className="hidden sm:table-cell py-3 px-1.5 sm:px-3 text-center text-sm text-gray-600 dark:text-gray-400">{p.acertosVencedor}</td>
                              <td className="py-3 px-1.5 sm:px-3 text-center"><span className="text-sm font-bold text-brand-600 dark:text-brand-400">{p.pontos}</span></td>
                              {geral && <td className="py-3 px-1.5 sm:px-3 text-center"><Variacao valor={p.variacao} /></td>}
                              <td className="sm:hidden pr-2 text-gray-400">
                                <ChevronDown className={`w-4 h-4 transition-transform ${expandida ? 'rotate-180' : ''}`} aria-label={expandida ? 'Recolher detalhes' : 'Ver detalhes'} />
                              </td>
                            </tr>
                            {expandida && (
                              <tr className="sm:hidden bg-gray-50/70 dark:bg-gray-800/40">
                                <td colSpan={geral ? 6 : 5} className="px-3 py-3 max-w-0">
                                  <dl className="grid grid-cols-2 gap-2 text-xs animate-fade-in">
                                    {[
                                      ['Pontos', pontosPlacar, 'dos placares'],
                                      ['Bônus', bonus > 0 ? `+${bonus}` : '0', 'primeiro gol'],
                                      ['Cravadas', p.cravadas, 'placar exato'],
                                      ['Resultados', p.acertosVencedor, 'vencedor ou empate'],
                                    ].map(([rotulo, valor, dica]) => (
                                      <div key={rotulo} className="min-w-0 rounded-lg bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 px-3 py-2">
                                        <dt className="text-gray-400">{rotulo}</dt>
                                        <dd className="text-sm font-bold text-gray-900 dark:text-white">{valor}<span className="block text-[10px] font-normal text-gray-400 truncate">{dica}</span></dd>
                                      </div>
                                    ))}
                                  </dl>
                                </td>
                              </tr>
                            )}
                            </Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="px-5 py-3 text-xs text-gray-400 border-t border-gray-100 dark:border-gray-800"><span className="sm:hidden">Toque em um participante para ver pontos e bônus. </span>Total = pontos + bônus. Desempate: total, cravadas, resultados e nome.</p>
                  </>
                )}
              </div>
            )}

            {aba === 'regras' && <AbaRegras bolaoId={bolaoId} dados={dados} onSalvo={recarregar} />}
            {aba === 'publico' && <LinkPublico key={bolaoId} bolaoId={bolaoId} />}

            <button onClick={onVoltar} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
              <ChevronRight className="w-4 h-4 rotate-180" /> Voltar para bolões
            </button>

            <CompartilharClassificacao dados={dados} aberto={compartilhar} onClose={() => setCompartilhar(false)} />
          </>
        )}
      </div>
    </div>
  );
}


/** Regras do bolão, editáveis; a mudança vale para todas as rodadas (retroativa). */
function AbaRegras({ bolaoId, dados, onSalvo }: { bolaoId: number; dados: ClassificacaoBolaoApi; onSalvo: () => Promise<void> }) {
  const showToast = useToast();
  const [valores, setValores] = useState<RegrasEditaveis>(() => paraEdicao(dados.regras));
  const [confirmar, setConfirmar] = useState(false);
  useEffect(() => { setValores(paraEdicao(dados.regras)); }, [dados.regras]);
  const { regras, erro } = validarRegras(valores);
  const alterado = JSON.stringify(valores) !== JSON.stringify(paraEdicao(dados.regras));

  const salvar = async () => {
    try {
      const r = await api.put<{ mensagem: string }>(`/boloes/${bolaoId}/regras`, regras);
      showToast(r.mensagem);
      await onSalvo();
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar as regras.', 'error');
      throw e;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-6 animate-slide-up">
      <h3 className="font-bold text-gray-900 dark:text-white mb-1">Regras de pontuação</h3>
      <p className="text-sm text-gray-400 mb-4">Valem só para este bolão e para todas as rodadas, inclusive as já jogadas.</p>
      <EditorRegras valores={valores} onChange={setValores} />
      {erro && <p role="alert" className="mt-3 text-sm text-red-600">{erro}</p>}
      <div className="mt-4 p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm text-gray-600 dark:text-gray-300 flex gap-2">
        <Shield className="w-4 h-4 mt-0.5 shrink-0 text-gray-400" />
        <p>Palpite marcado como "não enviou" ou "fora do prazo" vale 0. {dados.regras.politicaEntrada === 'fora_da_conta'
          ? 'Rodadas anteriores à entrada de um participante ficam fora da conta.'
          : 'Rodadas anteriores à entrada de um participante contam com zero pontos.'} Créditos de bônus importados do histórico não mudam.</p>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <button onClick={() => setConfirmar(true)} disabled={!regras || !alterado}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm transition-colors disabled:opacity-50">
          <Check className="w-4 h-4" /> Salvar regras
        </button>
        {alterado && <button onClick={() => setValores(paraEdicao(dados.regras))} className="px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Desfazer</button>}
      </div>
      <ConfirmDialog open={confirmar} onClose={() => setConfirmar(false)} onConfirm={salvar}
        title="Recalcular a pontuação?"
        message="As novas regras valem para todas as rodadas, inclusive as já jogadas. A classificação, a grade e o gráfico de todos os participantes serão recalculados. Nenhum palpite é alterado e dá para voltar aos valores antigos depois."
        confirmLabel="Salvar e recalcular" />
    </div>
  );
}
