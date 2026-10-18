import { useCallback, useEffect, useState } from 'react';
import { BookOpen, Check, ChevronRight, Globe, Lock, Pencil, Share2, Shield, Trophy, Users } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { Drawer } from '@/components/ui/Drawer';
import { DesempenhoParticipante } from '@/components/participantes/DesempenhoParticipante';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { useRecurso } from '@/lib/useRecurso';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EditorRegras, paraEdicao, validarRegras, type RegrasEditaveis } from './EditorRegras';
import type { ClassificacaoBolaoApi, StatusBolao } from '@/types';
import { CompartilharClassificacao } from './CompartilharClassificacao';
import { Podio } from './Podio';
import { TabelaClassificacao } from './TabelaClassificacao';
import { LinkPublico } from './LinkPublico';
import { EditarBolao } from './EditarBolao';

type Aba = 'classificacao' | 'regras' | 'publico';
type ClassificacaoComEliminacao = ClassificacaoBolaoApi & { eliminadosOcultos?: number };

/** Selo de situação: verde (em andamento), azul (finalizado) ou vermelho (desistido). */
export function statusBolao(status: StatusBolao | string) {
  if (status === 'finalizado') return { label: 'Finalizado', color: 'blue' as const };
  if (status === 'desistido') return { label: 'Desistido', color: 'red' as const };
  return { label: 'Em andamento', color: 'green' as const };
}

/** Detalhe do bolão no estilo do Bolt: classificação completa (geral ou por rodada) e regras. */
export function DetalheBolao({ bolaoId, onTrocar, onVoltar }: { bolaoId: number; onTrocar: (id: number) => void; onVoltar: () => void }) {
  const [aba, setAba] = useState<Aba>('classificacao');
  const [rodadaId, setRodadaId] = useState('');
  // Desistentes ficam ocultos por padrão (pedido do bolão); o switch mostra quando preciso.
  const [ocultar, setOcultar] = useState(true);
  const [compartilhar, setCompartilhar] = useState(false);
  const [editando, setEditando] = useState(false);
  const [desempenho, setDesempenho] = useState<{ id: number; nome: string } | null>(null);
  const fecharDesempenho = useCallback(() => setDesempenho(null), []);
  const params = new URLSearchParams();
  if (rodadaId) params.set('rodada_id', rodadaId);
  if (ocultar) params.set('ocultar_desistentes', '1');
  const { dados, carregando, erro, recarregar } = useRecurso<ClassificacaoComEliminacao>(`/boloes/${bolaoId}/classificacao?${params}`);

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
          <>
            <button onClick={() => setEditando(true)} aria-label="Editar bolão"
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <Pencil className="w-4 h-4" /><span className="hidden sm:inline">Editar</span>
            </button>
            <button onClick={() => setCompartilhar(true)} aria-label="Compartilhar classificação"
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-semibold hover:bg-brand-100 transition-colors">
              <Share2 className="w-4 h-4" /><span className="hidden sm:inline">Compartilhar</span>
            </button>
          </>
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

            <div className="flex flex-wrap items-center gap-2">
              <Badge color={status.color} size="md">{status.label}</Badge>
              {dados.bolao.status !== 'ativo' && (
                <span className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                  <Lock className="w-4 h-4" /> Somente consulta. Para alterar, volte para "Em andamento" em Editar.
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2 sm:gap-3">
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

                {!!dados.eliminadosOcultos && <p className="px-5 py-3 text-xs text-gray-500 dark:text-gray-400">{dados.eliminadosOcultos} participantes eliminados nas fases anteriores não aparecem no ranking.</p>}
                {dados.ranking.length === 0 ? (
                  <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação" description="Cadastre participantes e lance resultados para ver a classificação." />
                ) : (
                  <>
                    <div className="p-5 bg-gradient-to-b from-brand-50 to-transparent dark:from-brand-900/20">
                      <Podio ranking={dados.ranking} />
                    </div>
                    <TabelaClassificacao geral={geral}
                      onAbrir={l => setDesempenho({ id: Number(l.chave), nome: l.nome })}
                      dicaVariacao={dados.variacaoReferencia ? `Variação após a ${dados.variacaoReferencia}` : undefined}
                      itens={dados.ranking.map(p => ({ chave: p.participacaoId, avatarId: p.participacaoId, nome: p.nome, status: p.status,
                        posicao: p.posicao, pontos: p.pontos, pontosPalpites: p.pontosPalpites, bonus: p.bonus,
                        bonusPrimeiroGol: p.bonusPrimeiroGol, cravadas: p.cravadas, acertos: p.acertosVencedor, variacao: p.variacao }))} />
                  </>
                )}
              </div>
            )}

            {aba === 'regras' && <AbaRegras bolaoId={bolaoId} dados={dados} onSalvo={recarregar} />}
            {aba === 'publico' && <LinkPublico key={bolaoId} bolaoId={bolaoId} />}

            <button onClick={onVoltar} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
              <ChevronRight className="w-4 h-4 rotate-180" /> Voltar para bolões
            </button>

            <EditarBolao bolao={dados.bolao} aberto={editando} onClose={() => setEditando(false)} onSalvo={recarregar} />
            <CompartilharClassificacao dados={dados} aberto={compartilhar} onClose={() => setCompartilhar(false)} />
            <Drawer open={!!desempenho} onClose={fecharDesempenho} title="Desempenho do participante" width="max-w-xl">
              {desempenho && <DesempenhoParticipante key={`${bolaoId}-${desempenho.id}`} bolaoId={bolaoId} participacaoId={desempenho.id} nome={desempenho.nome} />}
            </Drawer>
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
