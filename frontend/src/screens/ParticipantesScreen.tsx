import { useMemo, useState } from 'react';
import { PencilLine, Pencil, Plus, Search, Shield, UserMinus, UserCheck, UserX, Users } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Drawer } from '@/components/ui/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { Variacao } from '@/components/ui/Variacao';
import { DesistenciaModal } from '@/components/participantes/DesistenciaModal';
import { DetalheParticipante } from '@/components/participantes/DetalheParticipante';
import { FormParticipante } from '@/components/participantes/FormParticipante';
import { StatusBadge } from '@/components/participantes/StatusBadge';
import { useApp } from '@/context/AppContext';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { AcaoDesistencia, ParticipanteApi, ParticipantesApi } from '@/types';

type Filtro = 'todos' | 'ativos' | 'desistentes';

const botao = 'flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors';

function semAcento(texto: string) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

export function ParticipantesScreen() {
  const showToast = useToast();
  const { setView, logout } = useApp();
  const { dados, carregando, erro, recarregar } = useRecurso<ParticipantesApi>('/participantes');
  const [busca, setBusca] = useState('');
  const [filtro, setFiltro] = useState<Filtro>('todos');
  const [form, setForm] = useState<{ pessoa: ParticipanteApi | null } | null>(null);
  const [detalheId, setDetalheId] = useState<number | null>(null);
  const [versao, setVersao] = useState(0);
  const [desistencia, setDesistencia] = useState<{ pessoa: ParticipanteApi; acao: AcaoDesistencia } | null>(null);
  const [status, setStatus] = useState<{ pessoa: ParticipanteApi; acao: 'remover' | 'reativar' } | null>(null);

  const lista = useMemo(() => {
    if (!dados) return [];
    const termo = semAcento(busca.trim());
    return dados.participantes.filter(p => {
      if (termo && !semAcento(p.nome).includes(termo) && !semAcento(p.email).includes(termo)) return false;
      if (filtro === 'ativos') return p.status === 'ativo';
      if (filtro === 'desistentes') return p.status === 'desistente';
      return true;
    });
  }, [dados, busca, filtro]);

  const detalhe = dados?.participantes.find(p => p.id === detalheId) ?? null;
  const atualizar = async () => { await recarregar(); setVersao(v => v + 1); };
  const concluir = (sair: boolean) => { if (sair) logout(); else void atualizar(); };

  const alterarStatus = async () => {
    if (!status) return;
    try {
      const r = await api.post<{ mensagem: string; logout: boolean }>(`/participantes/${status.pessoa.id}/status`, { acao: status.acao });
      showToast(r.mensagem);
      concluir(r.logout);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível alterar o status.', 'error');
      throw e;
    }
  };

  const lancar = (p: ParticipanteApi) => setView('palpites', { participacaoId: p.id });

  const filtros: { id: Filtro; label: string }[] = [
    { id: 'todos', label: 'Todos' }, { id: 'ativos', label: 'Ativos' }, { id: 'desistentes', label: 'Desistentes' },
  ];

  return (
    <div>
      <Header
        title="Participantes"
        subtitle={dados ? `${dados.contagens.ativos} ativos · ${dados.contagens.todos} cadastrados` : 'Participantes do bolão'}
        actions={dados ? (
          <button onClick={() => setForm({ pessoa: null })} disabled={!dados.rodadas.length}
            title={dados.rodadas.length ? undefined : 'Cadastre uma rodada antes de adicionar participantes'}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold transition-colors disabled:opacity-50">
            <Plus className="w-4 h-4" /><span className="hidden sm:inline">Novo participante</span>
          </button>
        ) : undefined}
      />

      <div className="p-4 md:p-8 pb-28 md:pb-8 space-y-4">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={5} />}

        {dados && (
          <>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input type="search" value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar por nome ou e-mail…" aria-label="Buscar participante"
                  className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 transition-colors" />
              </div>
              <div className="flex gap-2 overflow-x-auto no-scrollbar" role="group" aria-label="Filtrar participantes">
                {filtros.map(f => (
                  <button key={f.id} onClick={() => setFiltro(f.id)} aria-pressed={filtro === f.id}
                    className={`px-3 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${filtro === f.id ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
                    {f.label} <span className="opacity-70">({dados.contagens[f.id]})</span>
                  </button>
                ))}
              </div>
            </div>

            {lista.length === 0 ? (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
                <EmptyState icon={<Users className="w-10 h-10" />} title="Nenhum participante encontrado"
                  description={dados.participantes.length ? 'Ajuste a busca ou o filtro' : 'Cadastre o primeiro participante do bolão'} />
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden animate-slide-up">
                {/* Tabela (desktop) */}
                <div className="hidden md:block overflow-x-auto scrollbar-thin">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-100 dark:border-gray-800">
                        <th className="text-left py-3 px-5 text-xs font-semibold text-gray-400 uppercase">Participante</th>
                        <th className="text-left py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Contato</th>
                        <th className="text-left py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Entrada</th>
                        <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Pontos</th>
                        <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase" title={dados.variacaoReferencia ? `Variação após a ${dados.variacaoReferencia}` : undefined}>Posição</th>
                        <th className="text-center py-3 px-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
                        <th className="py-3 px-5"><span className="sr-only">Ações</span></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                      {lista.map(p => (
                        <tr key={p.id} onClick={() => setDetalheId(p.id)} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors">
                          <td className="py-3 px-5">
                            <div className="flex items-center gap-3">
                              <Avatar nome={p.nome} id={p.id} size="md" />
                              <div className="min-w-0">
                                <button onClick={e => { e.stopPropagation(); setDetalheId(p.id); }} className="text-sm font-medium text-gray-900 dark:text-white text-left hover:text-brand-700">{p.nome}</button>
                                <div className="flex gap-1.5 mt-0.5">
                                  {p.responsavel && <Badge color="purple" size="sm" icon={<Shield className="w-3 h-3" />}>Responsável</Badge>}
                                  {p.duplicado && <Badge color="yellow" size="sm">Registro {p.id}</Badge>}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-sm text-gray-500 dark:text-gray-400 max-w-[14rem] truncate">{p.email || '—'}</td>
                          <td className="py-3 px-3 text-sm text-gray-600 dark:text-gray-400">
                            {p.rodadaEntrada?.nome ?? '—'}
                            {p.rodadaDesistencia && <span className="block text-xs text-gold-700 dark:text-gold-300">Desistiu na {p.rodadaDesistencia.nome}</span>}
                          </td>
                          <td className="py-3 px-3 text-center"><span className="text-sm font-bold text-brand-600 dark:text-brand-400">{p.pontos}</span></td>
                          <td className="py-3 px-3 text-center">
                            <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-700 dark:text-gray-300">{p.posicao ? `${p.posicao}º` : '—'} <Variacao valor={p.variacao} /></span>
                          </td>
                          <td className="py-3 px-3 text-center"><StatusBadge status={p.status} /></td>
                          <td className="py-3 px-5">
                            <div className="flex items-center justify-end gap-1" onClick={e => e.stopPropagation()}>
                              {p.status === 'ativo' && (
                                <button onClick={() => lancar(p)} title="Lançar palpites" aria-label={`Lançar palpites de ${p.nome}`} className="p-1.5 rounded-lg hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">
                                  <PencilLine className="w-4 h-4 text-brand-600" />
                                </button>
                              )}
                              <button onClick={() => setForm({ pessoa: p })} title="Editar" aria-label={`Editar ${p.nome}`} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                                <Pencil className="w-4 h-4 text-gray-400" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Cartões (celular) */}
                <div className="md:hidden divide-y divide-gray-50 dark:divide-gray-800">
                  {lista.map(p => (
                    <button key={p.id} onClick={() => setDetalheId(p.id)} className="w-full text-left p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                      <div className="flex items-start gap-3">
                        <Avatar nome={p.nome} id={p.id} size="md" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.nome}</p>
                            {p.responsavel && <Shield className="w-3.5 h-3.5 text-purple-500 shrink-0" aria-label="Responsável" />}
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5 truncate">{p.email || (p.rodadaEntrada ? `Entrou na ${p.rodadaEntrada.nome}` : '')}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <StatusBadge status={p.status} />
                            <Badge color="green" size="sm">{p.pontos} pts</Badge>
                            {p.duplicado && <Badge color="yellow" size="sm">Registro {p.id}</Badge>}
                          </div>
                        </div>
                        <span className="flex flex-col items-end gap-0.5 text-sm font-bold text-gray-700 dark:text-gray-300 shrink-0">
                          {p.posicao ? `${p.posicao}º` : '—'}<Variacao valor={p.variacao} />
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {dados && (
        <FormParticipante aberto={!!form} pessoa={form?.pessoa ?? null} dados={dados} onClose={() => setForm(null)} onSalvo={atualizar} />
      )}

      <Drawer open={!!detalhe} onClose={() => setDetalheId(null)} title="Detalhes do participante" width="max-w-xl"
        footer={detalhe ? (
          <div className="flex flex-wrap gap-2 w-full justify-end">
            {detalhe.status === 'ativo' && (
              <>
                <button onClick={() => setStatus({ pessoa: detalhe, acao: 'remover' })} className={`${botao} text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20`}>
                  <UserX className="w-4 h-4" /> Remover
                </button>
                <button onClick={() => setDesistencia({ pessoa: detalhe, acao: 'registrar' })} className={`${botao} border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
                  <UserMinus className="w-4 h-4" /> Desistência
                </button>
              </>
            )}
            {detalhe.status === 'desistente' && (
              <>
                <button onClick={() => setDesistencia({ pessoa: detalhe, acao: 'corrigir' })} className={`${botao} border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
                  <UserMinus className="w-4 h-4" /> Editar desistência
                </button>
                <button onClick={() => setDesistencia({ pessoa: detalhe, acao: 'reativar' })} className={`${botao} border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
                  <UserCheck className="w-4 h-4" /> Reativar
                </button>
              </>
            )}
            {(detalhe.status === 'removido' || detalhe.status === 'saiu') && (
              <button onClick={() => setStatus({ pessoa: detalhe, acao: 'reativar' })} className={`${botao} border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
                <UserCheck className="w-4 h-4" /> Reativar
              </button>
            )}
            <button onClick={() => setForm({ pessoa: detalhe })} className={`${botao} border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800`}>
              <Pencil className="w-4 h-4" /> Editar
            </button>
            {detalhe.status === 'ativo' && (
              <button onClick={() => lancar(detalhe)} className={`${botao} bg-brand-600 hover:bg-brand-700 text-white`}>
                <PencilLine className="w-4 h-4" /> Lançar palpites
              </button>
            )}
          </div>
        ) : undefined}>
        {detalhe && <DetalheParticipante pessoa={detalhe} versao={versao}
          onRestaurar={detalhe.status === 'ativo' || detalhe.status === 'desistente' ? () => setDesistencia({ pessoa: detalhe, acao: 'restaurar' }) : undefined} />}
      </Drawer>

      {dados && (
        <DesistenciaModal pessoa={desistencia?.pessoa ?? null} acao={desistencia?.acao ?? 'registrar'} dados={dados}
          onClose={() => setDesistencia(null)} onConcluido={concluir} />
      )}

      <ConfirmDialog
        open={!!status}
        onClose={() => setStatus(null)}
        onConfirm={alterarStatus}
        title={status?.acao === 'remover' ? 'Remover do bolão?' : 'Reativar participante?'}
        message={status?.acao === 'remover'
          ? <>A remoção administrativa de <strong>{status.pessoa.nome}</strong> mantém a pessoa, os palpites e o histórico guardados.</>
          : <>Reativar não concede acesso de responsável. Palpites e histórico de <strong>{status?.pessoa.nome}</strong> continuam preservados.</>}
        confirmLabel={status?.acao === 'remover' ? 'Remover' : 'Reativar'}
        danger={status?.acao === 'remover'}
      />
    </div>
  );
}
