import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Clock, Grid3x3, History, Save, SkipForward, Star, UserCheck } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Badge } from '@/components/ui/Badge';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { useToast } from '@/components/ui/Toast';
import { SeletorRodadas } from '@/components/rodadas/SeletorRodadas';
import { EstadoRodadaBadge } from '@/components/rodadas/EstadoRodada';
import { PreviaWhatsapp, type LinhaAplicada } from '@/components/palpites/PreviaWhatsapp';
import { GradeModal } from '@/components/palpites/GradeModal';
import { useApp } from '@/context/AppContext';
import { api, ApiError } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { JogoLancamento, LancamentoApi, SituacaoPalpite } from '@/types';

interface Valor { casa: string; fora: string; primeiroGol: string; situacao: SituacaoPalpite }

const situacoes: { valor: SituacaoPalpite; texto: string }[] = [
  { valor: 'valido', texto: 'Válido' },
  { valor: 'nao_enviado', texto: 'Não enviou' },
  { valor: 'fora_prazo', texto: 'Fora do prazo (0 pt)' },
];

function valorInicial(j: JogoLancamento): Valor {
  const p = j.palpite;
  return { casa: p?.casa?.toString() ?? '', fora: p?.fora?.toString() ?? '', primeiroGol: p?.primeiroGol ?? '', situacao: p?.situacao ?? 'valido' };
}

