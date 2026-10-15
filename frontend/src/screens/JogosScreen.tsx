import { useCallback, useEffect, useRef, useState } from 'react';
import { AlarmClock, CalendarClock, History, RefreshCw, CheckCircle2, ListOrdered, Table2 } from 'lucide-react';
import { TabelaOficial } from '@/components/campeonatos/TabelaOficial';
import { Header } from '@/components/layout/Header';
import { JogoLinha } from '@/components/jogos/JogoLinha';
import { SeletorRodadas } from '@/components/rodadas/SeletorRodadas';
import { EstadoRodadaBadge } from '@/components/rodadas/EstadoRodada';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { useRecurso } from '@/lib/useRecurso';
import { api } from '@/lib/api';
import type { AgendaApi, AtualizacaoHorarios } from '@/types';

/** Datas chegam no horário de Brasília sem fuso; a diferença usa o "agora" do servidor. */
function lerData(valor: string) {
  const [d, h = '00:00:00'] = valor.split('T');
  const [a, m, dia] = d.split('-').map(Number);
  const [hh, mm] = h.split(':').map(Number);
  return Date.UTC(a, m - 1, dia, hh, mm);
}

function situacaoRodada(dados: AgendaApi) {
  const r = dados.rodada;
  if (!r) return null;
  const encerrados = dados.jogos.filter(j => j.status === 'encerrado').length;
  if (dados.jogos.length && encerrados === dados.jogos.length) return { texto: 'Rodada encerrada', cor: 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' };
  if (!r.inicio) return { texto: 'Horários a definir', cor: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' };
  const minutos = Math.round((lerData(r.inicio) - lerData(dados.agora)) / 60000);
  if (minutos <= 0) return { texto: 'Em andamento', cor: 'bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300' };
  const dias = Math.floor(minutos / 1440);
  const horas = Math.floor((minutos % 1440) / 60);
  const texto = dias > 0 ? `Começa em ${dias} ${dias === 1 ? 'dia' : 'dias'}${horas ? ` e ${horas} h` : ''}`
    : horas > 0 ? `Começa em ${horas} h ${minutos % 60} min` : `Começa em ${minutos} min`;
  return { texto, cor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' };
}

export function JogosScreen() {
  const showToast = useToast();
  const [rodadaId, setRodadaId] = useState<number | null>(null);
  const { dados, carregando, erro, recarregar } = useRecurso<AgendaApi>(rodadaId ? `/jogos?rodada_id=${rodadaId}` : '/jogos');
  const [atualizando, setAtualizando] = useState(false);
  const [visao, setVisao] = useState<'jogos' | 'tabela'>('jogos');
  const automatico = useRef(false);

  const atualizarHorarios = useCallback(async (forcar: boolean) => {
    setAtualizando(true);
    try {
      const r = await api.post<AtualizacaoHorarios>('/horarios/atualizar', { forcar });
      if (r.status === 'ok') {
        if (r.horariosAtualizados) await recarregar();
        if (forcar || r.horariosAtualizados) {
          showToast(r.horariosAtualizados ? `${r.horariosAtualizados} horários atualizados pela API.` : 'Horários já estavam em dia.');
        }
      } else if (r.status === 'recente') {
        if (forcar) showToast('Os horários foram consultados há pouco. Tente novamente em alguns minutos.', 'info');
      } else if (forcar || r.status === 'erro') {
        showToast(r.mensagem ?? 'Não foi possível atualizar os horários.', r.status === 'erro' ? 'error' : 'warning');
      }
    } catch (e) {
      if (forcar) showToast(e instanceof Error ? e.message : 'Erro ao atualizar horários.', 'error');
    } finally {
      setAtualizando(false);
    }
  }, [recarregar, showToast]);

  // Ao abrir a aba, busca os horários na API (o servidor limita a frequência).
  useEffect(() => {
    if (automatico.current) return;
    automatico.current = true;
    void atualizarHorarios(false);
  }, [atualizarHorarios]);

  const situacao = dados ? situacaoRodada(dados) : null;
  const r = dados?.rodada;

  return (
    <div>
      <Header
        title="Jogos"
        subtitle={visao === 'tabela' ? 'Classificação do campeonato agora' : 'Próxima rodada e jogos atrasados'}
        actions={visao === 'jogos' && dados?.horarios.configurado ? (
          <button onClick={() => atualizarHorarios(true)} disabled={atualizando} title="Buscar horários oficiais na API"
            className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60 transition-colors">
            <RefreshCw className={`w-4 h-4 ${atualizando ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Atualizar horários</span>
          </button>
        ) : undefined}
      />
      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        <div role="tablist" aria-label="Visualização" className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit">
          {([['jogos', 'Jogos', ListOrdered], ['tabela', 'Tabela agora', Table2]] as const).map(([id, label, Icon]) => (
            <button key={id} role="tab" aria-selected={visao === id} onClick={() => setVisao(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${visao === id ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'}`}>
              <Icon className="w-4 h-4" />{label}
            </button>
          ))}
        </div>
        {visao === 'tabela' && <TabelaOficial />}
        {visao === 'jogos' && erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {visao === 'jogos' && !dados && carregando && <Carregando linhas={4} />}
        {visao === 'jogos' && dados && r && (
          <>
            {/* Navegação rápida entre rodadas */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-3 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
              <SeletorRodadas rodadas={dados.rodadas} selecionadaId={rodadaId ?? dados.rodadaAtualId ?? r.id} atualId={dados.rodadaAtualId}
                onSelecionar={id => setRodadaId(id === dados.rodadaAtualId ? null : id)} />
            </div>

            {/* Destaque da rodada */}
            <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden animate-fade-in">
              <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4" />
              <div className="relative flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
                <div>
                  <p className="text-white/80 text-sm">{r.atual ? 'Rodada atual' : 'Rodada selecionada'}{r.numero ? ` · ${r.numero}/${r.total}` : ''}</p>
                  <h2 className="text-2xl font-bold mt-1">{r.nome}</h2>
                  <p className="text-white/90 text-sm mt-2 flex items-center gap-2">
                    <CalendarClock className="w-4 h-4 shrink-0" />
                    {r.inicioTexto ? <>Início: <strong>{r.inicioTexto}</strong>{r.fimTexto && r.fimTexto !== r.inicioTexto ? <> · último jogo: {r.fimTexto}</> : null}</> : 'Horários ainda não divulgados'}
                  </p>
                  {r.semHorario > 0 && r.inicioTexto && (
                    <p className="text-white/70 text-xs mt-1">{r.semHorario} {r.semHorario === 1 ? 'jogo ainda sem horário' : 'jogos ainda sem horário'}</p>
                  )}
                </div>
                {situacao && <span className={`self-start sm:self-auto inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${situacao.cor}`}>{situacao.texto}</span>}
              </div>
            </div>

            {/* Jogos da rodada */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-4">
                <h3 className="font-bold text-gray-900 dark:text-white truncate">Jogos — {r.nome}</h3>
                <div className="flex items-center gap-2 shrink-0">
                  {!r.atual && dados.rodadaAtualId && (
                    <button onClick={() => setRodadaId(null)} className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline">Ir para a atual</button>
                  )}
                  {(() => { const e = dados.rodadas.find(x => x.id === r.id); return e ? <EstadoRodadaBadge estado={e.estado} faltantes={e.faltantes} /> : null; })()}
                </div>
              </div>
              <div className={`space-y-1 transition-opacity ${carregando ? 'opacity-50' : ''}`}>
                {dados.jogos.length ? dados.jogos.map(j => <JogoLinha key={j.id} jogo={j} mostrarData />) : (
                  <p className="text-sm text-gray-400 text-center py-8">Nenhum jogo cadastrado nesta rodada.</p>
                )}
              </div>
            </div>

            {/* Jogos atrasados */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-red-500" />
                  <h3 className="font-bold text-gray-900 dark:text-white">Jogos atrasados</h3>
                </div>
                {dados.atrasados.length > 0 && (
                  <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
                    <AlarmClock className="w-3 h-3" /> {dados.atrasados.length}
                  </span>
                )}
              </div>
              {dados.atrasados.length === 0 ? (
                <div className="flex flex-col items-center py-6 text-center">
                  <CheckCircle2 className="w-10 h-10 text-brand-300 mb-2" />
                  <p className="text-sm text-gray-400">Nenhum jogo atrasado. Todas as rodadas anteriores têm resultado.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dados.atrasados.map(j => (
                    <div key={j.id} className="rounded-xl border border-gray-100 dark:border-gray-800">
                      <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase tracking-wide">{j.rodadaNome}</p>
                      <JogoLinha jogo={j} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <p className="text-xs text-gray-400 text-center">
              {dados.horarios.configurado
                ? <>Horários oficiais (Brasília) via {dados.horarios.fonte}{dados.horarios.ultimaAtualizacao ? ` · consultado em ${dados.horarios.ultimaAtualizacao}` : ''}</>
                : 'Configure FOOTBALL_DATA_TOKEN e o código da API do campeonato para buscar os horários oficiais.'}
            </p>
          </>
        )}
        {visao === 'jogos' && dados && !r && <p className="text-sm text-gray-400 text-center py-12">Nenhuma rodada cadastrada neste campeonato.</p>}
      </div>
    </div>
  );
}
