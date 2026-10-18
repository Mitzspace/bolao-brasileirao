import { useState } from 'react';
import { AlertCircle, CalendarDays, Info, Table2, Users } from 'lucide-react';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { EmptyState } from '@/components/ui/EmptyState';
import { JogoLinha } from '@/components/jogos/JogoLinha';
import { Chaveamento } from '@/components/campeonatos/Chaveamento';
import { ehMataMata, fasesDaChave } from '@/lib/chaveamento';
import { useRecurso } from '@/lib/useRecurso';
import type { TabelaApi } from '@/types';

// Colunas congeladas na rolagem lateral: largura fixa, fundo opaco (inclusive no hover) e separador.
const COL_POS = 'sticky left-0 w-12 min-w-[3rem] max-w-[3rem] pl-4 sm:pl-5 pr-1';
const COL_TIME = 'sticky left-12 w-[9.5rem] min-w-[9.5rem] max-w-[9.5rem] sm:w-auto sm:max-w-none';
const FIXA = 'z-[1] bg-white dark:bg-gray-900';
const FIXA_HOVER = 'group-hover:bg-gray-50 dark:group-hover:bg-gray-800';
const SEPARADOR = 'shadow-[inset_-1px_0_0_#f3f4f6,6px_0_8px_-6px_rgba(0,0,0,0.18)] dark:shadow-[inset_-1px_0_0_#1f2937,6px_0_8px_-6px_rgba(0,0,0,0.7)]';

const cartao = 'bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800';

type Aba = 'grupos' | 'confrontos';

export interface RecursoTabela {
  dados: TabelaApi | null; carregando: boolean; erro: string | null; recarregar: () => Promise<void>;
}

/** Tabela do campeonato: grupos (classificação) e confrontos (jogos por fase). Cache de 15 min no servidor. */
export function TabelaOficial() {
  return <TabelaConteudo recurso={useRecurso<TabelaApi>('/tabela')} />;
}

/**
 * Conteúdo da tabela. Com `visao`, mostra só aquela parte (a aba Jogos tem "Grupos" e "Confrontos"
 * como abas separadas); sem ela, mantém a alternância interna.
 */
