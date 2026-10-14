import { useState } from 'react';
import { Calendar, Check, Clock, Grid3x3, ListChecks, Lock, LockOpen, Medal, Pencil, Plus, Star, Target, Trash2, Trophy, Users } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Input, Select, Switch } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { useToast } from '@/components/ui/Toast';
import { useApp } from '@/context/AppContext';
import { SeletorRodadas } from '@/components/rodadas/SeletorRodadas';
import { EstadoRodadaBadge } from '@/components/rodadas/EstadoRodada';
import { GradeModal } from '@/components/palpites/GradeModal';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { ClassificacaoRodadaApi, GestaoRodadasApi, JogoGestao } from '@/types';

type Aba = 'jogos' | 'classificacao';
interface FormJogo { id: number | null; casa: string; fora: string; rodadaId: string; data: string; classico: boolean }

const statusJogo = {
  encerrado: { cor: 'green', texto: 'Encerrado' },
  aguardando: { cor: 'yellow', texto: 'Aguardando resultado' },
  agendado: { cor: 'gray', texto: 'Agendado' },
} as const;
const medalColors = ['#fbbf24', '#cbd5e1', '#d97706'];
const botaoSecundario = 'px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';
const botaoPrimario = 'px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-60';
const placarInput = 'w-16 h-16 text-2xl font-bold text-center rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500';

