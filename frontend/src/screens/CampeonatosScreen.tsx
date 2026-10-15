import { useState, type ReactNode } from 'react';
import { Calendar, Download, ExternalLink, Grid3x3, MoreVertical, Pencil, Plus, RefreshCw, Target, Trash2, Trophy } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Input } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { TabelaOficial } from '@/components/campeonatos/TabelaOficial';
import { EstadoRodadaBadge } from '@/components/rodadas/EstadoRodada';
import { GradeModal } from '@/components/palpites/GradeModal';
import { useApp } from '@/context/AppContext';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { CampeonatoApi, RodadaGestao } from '@/types';

type Aba = 'rodadas' | 'tabela';

const botaoSecundario = 'px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';
const botaoPrimario = 'px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-60';

/** Campeonatos do bolão. Fica dentro de Configurações; `topo` recebe as abas dessa tela. */
export function CampeonatosScreen({ titulo = 'Campeonatos', subtitulo = 'Campeonato do bolão, rodadas e tabela oficial', topo }: { titulo?: string; subtitulo?: string; topo?: ReactNode }) {
  const showToast = useToast();
  const [aba, setAba] = useState<Aba>('rodadas');
  const { dados, carregando, erro, recarregar } = useRecurso<CampeonatoApi>('/campeonato');
  const [menuAberto, setMenuAberto] = useState(false);
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({ nome: '', ano: '', codigoApi: '' });
  const [novaRodada, setNovaRodada] = useState<{ nome: string; aberta: boolean } | null>(null);
  const [excluir, setExcluir] = useState<RodadaGestao | null>(null);
  const [salvando, setSalvando] = useState(false);

  const executar = async <T extends { mensagem?: string }>(acao: () => Promise<T>) => {
    try {
      const r = await acao();
      if (r.mensagem) showToast(r.mensagem);
      await recarregar();
      return true;
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
      throw e;
    }
  };

  const abrirEdicao = () => {
    if (!dados) return;
    const c = dados.campeonato;
    setForm({ nome: c.nome, ano: String(c.ano ?? ''), codigoApi: c.codigoApi || 'BSA' });
    setMenuAberto(false);
    setEditando(true);
  };

  const salvarCampeonato = async () => {
    setSalvando(true);
    try { await executar(() => api.put<{ mensagem: string }>('/campeonato', form)); setEditando(false); }
    catch { /* aviso já exibido */ } finally { setSalvando(false); }
  };

  const salvarRodada = async () => {
    if (!novaRodada) return;
    setSalvando(true);
    try { await executar(() => api.post<{ mensagem: string }>('/rodadas', novaRodada)); setNovaRodada(null); }
    catch { /* aviso já exibido */ } finally { setSalvando(false); }
  };

  const c = dados?.campeonato;
  const progresso = c && c.totalRodadas ? Math.round((c.rodadasConcluidas / c.totalRodadas) * 100) : 0;

  return (
    <div>
      <Header
        title={titulo}
        subtitle={subtitulo}
        actions={aba === 'rodadas' && dados ? (
          <button onClick={() => setNovaRodada({ nome: '', aberta: true })}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold transition-colors">
            <Plus className="w-4 h-4" /><span className="hidden sm:inline">Nova rodada</span>
          </button>
        ) : undefined}
      />

      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        {topo}
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={3} />}

        {dados && c && (
          <>
            {/* Card do campeonato, no estilo do Bolt */}
            <div className="grid lg:grid-cols-3 gap-4">
              <div className="lg:col-span-1 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 relative animate-slide-up">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md">
                    <Trophy className="w-6 h-6 text-white" />
                  </div>
                  <div className="relative">
                    <button onClick={() => setMenuAberto(v => !v)} aria-label="Opções do campeonato" className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                      <MoreVertical className="w-4 h-4 text-gray-400" />
                    </button>
                    {menuAberto && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setMenuAberto(false)} />
                        <div className="absolute right-0 top-9 z-20 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 py-1.5 w-44 animate-scale-in">
                          <button onClick={abrirEdicao} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                            <Pencil className="w-4 h-4" /> Editar
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white text-lg">{c.nome}</h3>
                <p className="text-sm text-gray-400 mb-3">Temporada {c.ano ?? '—'}</p>
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  <Badge color={c.rodadasConcluidas === c.totalRodadas && c.totalRodadas > 0 ? 'gray' : 'green'}>
                    {c.rodadasConcluidas === c.totalRodadas && c.totalRodadas > 0 ? 'Encerrado' : 'Em andamento'}
                  </Badge>
                  {c.codigoApi && <Badge color="purple">API: {c.codigoApi}</Badge>}
                </div>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-gray-500 dark:text-gray-400 flex items-center gap-1"><Calendar className="w-3 h-3" />{c.rodadasConcluidas} de {c.totalRodadas} rodadas concluídas</span>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">{progresso}%</span>
                </div>
                <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-brand-400 to-brand-600 rounded-full transition-all duration-500" style={{ width: `${progresso}%` }} />
                </div>
              </div>

              {/* Atalhos para telas ainda não migradas */}
              <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
                <h3 className="font-bold text-gray-900 dark:text-white mb-1">Jogos</h3>
                <p className="text-xs text-gray-400 mb-4">Estas ferramentas abrem as telas atuais do sistema.</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  {[
                    { href: dados.links.novoJogo, label: 'Cadastrar jogo avulso', icon: Plus },
                    { href: dados.links.sync, label: 'Sincronizar com a API', icon: RefreshCw },
                    { href: dados.links.importarJogos, label: 'Importar jogos da API', icon: Download },
                  ].filter(a => a.href).map(a => {
                    const Icon = a.icon;
                    return (
                      <a key={a.label} href={a.href} className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-brand-200 dark:hover:border-brand-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <span className="w-9 h-9 rounded-lg bg-brand-50 dark:bg-brand-900/30 text-brand-600 flex items-center justify-center"><Icon className="w-4 h-4" /></span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 flex-1">{a.label}</span>
                        <ExternalLink className="w-4 h-4 text-gray-300" />
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Abas */}
            <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit">
              {([['rodadas', 'Rodadas', Calendar], ['tabela', 'Tabela oficial', Target]] as const).map(([id, label, Icon]) => (
                <button key={id} onClick={() => setAba(id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${aba === id ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'}`}>
                  <Icon className="w-4 h-4" />{label}
                </button>
              ))}
            </div>

            {aba === 'tabela' ? <TabelaOficial /> : dados.rodadas.length === 0 ? (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
                <EmptyState icon={<Calendar className="w-10 h-10" />} title="Nenhuma rodada cadastrada" description="Cadastre as rodadas ou sincronize com a API."
                  action={<button onClick={() => setNovaRodada({ nome: '', aberta: true })} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700"><Plus className="w-4 h-4" /> Nova rodada</button>} />
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
                {/* Desktop: tabela */}
                <table className="hidden md:table w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 dark:border-gray-800">
                      <th className="text-left py-3 px-5 text-xs font-semibold text-gray-400 uppercase">Rodada</th>
                      <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Jogos</th>
                      <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Resultados</th>
                      <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Situação</th>
                      <th className="text-right py-3 px-5 text-xs font-semibold text-gray-400 uppercase">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.rodadas.map(r => (
                      <tr key={r.id} className={`border-b border-gray-50 dark:border-gray-800/50 transition-colors ${r.estado === 'pendente' ? 'bg-red-50/70 dark:bg-red-900/10 hover:bg-red-50' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}>
                        <td className={`py-3 px-5 font-semibold text-gray-900 dark:text-white ${r.estado === 'pendente' ? 'shadow-[inset_3px_0_0_#ef4444]' : ''}`}>{r.nome}</td>
                        <td className="py-3 px-3 text-center text-gray-500">{r.jogos}</td>
                        <td className="py-3 px-3 text-center text-gray-500">{r.comResultado}/{r.jogos}</td>
                        <td className="py-3 px-3 text-center"><EstadoRodadaBadge estado={r.estado} faltantes={r.faltantes} /></td>
                        <td className="py-3 px-5"><AcoesRodada r={r} onExcluir={setExcluir} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {/* Celular: cards */}
                <div className="md:hidden divide-y divide-gray-100 dark:divide-gray-800">
                  {dados.rodadas.map(r => (
                    <div key={r.id} className={`p-4 space-y-3 ${r.estado === 'pendente' ? 'bg-red-50/70 dark:bg-red-900/10 shadow-[inset_3px_0_0_#ef4444]' : ''}`}>
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="font-semibold text-gray-900 dark:text-white">{r.nome}</p>
                          <p className="text-xs text-gray-400">{r.jogos} jogos · {r.comResultado} com resultado</p>
                        </div>
                        <EstadoRodadaBadge estado={r.estado} faltantes={r.faltantes} />
                      </div>
                      <AcoesRodada r={r} onExcluir={setExcluir} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <Modal open={editando} onClose={() => setEditando(false)} title="Editar campeonato"
        footer={<>
          <button onClick={() => setEditando(false)} className={botaoSecundario}>Cancelar</button>
          <button onClick={salvarCampeonato} disabled={salvando} className={botaoPrimario}>Salvar</button>
        </>}>
        <div className="space-y-4">
          <Input label="Nome do campeonato" value={form.nome} maxLength={100} onChange={e => setForm({ ...form, nome: e.target.value })} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Temporada" type="number" value={form.ano} onChange={e => setForm({ ...form, ano: e.target.value })} />
            <Input label="Código na API" value={form.codigoApi} maxLength={20} onChange={e => setForm({ ...form, codigoApi: e.target.value.toUpperCase() })}
              hint="BSA = Brasileirão" />
          </div>
          <p className="text-xs text-gray-400">O código e a temporada são usados para buscar horários e a tabela na football-data.org.</p>
        </div>
      </Modal>

      <Modal open={!!novaRodada} onClose={() => setNovaRodada(null)} title="Nova rodada" size="sm"
        footer={<>
          <button onClick={() => setNovaRodada(null)} className={botaoSecundario}>Cancelar</button>
          <button onClick={salvarRodada} disabled={salvando} className={botaoPrimario}>Criar</button>
        </>}>
        {novaRodada && (
          <div className="space-y-4">
            <Input label="Nome da rodada" placeholder="Ex.: 39º Rodada" value={novaRodada.nome} maxLength={100} onChange={e => setNovaRodada({ ...novaRodada, nome: e.target.value })} />
            <p className="text-xs text-gray-400">A situação (aberta, pendente ou fechada) é calculada automaticamente pelos jogos e palpites.</p>
          </div>
        )}
      </Modal>


      <ConfirmDialog
        open={!!excluir}
        onClose={() => setExcluir(null)}
        onConfirm={() => excluir ? executar(() => api.delete<{ mensagem: string }>(`/rodadas/${excluir.id}`)) : undefined}
        title="Excluir rodada?"
        message={excluir ? <>A <strong>{excluir.nome}</strong> e todos os seus jogos serão excluídos. Esta ação não pode ser desfeita.</> : ''}
        confirmLabel="Excluir"
        danger
      />
    </div>
  );
}

function AcoesRodada({ r, onExcluir }: { r: RodadaGestao; onExcluir: (r: RodadaGestao) => void }) {
  const { setView } = useApp();
  const [grade, setGrade] = useState<number | null>(null);
  const base = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors';
  return (
    <div className="flex flex-wrap md:justify-end gap-1.5">
      <button onClick={() => setGrade(r.id)} className={`${base} border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`} title="Ver grade de palpites">
        <Grid3x3 className="w-3.5 h-3.5" /> Grade
      </button>
      <GradeModal rodadaId={grade} onClose={() => setGrade(null)} />
      <button onClick={() => setView('palpites', { rodadaId: r.id })} title="Lançar palpites dos participantes"
        className={`${base} ${r.estado === 'pendente' ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 hover:bg-brand-100'}`}>
        <Target className="w-3.5 h-3.5" /> {r.estado === 'pendente' ? 'Palpitar agora' : 'Palpitar'}
      </button>
      <button onClick={() => onExcluir(r)} disabled={!r.podeExcluir} aria-label="Excluir rodada"
        title={r.podeExcluir ? 'Excluir rodada' : 'Rodada com palpites ou créditos históricos não pode ser excluída'}
        className={`${base} text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed`}>
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