export function TabelaConteudo({ recurso: { dados, carregando, erro, recarregar }, visao }: { recurso: RecursoTabela; visao?: 'tabela' | Aba }) {
  const [escolhida, setEscolhida] = useState<Aba | null>(null);
  if (erro) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return carregando ? <Carregando linhas={6} /> : null;

  const temGrupos = dados.grupos.length > 0;
  const temConfrontos = dados.confrontos.length > 0 || dados.mataMata.length > 0;
  // Sem grupos (ex.: Copa do Brasil), abre direto nos confrontos.
  const padrao: Aba = temGrupos ? 'grupos' : 'confrontos';
  const aba: Aba = visao ? (visao === 'tabela' ? padrao : visao) : escolhida ?? padrao;

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

      {!visao && temGrupos && temConfrontos && <SeletorAba aba={aba} onMudar={setEscolhida} />}

      {aba === 'grupos' && dados.grupos.map(grupo => (
        <div key={grupo.nome} className={`${cartao} overflow-hidden`}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <h3 className="font-bold text-gray-900 dark:text-white">{grupo.nome}</h3>
            <span className="text-xs text-gray-400">{grupo.linhas.length} equipes</span>
          </div>
          {/* Rolagem lateral no celular: posição e time ficam congelados à esquerda. */}
          <div className="relative overflow-x-auto scrollbar-thin overscroll-x-contain">
            {/* table-fixed: as colunas têm a mesma largura em todos os grupos, não importa o nome dos times. */}
            <table className="w-full table-fixed text-sm min-w-[32rem] sm:min-w-0">
              <thead>
                <tr className="text-xs text-gray-400 uppercase">
                  <th className={`${COL_POS} ${FIXA} z-[2] text-left py-3 font-semibold`}>#</th>
                  <th className={`${COL_TIME} ${FIXA} ${SEPARADOR} z-[2] text-left py-3 px-2 font-semibold`}>Time</th>
                  <th className="w-12 py-3 px-2 font-semibold">P</th>
                  <th className="w-12 py-3 px-2 font-semibold">J</th>
                  <th className="w-12 py-3 px-2 font-semibold">V</th>
                  <th className="w-12 py-3 px-2 font-semibold">E</th>
                  <th className="w-12 py-3 px-2 font-semibold">D</th>
                  <th className="w-14 py-3 px-2 font-semibold hidden sm:table-cell">GP</th>
                  <th className="w-14 py-3 px-2 font-semibold hidden sm:table-cell">GC</th>
                  <th className="w-[4.5rem] py-3 pl-2 pr-5 font-semibold">SG</th>
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

      {aba === 'confrontos' && <Confrontos dados={dados} soChave={!!visao} />}

      {dados.sucesso && !temGrupos && !temConfrontos && (
        <div className={cartao}>
          <EmptyState icon={<Table2 className="w-10 h-10" />} title="Tabela indisponível" description="A API ainda não publicou a classificação desta temporada." />
        </div>
      )}

      {aba === 'grupos' && dados.legendas.length > 0 && (
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
        Fonte: {dados.fonte || 'football-data.org'}{dados.fonteCache && dados.horarioCache ? ` · dados do cache, atualizados às ${dados.horarioCache}` : ''}
      </p>
    </div>
  );
}

/** Alternância "Grupos | Confrontos", no mesmo estilo da alternância Jogos | Tabela. */
function SeletorAba({ aba, onMudar }: { aba: Aba; onMudar: (a: Aba) => void }) {
  return (
    <div role="tablist" aria-label="Tabela do campeonato" className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit max-w-full">
      {([['grupos', 'Grupos', Users], ['confrontos', 'Confrontos', CalendarDays]] as const).map(([id, label, Icon]) => (
        <button key={id} role="tab" aria-selected={aba === id} onClick={() => onMudar(id)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${aba === id ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
          <Icon className="w-4 h-4" />{label}
        </button>
      ))}
    </div>
  );
}

/** Confrontos: chave do mata-mata com linhas entre as fases e, fora da aba própria, as rodadas importadas. */
function Confrontos({ dados, soChave }: { dados: TabelaApi; soChave: boolean }) {
  const { fases: naChave, fora } = fasesDaChave(dados);
  const temChave = naChave.length > 0;
  // Rodadas de pontos corridos/fase de grupos continuam em lista; o mata-mata vai para a chave,
  // menos as fases iniciais (sem encadeamento), que ficam em lista.
  const soLista = new Set(fora.map(f => f.original));
  const fases = dados.confrontos.filter(f => !temChave || (soChave ? soLista.has(f.nome) : !ehMataMata(f.nome) || soLista.has(f.nome)));
  // Fase inicial: a primeira com jogo ainda sem resultado; se tudo terminou, a última.
  const pendente = fases.findIndex(f => f.jogos.some(j => j.status !== 'encerrado'));
  const inicial = pendente === -1 ? Math.max(0, fases.length - 1) : pendente;
  const [escolhida, setEscolhida] = useState<number | null>(null);

  const chave = temChave && (
    <div className={`${cartao} p-4 sm:p-5`}>
      <h3 className="font-bold text-gray-900 dark:text-white mb-4">Mata-mata</h3>
      <Chaveamento dados={dados} />
    </div>
  );
  if (!fases.length) return <>{chave}</>;

  const indice = Math.min(escolhida ?? inicial, fases.length - 1);
  const fase = fases[indice];
  return (
    <>
      {chave}
      <div className={`${cartao} overflow-hidden`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="min-w-0">
            {temChave && <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Fora da chave</p>}
            <h3 className="font-bold text-gray-900 dark:text-white">{fase.nome}</h3>
            {temChave && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Jogos de fases que não entram no mata-mata acima (fase de grupos, preliminares e playoffs).</p>}
          </div>
          <select value={indice} onChange={e => setEscolhida(Number(e.target.value))} aria-label="Escolher fase ou rodada"
            className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
            {fases.map((f, i) => <option key={f.nome} value={i}>{f.nome}</option>)}
          </select>
        </div>
        <div className="p-2 sm:p-3 divide-y divide-gray-50 dark:divide-gray-800/60">
          {fase.jogos.map((j, i) => <JogoLinha key={`${j.casa}-${j.fora}-${i}`} jogo={j} mostrarData />)}
        </div>
      </div>
    </>
  );
}
