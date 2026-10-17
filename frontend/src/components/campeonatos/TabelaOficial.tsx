import { AlertCircle, Info, Table2 } from 'lucide-react';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { EmptyState } from '@/components/ui/EmptyState';
import { useRecurso } from '@/lib/useRecurso';
import type { TabelaApi } from '@/types';

const statusMataMata: Record<string, string> = {
  FINISHED: 'Finalizado', SCHEDULED: 'Agendado', TIMED: 'Agendado', IN_PLAY: 'Em andamento', PAUSED: 'Intervalo',
  POSTPONED: 'Adiado', SUSPENDED: 'Suspenso', CANCELLED: 'Cancelado', AWARDED: 'Resultado definido',
};

// Colunas congeladas na rolagem lateral: largura fixa, fundo opaco (inclusive no hover) e separador.
const COL_POS = 'sticky left-0 w-12 min-w-[3rem] max-w-[3rem] pl-4 sm:pl-5 pr-1';
const COL_TIME = 'sticky left-12 w-[9.5rem] min-w-[9.5rem] max-w-[9.5rem] sm:w-auto sm:max-w-none';
const FIXA = 'z-[1] bg-white dark:bg-gray-900';
const FIXA_HOVER = 'group-hover:bg-gray-50 dark:group-hover:bg-gray-800';
const SEPARADOR = 'shadow-[inset_-1px_0_0_#f3f4f6,6px_0_8px_-6px_rgba(0,0,0,0.18)] dark:shadow-[inset_-1px_0_0_#1f2937,6px_0_8px_-6px_rgba(0,0,0,0.7)]';

/** Tabela do campeonato (football-data.org, com cache de 15 min no servidor). */
export function TabelaOficial() {
  const { dados, carregando, erro, recarregar } = useRecurso<TabelaApi>('/tabela');
  if (erro) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return carregando ? <Carregando linhas={6} /> : null;

  return (
    <div className="space-y-4">
      {dados.aviso && (
        <p className="flex items-start gap-2 rounded-xl bg-gold-50 dark:bg-gold-900/20 border border-gold-200 dark:border-gold-800/40 p-3 text-sm text-gold-800 dark:text-gold-300">
          <Info className="w-4 h-4 mt-0.5 shrink-0" />{dados.aviso}
        </p>
      )}
      {!dados.sucesso && dados.erro && (
        <p className="flex items-start gap-2 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 p-3 text-sm text-red-700 dark:text-red-300">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />{dados.erro}
        </p>
      )}

      {dados.grupos.map(grupo => (
        <div key={grupo.nome} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <h3 className="font-bold text-gray-900 dark:text-white">{grupo.nome}</h3>
            <span className="text-xs text-gray-400">{grupo.linhas.length} equipes</span>
          </div>
          {/* Rolagem lateral no celular: posição e time ficam congelados à esquerda. */}
          <div className="relative overflow-x-auto scrollbar-thin overscroll-x-contain">
            <table className="w-full text-sm min-w-[30rem] sm:min-w-0">
              <thead>
                <tr className="text-xs text-gray-400 uppercase">
                  <th className={`${COL_POS} ${FIXA} z-[2] text-left py-3 font-semibold`}>#</th>
                  <th className={`${COL_TIME} ${FIXA} ${SEPARADOR} z-[2] text-left py-3 px-2 font-semibold`}>Time</th>
                  <th className="py-3 px-2 font-semibold">P</th>
                  <th className="py-3 px-2 font-semibold">J</th>
                  <th className="py-3 px-2 font-semibold">V</th>
                  <th className="py-3 px-2 font-semibold">E</th>
                  <th className="py-3 px-2 font-semibold">D</th>
                  <th className="py-3 px-2 font-semibold hidden sm:table-cell">GP</th>
                  <th className="py-3 px-2 font-semibold hidden sm:table-cell">GC</th>
                  <th className="py-3 pl-2 pr-5 font-semibold">SG</th>
                </tr>
              </thead>
              <tbody>
                {grupo.linhas.map(l => (
                  <tr key={l.posicao + l.time} className="group border-t border-gray-50 dark:border-gray-800/60 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors" title={l.zona?.nome}>
                    <td className={`${COL_POS} ${FIXA} ${FIXA_HOVER} py-2.5`} style={l.zona ? { boxShadow: `inset 3px 0 0 ${l.zona.cor}` } : undefined}>
                      <span className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-[11px] font-bold ${l.zona ? 'text-white' : 'text-gray-500'}`} style={l.zona ? { backgroundColor: l.zona.cor } : undefined}>{l.posicao}</span>
                    </td>
                    <td className={`${COL_TIME} ${FIXA} ${FIXA_HOVER} ${SEPARADOR} py-2.5 px-2`}>
                      <div className="flex items-center gap-2.5 min-w-0">
                        <TeamCrest nome={l.time} escudo={l.escudo} size="xs" />
                        <span className="font-medium text-gray-900 dark:text-white truncate" title={l.timeCompleto}>{l.time}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-2 text-center font-bold text-brand-600 dark:text-brand-400">{l.pontos}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500">{l.jogos}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500">{l.vitorias}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500">{l.empates}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500">{l.derrotas}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500 hidden sm:table-cell">{l.golsPro}</td>
                    <td className="py-2.5 px-2 text-center text-gray-500 hidden sm:table-cell">{l.golsContra}</td>
                    <td className={`py-2.5 pl-2 pr-5 text-center font-semibold ${l.saldo > 0 ? 'text-brand-600' : l.saldo < 0 ? 'text-red-500' : 'text-gray-500'}`}>{l.saldo > 0 ? `+${l.saldo}` : l.saldo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {dados.mataMata.map(fase => (
        <div key={fase.nome} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-5">
          <h3 className="font-bold text-gray-900 dark:text-white mb-3">{fase.nome}</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {fase.jogos.map((j, i) => (
              <div key={j.id ?? `${j.casa}-${j.fora}-${i}`} className="rounded-xl border border-gray-100 dark:border-gray-800 p-3 text-sm">
                <p className="text-xs text-gray-400 mb-2">{j.horario ?? 'Horário a definir'} · {statusMataMata[j.status] ?? 'A definir'}</p>
                <div className="flex justify-between"><span>{j.casa}</span><strong>{j.gols_casa ?? '—'}</strong></div>
                <div className="flex justify-between mt-1"><span>{j.fora}</span><strong>{j.gols_fora ?? '—'}</strong></div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {dados.sucesso && !dados.grupos.length && !dados.mataMata.length && (
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800">
          <EmptyState icon={<Table2 className="w-10 h-10" />} title="Tabela indisponível" description="A API ainda não publicou a classificação desta temporada." />
        </div>
      )}

      {dados.legendas.length > 0 && (
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-500 dark:text-gray-400">
          {dados.legendas.map(z => (
            <span key={z.nome} className="inline-flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: z.cor }} />
              {z.nome} ({z.de}º{z.de !== z.ate ? `–${z.ate}º` : ''})
            </span>
          ))}
        </div>
      )}
      <p className="text-xs text-gray-400">
        Fonte: football-data.org{dados.fonteCache && dados.horarioCache ? ` · dados do cache, atualizados às ${dados.horarioCache}` : ''}
      </p>
    </div>
  );
}
