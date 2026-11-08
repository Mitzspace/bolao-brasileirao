import { useCallback, useState } from 'react';
import { Crown, ListFilter, Target, TrendingUp, Users } from 'lucide-react';
import { DesempenhoParticipante } from '@/components/participantes/DesempenhoParticipante';
import { Drawer } from '@/components/ui/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { Switch } from '@/components/ui/Form';
import { useRecurso } from '@/lib/useRecurso';
import type { ClassificacaoBolaoApi } from '@/types';
import { Podio } from './Podio';
import { TabelaClassificacao } from './TabelaClassificacao';

export type ClassificacaoComEliminacao = ClassificacaoBolaoApi & { eliminadosOcultos?: number };

/** Classificação do bolão com os filtros da tela (geral ou por rodada, ocultar desistentes). */
export function useClassificacao(bolaoId: number) {
  const [rodadaId, setRodadaId] = useState('');
  // Desistentes ficam ocultos por padrão (pedido do bolão); o switch mostra quando preciso.
  const [ocultar, setOcultar] = useState(true);
  const params = new URLSearchParams();
  if (rodadaId) params.set('rodada_id', rodadaId);
  if (ocultar) params.set('ocultar_desistentes', '1');
  const recurso = useRecurso<ClassificacaoComEliminacao>(`/boloes/${bolaoId}/classificacao?${params}`);
  return { ...recurso, rodadaId, setRodadaId, ocultar, setOcultar };
}

/** Filtros, pódio e tabela de pontuação; o nome do participante abre o desempenho dele. */
export function CartaoClassificacao({ bolaoId, dados, rodadaId, setRodadaId, ocultar, setOcultar }: {
  bolaoId: number; dados: ClassificacaoComEliminacao; rodadaId: string; setRodadaId: (id: string) => void;
  ocultar: boolean; setOcultar: (ocultar: boolean) => void;
}) {
  const [desempenho, setDesempenho] = useState<{ id: number; nome: string } | null>(null);
  const fecharDesempenho = useCallback(() => setDesempenho(null), []);
  const lider = dados.ranking[0];
  const segundo = dados.ranking[1];
  const craque = dados.ranking.reduce<typeof lider | undefined>((m, p) => (!m || p.cravadas > m.cravadas ? p : m), undefined);
  const resumo = lider ? [
    { rotulo: 'Líder', valor: lider.nome, detalhe: `${lider.pontos} pts`, icone: Crown, cor: 'from-gold-400 to-gold-600' },
    { rotulo: 'Vantagem do líder', valor: segundo ? `${lider.pontos - segundo.pontos} pts` : '—', detalhe: segundo ? `sobre ${segundo.nome.split(' ')[0]}` : 'sem 2º colocado', icone: TrendingUp, cor: 'from-brand-500 to-brand-700' },
    { rotulo: 'Mais cravadas', valor: craque && craque.cravadas > 0 ? craque.nome : '—', detalhe: craque && craque.cravadas > 0 ? `${craque.cravadas} placares exatos` : 'nenhuma ainda', icone: Target, cor: 'from-blue-500 to-blue-700' },
  ] : [];
  return (
    <>
      {/* Filtros */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 px-4 py-3 animate-fade-in">
        <div className="relative">
          <ListFilter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-600 dark:text-brand-400 pointer-events-none" />
          <select value={rodadaId} onChange={e => setRodadaId(e.target.value)} aria-label="Classificação"
            className="w-full sm:w-auto pl-9 pr-8 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm font-semibold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
            <option value="">Classificação geral</option>
            {dados.rodadas.map(r => <option key={r.id} value={r.id}>Somente a {r.nome}</option>)}
          </select>
        </div>
        <span className="hidden sm:inline text-xs text-gray-400">{dados.ranking.length} {dados.ranking.length === 1 ? 'participante' : 'participantes'}</span>
        <div className="sm:ml-auto"><Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" /></div>
      </div>

      {/* Resumo */}
      {resumo.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {resumo.map(r => {
            const Icone = r.icone;
            return (
              <div key={r.rotulo} className="flex items-center gap-3 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-4 min-w-0 cartao-elevavel animate-slide-up">
                <span className={`w-11 h-11 rounded-xl bg-gradient-to-br ${r.cor} text-white flex items-center justify-center shrink-0 shadow-md`}><Icone className="w-5 h-5" /></span>
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">{r.rotulo}</p>
                  <p className="text-base font-extrabold text-gray-900 dark:text-white truncate" title={r.valor}>{r.valor}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{r.detalhe}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden animate-slide-up">
        {!!dados.eliminadosOcultos && <p className="px-5 py-3 text-xs text-gray-500 dark:text-gray-400">{dados.eliminadosOcultos} participantes eliminados nas fases anteriores não aparecem no ranking.</p>}
        {dados.ranking.length === 0 ? (
          <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação" description="Cadastre participantes e lance resultados para ver a classificação." />
        ) : (
          <>
            <div className="p-3 sm:p-4">
              <Podio ranking={dados.ranking} />
            </div>
            <TabelaClassificacao geral={!dados.rodadaId}
              onAbrir={l => setDesempenho({ id: Number(l.chave), nome: l.nome })}
              dicaVariacao={dados.variacaoReferencia ? `Variação após a ${dados.variacaoReferencia}` : undefined}
              itens={dados.ranking.map(p => ({ chave: p.participacaoId, avatarId: p.participacaoId, nome: p.nome, status: p.status,
                posicao: p.posicao, pontos: p.pontos, pontosPalpites: p.pontosPalpites, bonus: p.bonus,
                bonusPrimeiroGol: p.bonusPrimeiroGol, cravadas: p.cravadas, acertos: p.acertosVencedor, variacao: p.variacao }))} />
          </>
        )}
      </div>
      <Drawer open={!!desempenho} onClose={fecharDesempenho} title="Desempenho do participante" width="max-w-xl">
        {desempenho && <DesempenhoParticipante key={`${bolaoId}-${desempenho.id}`} bolaoId={bolaoId} participacaoId={desempenho.id} nome={desempenho.nome} />}
      </Drawer>
    </>
  );
}