export function PalpitesScreen() {
  const showToast = useToast();
  const { parametros } = useApp();
  const [rodadaId, setRodadaId] = useState<number | null>(parametros.rodadaId ?? null);
  const [pessoaId, setPessoaId] = useState<number | null>(parametros.participacaoId ?? null);
  const caminho = `/palpites?${new URLSearchParams({
    ...(rodadaId ? { rodada_id: String(rodadaId) } : {}), ...(pessoaId ? { participacao_id: String(pessoaId) } : {}),
  })}`;
  const { dados, carregando, erro, recarregar } = useRecurso<LancamentoApi>(caminho);

  const [valores, setValores] = useState<Record<number, Valor>>({});
  const [naoEnviou, setNaoEnviou] = useState(false);
  const [recebidoEm, setRecebidoEm] = useState('');
  const [automatico, setAutomatico] = useState(true);
  const [whatsapp, setWhatsapp] = useState<{ token: string; jogos: number[] } | null>(null);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [verPendencias, setVerPendencias] = useState(false);
  const [grade, setGrade] = useState<number | null>(null);
  const campos = useRef<(HTMLInputElement | null)[]>([]);

  // Ao carregar outra pessoa/rodada, o formulário volta aos palpites gravados.
  const chaveForm = dados ? `${dados.rodada?.id}-${dados.pessoa?.id}` : '';
  useEffect(() => {
    if (!dados) return;
    setValores(Object.fromEntries(dados.jogos.map(j => [j.id, valorInicial(j)])));
    setNaoEnviou(false); setRecebidoEm(''); setWhatsapp(null); setErros({});
    if (dados.pessoa && dados.pessoa.id !== pessoaId) setPessoaId(dados.pessoa.id);
    if (dados.rodada && rodadaId === null) setRodadaId(dados.rodada.id);
    setTimeout(() => {
      const vazio = campos.current.findIndex(c => c && !c.disabled && c.value === '');
      campos.current[vazio >= 0 ? vazio : 0]?.focus();
    }, 50);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chaveForm]);

  const editaveis = useMemo(() => dados?.jogos.filter(j => !j.palpite?.guardado) ?? [], [dados]);
  const alterar = (id: number, parcial: Partial<Valor>) => {
    setValores(v => ({ ...v, [id]: { ...v[id], ...parcial } }));
    setErros(e => { const { [String(id)]: _, ...resto } = e; return resto; });
  };

  const salvar = async (acao: 'ficar' | 'proximo') => {
    if (!dados?.pessoa || !dados.rodada) return;
    setSalvando(true);
    const jogos: Record<string, Partial<Valor>> = {};
    for (const j of editaveis) {
      const v = valores[j.id];
      jogos[j.id] = { casa: v.casa, fora: v.fora, situacao: v.situacao, ...(j.classico ? { primeiroGol: v.primeiroGol } : {}) };
    }
    try {
      const r = await api.post<{ mensagem: string; avisos: string[]; proximoId: number | null }>('/palpites', {
        participacaoId: dados.pessoa.id, rodadaId: dados.rodada.id, acao, jogos,
        naoEnviouRodada: naoEnviou, recebidoEm, whatsappToken: whatsapp?.token, whatsappJogos: whatsapp?.jogos.join(','),
      });
      showToast(r.mensagem);
      r.avisos.forEach(a => showToast(a, 'info'));
      if (r.proximoId) setPessoaId(r.proximoId);
      else await recarregar();
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        setErros((e.dados.erros as Record<string, string>) ?? {});
        showToast(e.message, 'error');
      } else showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    } finally { setSalvando(false); }
  };

  const aplicarWhatsapp = (linhas: LinhaAplicada[], token: string) => {
    setValores(v => {
      const novo = { ...v };
      for (const l of linhas) novo[l.jogoId] = { ...novo[l.jogoId], casa: l.casa, fora: l.fora, situacao: 'valido', ...(l.primeiroGol ? { primeiroGol: l.primeiroGol } : {}) };
      return novo;
    });
    setWhatsapp({ token, jogos: linhas.map(l => l.jogoId) });
  };

  const teclado = (indice: number) => ({
    onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Backspace' && e.currentTarget.value === '') { e.preventDefault(); campos.current[indice - 1]?.focus(); }
      if (e.key === 'Enter') { e.preventDefault(); void salvar('ficar'); }
    },
    onInput: (e: React.FormEvent<HTMLInputElement>) => {
      const ev = e.nativeEvent as InputEvent;
      if (automatico && /^[0-9]$/.test(e.currentTarget.value) && ev.inputType !== 'deleteContentBackward') {
        // Foco imediato: digitação rápida não perde dígitos.
        const prox = campos.current.slice(indice + 1).find(c => c && !c.disabled);
        prox?.focus();
        prox?.select();
      }
    },
  });

  const pessoa = dados?.pessoa;
  const pendentes = dados?.participantes.filter(p => p.faltantes > 0) ?? [];
  let indiceCampo = -1;

  return (
    <div>
      <Header title="Lançar palpites" subtitle={dados?.rodada ? `${dados.rodada.nome}${pessoa ? ` · ${pessoa.nome}` : ''}` : 'Todos os jogos da rodada em um único lançamento'}
        actions={dados?.rodada ? (
          <button onClick={() => setGrade(dados.rodada?.id ?? null)} title="Ver grade de palpites"
            className="flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Grid3x3 className="w-4 h-4" /><span className="hidden sm:inline">Grade</span>
          </button>
        ) : undefined} />
      <GradeModal rodadaId={grade} onClose={() => setGrade(null)} />

      <div className="p-4 md:p-8 pb-44 md:pb-32 space-y-4">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={5} />}
        {dados && !dados.rodada && <p className="text-sm text-gray-400 text-center py-12">Nenhuma rodada cadastrada.</p>}

        {dados?.rodada && (
          <>
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-3 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
              <SeletorRodadas rodadas={dados.rodadas} selecionadaId={rodadaId ?? dados.rodada.id} atualId={null}
                onSelecionar={id => { setRodadaId(id); setPessoaId(null); }} />
            </div>

            {/* Participante */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-800 space-y-3">
              <div className="flex items-center gap-2">
                <button onClick={() => pessoa?.anteriorId && setPessoaId(pessoa.anteriorId)} disabled={!pessoa?.anteriorId} aria-label="Participante anterior"
                  className="shrink-0 w-10 h-10 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-center disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-gray-800"><ChevronLeft className="w-5 h-5" /></button>
                <select value={pessoa?.id ?? ''} onChange={e => setPessoaId(Number(e.target.value))} aria-label="Participante"
                  className="flex-1 min-w-0 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500/40">
                  {dados.participantes.map(p => (
                    <option key={p.id} value={p.id}>{p.nome}{p.status === 'desistente' ? ' (desistente)' : ''} · {p.faltantes ? `${p.faltantes} faltando` : 'completo ✓'}</option>
                  ))}
                </select>
                <button onClick={() => pessoa?.proximaId && setPessoaId(pessoa.proximaId)} disabled={!pessoa?.proximaId} aria-label="Próximo participante"
                  className="shrink-0 w-10 h-10 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-center disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-gray-800"><ChevronRight className="w-5 h-5" /></button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <EstadoRodadaBadge estado={dados.rodada.estado} faltantes={dados.rodada.faltantes} />
                <button onClick={() => setVerPendencias(v => !v)} className="text-xs font-semibold text-brand-700 dark:text-brand-300 hover:underline">
                  {pendentes.length ? `${pendentes.length} participante(s) com pendência` : 'Todos completos nesta rodada'} {pendentes.length ? (verPendencias ? '▴' : '▾') : ''}
                </button>
              </div>
              {verPendencias && pendentes.length > 0 && (
                <div className="flex flex-wrap gap-1.5 animate-fade-in">
                  {pendentes.map(p => (
                    <button key={p.id} onClick={() => setPessoaId(p.id)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border ${p.id === pessoa?.id ? 'bg-brand-600 border-brand-600 text-white' : 'border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:border-red-300'}`}>
                      {p.nome} · {p.faltantes}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {pessoa && (
              <>
                <PreviaWhatsapp key={chaveForm} participacaoId={pessoa.id} rodadaId={dados.rodada.id} nome={pessoa.nome} rodadaNome={dados.rodada.nome} onAplicar={aplicarWhatsapp} />

                {/* Opções do lote */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-800 grid sm:grid-cols-2 gap-4">
                  <Switch checked={naoEnviou} onChange={setNaoEnviou} label="Não enviou nenhum palpite" description="Registra todos os jogos como não enviados (zero pontos), inclusive os já lançados" />
                  <Switch checked={automatico} onChange={setAutomatico} label="Avanço automático" description="Um dígito pula para o próximo campo; Backspace volta; Enter salva" />
                  <div className="sm:col-span-2">
                    <label htmlFor="recebido-em" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Recebido em (opcional, horário de São Paulo)</label>
                    <input id="recebido-em" type="datetime-local" value={recebidoEm} onChange={e => setRecebidoEm(e.target.value)}
                      className={`w-full sm:w-auto px-4 py-2.5 rounded-xl border bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 ${erros.recebido_em ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'}`} />
                    {erros.recebido_em && <p className="mt-1 text-xs text-red-500">{erros.recebido_em}</p>}
                    <p className="mt-1 text-xs text-gray-400">Aplicado aos palpites deste lote. Em branco, mantém a data já registrada. Campos vazios não apagam palpites.</p>
                  </div>
                </div>

                {Object.keys(erros).length > 0 && (
                  <div role="alert" className="flex items-start gap-2 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/40 p-3 text-sm text-red-700 dark:text-red-300">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <div>Nada foi salvo. Corrija os campos indicados e salve novamente.{erros.whatsapp && <p className="mt-1">{erros.whatsapp}</p>}</div>
                  </div>
                )}

                {/* Jogos */}
                <div className={`space-y-3 transition-opacity ${carregando ? 'opacity-60' : ''} ${naoEnviou ? 'opacity-50 pointer-events-none' : ''}`}>
                  {dados.jogos.map(j => {
                    const v = valores[j.id] ?? valorInicial(j);
                    const guardado = !!j.palpite?.guardado;
                    const valido = v.situacao === 'valido';
                    const iCasa = ++indiceCampo; const iFora = ++indiceCampo;
                    const erroJogo = erros[String(j.id)];
                    const temResultado = j.golsCasa !== null && j.golsFora !== null;
                    return (
                      <div key={j.id} className={`bg-white dark:bg-gray-900 rounded-2xl p-4 shadow-sm border ${erroJogo ? 'border-red-300 dark:border-red-800' : 'border-gray-100 dark:border-gray-800'}`}>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400 mb-3">
                          <span className="font-bold text-gray-500">{j.numero}</span>
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{j.dataTexto ?? 'Horário a definir'}</span>
                          {j.classico && <Badge color="gold" icon={<Star className="w-3 h-3" />}>Clássico</Badge>}
                          {j.iniciado && <Badge color="yellow">Iniciado — lançamento auditado</Badge>}
                          {j.palpite && !guardado && <Badge color="green" icon={<UserCheck className="w-3 h-3" />}>Já lançado</Badge>}
                          {guardado && <Badge color="red" icon={<History className="w-3 h-3" />}>Após desistência · guardado</Badge>}
                        </div>
                        <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sm:gap-4">
                          <div className="flex items-center justify-end gap-2 min-w-0">
                            <span className="font-semibold text-sm text-gray-900 dark:text-white truncate text-right"><span className="hidden sm:inline">{j.casa}</span><span className="sm:hidden">{j.escudoCasa.sigla}</span></span>
                            <TeamCrest nome={j.casa} escudo={j.escudoCasa} size="sm" />
                          </div>
                          <div className="flex items-center gap-2">
                            {(['casa', 'fora'] as const).map((lado, k) => (
                              <span key={lado} className="contents">
                                {k === 1 && <span className="text-gray-300 text-lg">×</span>}
                                <input ref={el => { campos.current[k === 0 ? iCasa : iFora] = el; }} type="text" inputMode="numeric" autoComplete="off"
                                  value={valido ? v[lado] : ''} disabled={guardado || !valido} maxLength={10}
                                  onChange={e => alterar(j.id, { [lado]: e.target.value.replace(/\D/g, '') })} {...teclado(k === 0 ? iCasa : iFora)}
                                  onFocus={e => e.currentTarget.select()}
                                  aria-label={`Gols de ${lado === 'casa' ? j.casa : j.fora} no jogo ${j.numero}`} aria-invalid={erroJogo ? true : undefined}
                                  className="w-14 h-14 text-2xl font-bold text-center rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 disabled:bg-gray-50 disabled:dark:bg-gray-800/50 disabled:text-gray-300" />
                              </span>
                            ))}
                          </div>
                          <div className="flex items-center gap-2 min-w-0">
                            <TeamCrest nome={j.fora} escudo={j.escudoFora} size="sm" />
                            <span className="font-semibold text-sm text-gray-900 dark:text-white truncate"><span className="hidden sm:inline">{j.fora}</span><span className="sm:hidden">{j.escudoFora.sigla}</span></span>
                          </div>
                        </div>

                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <select value={v.situacao} disabled={guardado} onChange={e => alterar(j.id, { situacao: e.target.value as SituacaoPalpite })}
                            aria-label={`Situação do palpite no jogo ${j.numero}`}
                            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500/40 ${valido ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300' : 'border-red-200 bg-red-50 text-red-700 dark:bg-red-900/20 dark:border-red-900/50 dark:text-red-300'}`}>
                            {situacoes.map(s => <option key={s.valor} value={s.valor}>{s.texto}</option>)}
                          </select>
                          {j.classico && (
                            <input value={v.primeiroGol} disabled={guardado || !valido} maxLength={100} onChange={e => alterar(j.id, { primeiroGol: e.target.value })}
                              placeholder="Primeiro gol (opcional)" aria-label={`Primeiro gol no jogo ${j.numero}`}
                              className="flex-1 min-w-[10rem] px-3 py-1.5 rounded-lg border border-gold-200 dark:border-gold-800/50 bg-gold-50/50 dark:bg-gold-900/10 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gold-400/40" />
                          )}
                          <span className="ml-auto text-xs text-gray-500">
                            {temResultado
                              ? <>Resultado {j.golsCasa} × {j.golsFora}{j.palpite?.pontos != null && <> · <strong className={j.palpite.pontos > 0 ? 'text-brand-600' : 'text-gray-500'}>{j.palpite.pontos} pt</strong></>}</>
                              : 'Aguardando resultado'}
                          </span>
                        </div>
                        {erroJogo && <p role="alert" className="mt-2 text-xs text-red-500">{erroJogo}</p>}
                        {guardado && <p className="mt-2 text-xs text-gray-500">Palpite guardado após desistência. A restauração é feita no histórico do participante.</p>}
                      </div>
                    );
                  })}
                  {dados.jogos.length === 0 && <p className="text-sm text-gray-400 text-center py-8">Esta rodada não possui jogos cadastrados.</p>}
                </div>
              </>
            )}
          </>
        )}
      </div>

      {/* Barra de salvar fixa */}
      {pessoa && dados?.jogos.length ? (
        <div className="fixed bottom-16 md:bottom-0 left-0 md:left-64 right-0 z-30 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-t border-gray-100 dark:border-gray-800 px-4 md:px-8 py-3 flex items-center gap-2">
          <p className="hidden sm:flex items-center gap-1.5 text-xs text-gray-400 flex-1 min-w-0">
            {whatsapp ? <><CheckCircle2 className="w-4 h-4 text-brand-500" /> Preenchido pela mensagem do WhatsApp</> : <>Enter salva e fica · o próximo pula quem já está completo</>}
          </p>
          <button onClick={() => salvar('ficar')} disabled={salvando} className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60">
            <Save className="w-4 h-4" /> Salvar
          </button>
          <button onClick={() => salvar('proximo')} disabled={salvando} className="flex-[2] sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-60">
            {salvando ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <SkipForward className="w-4 h-4" />} Salvar e próximo
          </button>
        </div>
      ) : null}
    </div>
  );
}
