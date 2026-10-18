import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { TabelaConteudo } from '@/components/campeonatos/TabelaOficial';
import { Header } from '@/components/layout/Header';
import { AgendaRodada, SeletorVisaoJogos, opcoesDaCompeticao, type VisaoJogos } from '@/components/jogos/AgendaRodada';
import { EstadoRodadaBadge } from '@/components/rodadas/EstadoRodada';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { useRecurso } from '@/lib/useRecurso';
import { api } from '@/lib/api';
import type { AgendaApi, AtualizacaoHorarios, TabelaApi } from '@/types';

export function JogosScreen() {
  const showToast = useToast();
  const [rodadaId, setRodadaId] = useState<number | null>(null);
  const { dados, carregando, erro, recarregar } = useRecurso<AgendaApi>(rodadaId ? `/jogos?rodada_id=${rodadaId}` : '/jogos');
  const [atualizando, setAtualizando] = useState(false);
  const [escolhida, setVisao] = useState<VisaoJogos>('jogos');
  const tabela = useRecurso<TabelaApi>('/tabela');
  const opcoes = opcoesDaCompeticao(tabela.dados);
  const visao = opcoes.includes(escolhida) ? escolhida : 'jogos';
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

  const r = dados?.rodada;

  return (
    <div>
      <Header
        title="Jogos"
        subtitle={visao === 'jogos' ? 'Próxima rodada e jogos atrasados' : visao === 'confrontos' ? 'Chave do mata-mata' : 'Classificação do campeonato agora'}
        actions={visao === 'jogos' && dados?.horarios.configurado ? (
          <button onClick={() => atualizarHorarios(true)} disabled={atualizando} title="Buscar horários oficiais na API"
            className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60 transition-colors">
            <RefreshCw className={`w-4 h-4 ${atualizando ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Atualizar horários</span>
          </button>
        ) : undefined}
      />
      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        <SeletorVisaoJogos visao={visao} onMudar={setVisao} opcoes={opcoes} />
        {visao !== 'jogos' && <TabelaConteudo recurso={tabela} visao={visao} />}
        {visao === 'jogos' && erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {visao === 'jogos' && !dados && carregando && <Carregando linhas={4} />}
        {visao === 'jogos' && dados && r && (
          <AgendaRodada
            agora={dados.agora}
            rodadas={dados.rodadas}
            selecionadaId={rodadaId ?? dados.rodadaAtualId ?? r.id}
            atualId={dados.rodadaAtualId}
            onSelecionar={id => setRodadaId(id === dados.rodadaAtualId ? null : id)}
            onIrAtual={() => setRodadaId(null)}
            rodada={r}
            jogos={dados.jogos}
            atrasados={dados.atrasados}
            carregando={carregando}
            selo={(() => { const e = dados.rodadas.find(x => x.id === r.id); return e ? <EstadoRodadaBadge estado={e.estado} faltantes={e.faltantes} /> : null; })()}
            rodape={(
              <p className="text-xs text-gray-400 text-center">
                {dados.horarios.configurado
                  ? <>Horários oficiais (Brasília) via {dados.horarios.fonte}{dados.horarios.ultimaAtualizacao ? ` · consultado em ${dados.horarios.ultimaAtualizacao}` : ''}</>
                  : 'Configure FOOTBALL_DATA_TOKEN e o código da API do campeonato para buscar os horários oficiais.'}
              </p>
            )}
          />
        )}
        {visao === 'jogos' && dados && !r && <p className="text-sm text-gray-400 text-center py-12">Nenhuma rodada cadastrada neste campeonato.</p>}
      </div>
    </div>
  );
}
