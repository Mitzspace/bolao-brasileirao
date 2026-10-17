import { useState } from 'react';
import { CalendarCheck, CalendarX, ChevronDown, History, Mail, Shield } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { useRecurso } from '@/lib/useRecurso';
import type { DetalheParticipanteApi, ParticipanteApi } from '@/types';
import { PainelDesempenho } from './PainelDesempenho';
import { StatusBadge } from './StatusBadge';

/** Conteúdo do painel lateral de detalhes (Bolt), com dados reais do bolão. */
export function DetalheParticipante({ pessoa, versao, onRestaurar }: { pessoa: ParticipanteApi; versao: number; onRestaurar?: () => void }) {
  const { dados, carregando, erro, recarregar } = useRecurso<DetalheParticipanteApi>(`/participantes/${pessoa.id}?v=${versao}`);
  const [verHistorico, setVerHistorico] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Avatar nome={pessoa.nome} id={pessoa.id} size="lg" />
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white break-words">{pessoa.nome}</h3>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {pessoa.responsavel && <Badge color="purple" icon={<Shield className="w-3 h-3" />}>Responsável</Badge>}
            <StatusBadge status={pessoa.status} />
            {pessoa.duplicado && <Badge color="yellow">Registro {pessoa.id}</Badge>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800 min-w-0 col-span-2 sm:col-span-1">
          <p className="text-xs text-gray-400 mb-1 flex items-center gap-1"><Mail className="w-3 h-3" />E-mail</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{pessoa.email || '—'}</p>
        </div>
        <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800 col-span-2 sm:col-span-1">
          <p className="text-xs text-gray-400 mb-1 flex items-center gap-1"><CalendarCheck className="w-3 h-3" />Entrada</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{pessoa.rodadaEntrada?.nome ?? 'Histórico preservado'}</p>
        </div>
        {pessoa.rodadaDesistencia && (
          <div className="p-3 rounded-xl bg-gold-50 dark:bg-gold-900/20 col-span-2">
            <p className="text-xs text-gold-700 dark:text-gold-300 mb-1 flex items-center gap-1"><CalendarX className="w-3 h-3" />Desistência</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">A partir da {pessoa.rodadaDesistencia.nome}</p>
            {pessoa.motivoDesistencia && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 break-words">{pessoa.motivoDesistencia}</p>}
          </div>
        )}
        {pessoa.observacao && (
          <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800 col-span-2">
            <p className="text-xs text-gray-400 mb-1">Observação</p>
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">{pessoa.observacao}</p>
          </div>
        )}
      </div>

      <PainelDesempenho
        resumo={{ pontos: pessoa.pontos, cravadas: pessoa.cravadas, posicao: pessoa.posicao, variacao: pessoa.variacao }}
        evolucao={dados ? dados.evolucao.map(e => ({ ...e, chave: e.rodadaId })) : null}
        carregando={carregando} erro={erro} onTentar={recarregar} />

      {dados && (
        <>
          {dados.guardados.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Palpites guardados após desistência</h4>
              <p className="text-xs text-gray-400 mb-3">Fora da pontuação até uma restauração confirmada. Nenhum registro foi apagado.</p>
              <div className="rounded-xl border border-gray-100 dark:border-gray-800 divide-y divide-gray-50 dark:divide-gray-800">
                {dados.guardados.map(g => (
                  <div key={g.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                    <span className="text-xs text-gray-400 w-20 shrink-0">{g.rodada}</span>
                    <span className="flex-1 min-w-0 truncate text-gray-700 dark:text-gray-300">{g.jogo}</span>
                    <span className="font-semibold">{g.palpite}</span>
                  </div>
                ))}
              </div>
              {onRestaurar && (
                <button onClick={onRestaurar} className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <History className="w-4 h-4" /> Revisar e restaurar palpites
                </button>
              )}
            </div>
          )}

          <div>
            <button onClick={() => setVerHistorico(v => !v)} aria-expanded={verHistorico}
              className="w-full flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
              <History className="w-4 h-4" /> Histórico de alterações ({dados.historico.length})
              <ChevronDown className={`w-4 h-4 ml-auto transition-transform ${verHistorico ? 'rotate-180' : ''}`} />
            </button>
            {verHistorico && (
              <div className="mt-3 space-y-2 animate-fade-in">
                <p className="text-xs text-gray-400">Horários de São Paulo.</p>
                {dados.historico.length === 0 && <p className="text-sm text-gray-400">Nenhuma mudança registrada desde a criação do histórico.</p>}
                {dados.historico.map((log, i) => (
                  <div key={i} className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-sm">
                    <p className="font-medium text-gray-900 dark:text-white">{log.acao} <span className="font-normal text-gray-400">· {log.quando} · {log.autor}</span></p>
                    {log.mudancas.map(([campo, antes, depois]) => (
                      <p key={campo} className="text-xs text-gray-500 dark:text-gray-400 mt-1 break-words">
                        <strong>{campo}:</strong> {antes ?? '—'} → {depois ?? '—'}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