export function RodadasScreen() {
  const showToast = useToast();
  const { setView } = useApp();
  const [rodadaId, setRodadaId] = useState<number | null>(null);
  const [aba, setAba] = useState<Aba>('jogos');
  const { dados, carregando, erro, recarregar } = useRecurso<GestaoRodadasApi>(rodadaId ? `/rodadas?rodada_id=${rodadaId}` : '/rodadas');
  const r = dados?.rodada;
  const classificacao = useRecurso<ClassificacaoRodadaApi>(aba === 'classificacao' && r ? `/rodadas/${r.id}/classificacao` : null);

  const [resultado, setResultado] = useState<{ jogo: JogoGestao; casa: string; fora: string; primeiroGol: string; focoGol?: boolean } | null>(null);
  const abrirResultado = (jogo: JogoGestao, focoGol = false) => setResultado({
    jogo, casa: jogo.golsCasa?.toString() ?? '', fora: jogo.golsFora?.toString() ?? '', primeiroGol: jogo.primeiroGol ?? '', focoGol,
  });
  const [formJogo, setFormJogo] = useState<FormJogo | null>(null);
  const [excluir, setExcluir] = useState<JogoGestao | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [grade, setGrade] = useState<number | null>(null);

  const gravar = async (acao: () => Promise<{ mensagem?: string }>, depois?: () => void) => {
    setSalvando(true);
    try {
      const resposta = await acao();
      if (resposta.mensagem) showToast(resposta.mensagem);
      depois?.();
      await recarregar();
      if (aba === 'classificacao') await classificacao.recarregar();
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
      throw e;
    } finally {
      setSalvando(false);
    }
  };
  const tentar = (acao: () => Promise<{ mensagem?: string }>, depois?: () => void) => { gravar(acao, depois).catch(() => undefined); };

  const abrirNovoJogo = () => r && setFormJogo({ id: null, casa: '', fora: '', rodadaId: String(r.id), data: '', classico: false });
  const abrirEdicao = (j: JogoGestao) => setFormJogo({ id: j.id, casa: j.casa, fora: j.fora, rodadaId: String(j.rodadaId), data: j.dataInput, classico: j.classico });

  const salvarJogo = () => {
    if (!formJogo) return;
    const corpo = { casa: formJogo.casa, fora: formJogo.fora, rodadaId: formJogo.rodadaId, data: formJogo.data, classico: formJogo.classico };
    tentar(() => formJogo.id ? api.put(`/jogos/${formJogo.id}`, corpo) : api.post('/jogos', corpo), () => setFormJogo(null));
  };

  const salvarResultado = () => {
    if (!resultado) return;
    tentar(() => api.post(`/jogos/${resultado.jogo.id}/resultado`, {
      golsCasa: resultado.casa, golsFora: resultado.fora,
      primeiroGol: Number(resultado.casa) + Number(resultado.fora) === 0 ? '' : resultado.primeiroGol,
    }), () => setResultado(null));
  };

  return (
    <div>
      <Header
        title="Rodadas"
        subtitle="Jogos e resultados de cada rodada"
        actions={r ? (
          <button onClick={abrirNovoJogo} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold transition-colors">
            <Plus className="w-4 h-4" /><span className="hidden sm:inline">Novo jogo</span>
          </button>
        ) : undefined}
      />

      <div className="p-4 md:p-8 pb-28 md:pb-8 space-y-5">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={4} />}
        {dados && !r && (
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
            <EmptyState icon={<Calendar className="w-10 h-10" />} title="Nenhuma rodada cadastrada" description="Cadastre as rodadas na aba Campeonatos." />
          </div>
        )}

        {dados && r && (
          <>
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-3 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
              <SeletorRodadas rodadas={dados.rodadas} selecionadaId={rodadaId ?? dados.rodadaAtualId ?? r.id} atualId={dados.rodadaAtualId}
                onSelecionar={id => setRodadaId(id === dados.rodadaAtualId ? null : id)} />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">{r.nome}</h2>
                <EstadoRodadaBadge estado={r.estado} faltantes={r.faltantes} />
              </div>
              <div className="flex gap-2">
                <button onClick={() => setGrade(r.id)} className="flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <Grid3x3 className="w-4 h-4" /><span className="hidden sm:inline">Grade</span>
                </button>
                <button onClick={() => setView('palpites', { rodadaId: r.id })} className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold transition-colors ${r.estado === 'pendente' ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 hover:bg-brand-100'}`}>
                  <Target className="w-4 h-4" /> Lançar palpites
                </button>
              </div>
            </div>

            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
              {([['jogos', 'Jogos', Calendar], ['classificacao', 'Classificação', Trophy]] as const).map(([id, label, Icon]) => (
                <button key={id} onClick={() => setAba(id)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${aba === id ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500'}`}>
                  <Icon className="w-4 h-4" /> {label}
                </button>
              ))}
            </div>

            {aba === 'jogos' && (
              <div className={`space-y-3 transition-opacity ${carregando ? 'opacity-60' : ''}`}>
                <p className="text-sm text-gray-400">{dados.jogos.length} jogos na rodada · {r.participantes} participantes</p>
                {dados.jogos.length === 0 && (
                  <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
                    <EmptyState icon={<Calendar className="w-10 h-10" />} title="Nenhum jogo nesta rodada"
                      action={<button onClick={abrirNovoJogo} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700"><Plus className="w-4 h-4" /> Novo jogo</button>} />
                  </div>
                )}
                {dados.jogos.map(jogo => {
                  const st = statusJogo[jogo.status];
                  const temPlacar = jogo.golsCasa !== null && jogo.golsFora !== null;
                  return (
                    <div key={jogo.id} className="bg-white dark:bg-gray-900 rounded-2xl p-4 md:p-5 shadow-sm border border-gray-100 dark:border-gray-800 animate-slide-up">
                      <div className="flex items-center justify-between gap-2 mb-4">
                        <div className="flex items-center gap-3 text-xs text-gray-400 min-w-0">
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{jogo.dataTexto ?? 'Horário a definir'}</span>
                          {jogo.classico && <span className="flex items-center gap-1 text-gold-600"><Star className="w-3 h-3 fill-gold-400" />Clássico</span>}
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {jogo.encerrado && !temPlacar && <Badge color="red" icon={<Lock className="w-3 h-3" />}>Encerrado p/ palpites</Badge>}
                          <Badge color={st.cor}>{st.texto}</Badge>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 md:gap-6">
                        <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0">
                          <TeamCrest nome={jogo.casa} escudo={jogo.escudoCasa} size="md" />
                          <div className="min-w-0">
                            <p className="font-semibold text-gray-900 dark:text-white text-sm md:text-base truncate">{jogo.casa}</p>
                            <p className="text-xs text-gray-400">{jogo.escudoCasa.sigla} (M)</p>
                          </div>
                        </div>
                        <div className="shrink-0">
                          {temPlacar ? (
                            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-800">
                              <span className="text-xl font-bold text-gray-900 dark:text-white">{jogo.golsCasa}</span>
                              <span className="text-gray-400 text-sm">×</span>
                              <span className="text-xl font-bold text-gray-900 dark:text-white">{jogo.golsFora}</span>
                            </div>
                          ) : <div className="text-gray-300 text-xl font-bold">×</div>}
                        </div>
                        <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0 justify-end">
                          <div className="min-w-0 text-right">
                            <p className="font-semibold text-gray-900 dark:text-white text-sm md:text-base truncate">{jogo.fora}</p>
                            <p className="text-xs text-gray-400">{jogo.escudoFora.sigla} (V)</p>
                          </div>
                          <TeamCrest nome={jogo.fora} escudo={jogo.escudoFora} size="md" />
                        </div>
                      </div>
                      {jogo.classico && (
                        <div className={`mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm ${jogo.primeiroGol ? 'bg-gold-50 dark:bg-gold-900/20 text-gold-800 dark:text-gold-300' : 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400'}`}>
                          <span className="flex items-center gap-1.5 min-w-0">
                            <Star className="w-4 h-4 shrink-0 text-gold-500 fill-gold-400" />
                            {jogo.primeiroGol ? <>1º gol: <strong className="truncate">{jogo.primeiroGol}</strong></> : 'Primeiro gol ainda não informado'}
                          </span>
                          <button onClick={() => abrirResultado(jogo, true)} className="text-xs font-semibold text-brand-700 dark:text-brand-300 hover:underline">
                            {jogo.primeiroGol ? 'Alterar' : 'Informar 1º gol'}
                          </button>
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-1 mt-4 pt-4 border-t border-gray-50 dark:border-gray-800">
                        <button onClick={() => abrirResultado(jogo)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                          <ListChecks className="w-4 h-4" /> Resultado real
                        </button>
                        <button onClick={() => abrirEdicao(jogo)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                          <Pencil className="w-4 h-4" /> Editar
                        </button>
                        <button onClick={() => tentar(() => api.post(`/jogos/${jogo.id}/encerrado`, { encerrado: !jogo.encerrado }))} disabled={salvando}
                          title={jogo.encerrado ? 'Reabrir para palpites' : 'Encerrar para palpites'}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50">
                          {jogo.encerrado ? <><LockOpen className="w-4 h-4" /> Reabrir</> : <><Lock className="w-4 h-4" /> Encerrar</>}
                        </button>
                        <button onClick={() => setExcluir(jogo)} disabled={!jogo.podeExcluir} aria-label="Excluir jogo"
                          title={jogo.podeExcluir ? 'Excluir jogo' : 'Jogo com palpites não pode ser excluído'}
                          className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed">
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <button onClick={() => setView('palpites', { rodadaId: r.id })} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors ml-auto">
                          <Users className="w-4 h-4" /> Palpites
                          <Badge color={jogo.palpites >= r.participantes && r.participantes > 0 ? 'green' : 'gray'} size="sm">{jogo.palpites}/{r.participantes}</Badge>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {aba === 'classificacao' && (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                  <h3 className="font-bold text-gray-900 dark:text-white flex items-center gap-2"><Trophy className="w-5 h-5 text-brand-600" /> Classificação — {r.nome}</h3>
                </div>
                {classificacao.erro && <div className="p-4"><ErroCarga mensagem={classificacao.erro} onTentar={classificacao.recarregar} /></div>}
                {!classificacao.dados && classificacao.carregando && <div className="p-4"><Carregando linhas={4} /></div>}
                <div className="divide-y divide-gray-50 dark:divide-gray-800">
                  {classificacao.dados?.ranking.map((p, i) => (
                    <div key={p.participacaoId} className="flex items-center gap-3 px-5 py-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${i < 3 ? 'text-white' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
                        style={i < 3 ? { backgroundColor: medalColors[i] } : {}}>
                        {i < 3 ? <Medal className="w-4 h-4" /> : i + 1}
                      </div>
                      <Avatar nome={p.nome} id={p.participacaoId} size="md" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.nome}</p>
                        <p className="text-xs text-gray-400">{p.cravadas} cravadas · {p.acertosVencedor} acertos{p.bonusPrimeiroGol ? ` · +${p.bonusPrimeiroGol} 1º gol` : ''}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-brand-600 dark:text-brand-400">{p.pontos}</p>
                        <p className="text-[10px] text-gray-400">pontos</p>
                      </div>
                    </div>
                  ))}
                  {classificacao.dados && classificacao.dados.ranking.length === 0 && <p className="p-6 text-center text-sm text-gray-400">Ninguém participa desta rodada.</p>}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Resultado real (modal do Bolt) */}
      <Modal open={!!resultado} onClose={() => setResultado(null)} title="Resultado real do jogo" size="sm"
        footer={<>
          <button onClick={() => setResultado(null)} className={botaoSecundario}>Cancelar</button>
          <button onClick={salvarResultado} disabled={salvando} className={botaoPrimario}><Check className="w-4 h-4" /> Lançar resultado</button>
        </>}>
        {resultado && (
          <div className="space-y-5">
            <div className="flex items-center justify-center gap-4">
              <div className="flex flex-col items-center gap-2 w-16">
                <TeamCrest nome={resultado.jogo.casa} escudo={resultado.jogo.escudoCasa} size="lg" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{resultado.jogo.escudoCasa.sigla}</p>
              </div>
              <div className="flex items-center gap-2">
                <input type="number" min={0} max={99} inputMode="numeric" aria-label={`Gols ${resultado.jogo.casa}`} autoFocus={!resultado.focoGol}
                  value={resultado.casa} onChange={e => setResultado({ ...resultado, casa: e.target.value })} className={placarInput} />
                <span className="text-2xl text-gray-300">×</span>
                <input type="number" min={0} max={99} inputMode="numeric" aria-label={`Gols ${resultado.jogo.fora}`}
                  value={resultado.fora} onChange={e => setResultado({ ...resultado, fora: e.target.value })} className={placarInput} />
              </div>
              <div className="flex flex-col items-center gap-2 w-16">
                <TeamCrest nome={resultado.jogo.fora} escudo={resultado.jogo.escudoFora} size="lg" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{resultado.jogo.escudoFora.sigla}</p>
              </div>
            </div>
            {resultado.jogo.classico && (() => {
              const semGols = resultado.casa !== '' && resultado.fora !== '' && Number(resultado.casa) + Number(resultado.fora) === 0;
              return (
                <div className="rounded-xl border border-gold-200 dark:border-gold-800/40 bg-gold-50/60 dark:bg-gold-900/10 p-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-gold-800 dark:text-gold-300">
                    <Star className="w-4 h-4 text-gold-500 fill-gold-400" /> Primeiro gol do clássico
                  </div>
                  <Input placeholder="Nome do jogador que fez o primeiro gol" value={semGols ? '' : resultado.primeiroGol} disabled={semGols}
                    autoFocus={resultado.focoGol} list="sugestoes-primeiro-gol"
                    onChange={e => setResultado({ ...resultado, primeiroGol: e.target.value })}
                    hint={semGols ? 'Jogo sem gols (0 × 0): não há bônus de primeiro gol.' : 'Quem palpitou o mesmo jogador ganha +2 pontos. Maiúsculas e acentos não importam.'} />
                  <datalist id="sugestoes-primeiro-gol">
                    {resultado.jogo.sugestoesPrimeiroGol.map(s => <option key={s.nome} value={s.nome} />)}
                  </datalist>
                  {!semGols && resultado.jogo.sugestoesPrimeiroGol.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5">Palpitados pelos participantes (toque para usar):</p>
                      <div className="flex flex-wrap gap-1.5">
                        {resultado.jogo.sugestoesPrimeiroGol.map(s => (
                          <button key={s.nome} type="button" onClick={() => setResultado({ ...resultado, primeiroGol: s.nome })}
                            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${resultado.primeiroGol.trim().toLowerCase() === s.nome.toLowerCase() ? 'bg-brand-600 border-brand-600 text-white' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-brand-300'}`}>
                            {s.nome} · {s.palpites}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </Modal>

      {/* Novo / editar jogo */}
      <Modal open={!!formJogo} onClose={() => setFormJogo(null)} title={formJogo?.id ? 'Editar jogo' : 'Novo jogo'}
        footer={<>
          <button onClick={() => setFormJogo(null)} className={botaoSecundario}>Cancelar</button>
          <button onClick={salvarJogo} disabled={salvando} className={botaoPrimario}>{formJogo?.id ? 'Salvar' : 'Cadastrar'}</button>
        </>}>
        {formJogo && dados && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input label="Mandante" value={formJogo.casa} maxLength={100} onChange={e => setFormJogo({ ...formJogo, casa: e.target.value })} />
              <Input label="Visitante" value={formJogo.fora} maxLength={100} onChange={e => setFormJogo({ ...formJogo, fora: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Select label="Rodada" value={formJogo.rodadaId} onChange={e => setFormJogo({ ...formJogo, rodadaId: e.target.value })}>
                {dados.rodadas.map(x => <option key={x.id} value={x.id}>{x.nome}</option>)}
              </Select>
              <Input label="Data e hora (Brasília)" type="datetime-local" value={formJogo.data} onChange={e => setFormJogo({ ...formJogo, data: e.target.value })} />
            </div>
            <Switch checked={formJogo.classico} onChange={v => setFormJogo({ ...formJogo, classico: v })} label="Clássico" description="Placar exato vale 5 e resultado 3; primeiro gol vale +2" />
          </div>
        )}
      </Modal>

      <GradeModal rodadaId={grade} onClose={() => setGrade(null)} />

      <ConfirmDialog open={!!excluir} onClose={() => setExcluir(null)}
        onConfirm={() => excluir ? gravar(() => api.delete(`/jogos/${excluir.id}`)) : undefined}
        title="Excluir jogo?" danger confirmLabel="Excluir"
        message={excluir ? <>O jogo <strong>{excluir.casa} × {excluir.fora}</strong> será excluído. Esta ação não pode ser desfeita.</> : ''} />
    </div>
  );
}
