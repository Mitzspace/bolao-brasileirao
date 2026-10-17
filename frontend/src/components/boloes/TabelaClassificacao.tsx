import { Fragment, useState, type ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Variacao } from '@/components/ui/Variacao';
import { CORES_MEDALHA } from './Podio';

export interface LinhaClassificacao {
  chave: string | number;
  avatarId: number;
  nome: string;
  status: string;
  posicao: number | null;
  pontos: number;
  pontosPalpites: number;
  bonus: number;
  bonusPrimeiroGol: number;
  cravadas: number;
  acertos: number;
  variacao: number | null;
}

/** Colunas de números da tabela (posição e participante aparecem sempre). */
export type ColunaClassificacao = 'pontos' | 'bonus' | 'cravadas' | 'resultados' | 'total' | 'variacao';

/** Padrão da gestão: todas as colunas, nesta ordem. */
export const COLUNAS_COMPLETAS: readonly ColunaClassificacao[] = ['pontos', 'bonus', 'cravadas', 'resultados', 'total', 'variacao'];

interface Props {
  itens: LinhaClassificacao[];
  /** Classificação geral (mostra a variação de posição); false = somente uma rodada. */
  geral: boolean;
  /** Colunas exibidas, na ordem dada (padrão: todas, como na gestão). */
  colunas?: readonly ColunaClassificacao[];
  /** Dica da coluna Var. (ex.: "Variação após a 12ª Rodada"). */
  dicaVariacao?: string;
  /**
   * Celular: 'expandir' esconde Pontos/Bônus/Resultados e mostra ao tocar na linha (gestão);
   * 'colunas' mostra as colunas escolhidas, com rolagem lateral e nome fixo se não couberem (página pública).
   */
  celular?: 'expandir' | 'colunas';
  /** Abre o desempenho do participante (nome clicável; no modo 'colunas', a linha inteira). */
  onAbrir?: (item: LinhaClassificacao) => void;
}

const th = 'py-3 px-1.5 sm:px-3 text-xs font-semibold text-gray-400 uppercase';
const td = 'py-3 px-1.5 sm:px-3';
/** No modo 'expandir', estas colunas só aparecem do tablet para cima (no celular, ao tocar na linha). */
const SO_NA_TELA: ReadonlySet<ColunaClassificacao> = new Set(['pontos', 'bonus', 'resultados']);

const CABECALHO: Record<ColunaClassificacao, { rotulo: string; dica?: string }> = {
  pontos: { rotulo: 'Pontos', dica: 'Pontos dos placares, sem o bônus' },
  bonus: { rotulo: 'Bônus', dica: 'Bônus de primeiro gol e créditos do histórico' },
  cravadas: { rotulo: 'Cravadas', dica: 'Placares exatos' },
  resultados: { rotulo: 'Resultados', dica: 'Vencedor ou empate correto, sem placar exato' },
  total: { rotulo: 'Total' },
  variacao: { rotulo: 'Var.' },
};

function valores(p: LinhaClassificacao) {
  // Bônus = primeiro gol (lançado no sistema + créditos importados); Pontos + Bônus = Total.
  const bonus = p.bonus + p.bonusPrimeiroGol;
  return { bonus, pontosPlacar: p.pontosPalpites - p.bonusPrimeiroGol };
}

function celula(coluna: ColunaClassificacao, p: LinhaClassificacao): ReactNode {
  const { bonus, pontosPlacar } = valores(p);
  switch (coluna) {
    case 'pontos': return <span className="text-sm text-gray-600 dark:text-gray-400">{pontosPlacar}</span>;
    case 'bonus': return bonus > 0 ? <span className="text-sm font-bold text-gold-600">+{bonus}</span> : <span className="text-sm text-gray-400">0</span>;
    case 'cravadas': return <span className="text-sm text-gray-600 dark:text-gray-400">{p.cravadas}</span>;
    case 'resultados': return <span className="text-sm text-gray-600 dark:text-gray-400">{p.acertos}</span>;
    case 'total': return <span className="text-sm font-bold text-brand-600 dark:text-brand-400">{p.pontos}</span>;
    case 'variacao': return <Variacao valor={p.variacao} />;
  }
}

/**
 * Tabela de classificação do Bolt (mesmas colunas da gestão):
 * Pontos (placares) + Bônus (primeiro gol e créditos) = Total; Cravadas; Resultados; Variação.
 */
export function TabelaClassificacao({ itens, geral, colunas: escolhidas = COLUNAS_COMPLETAS, dicaVariacao, celular = 'expandir', onAbrir }: Props) {
  const [aberta, setAberta] = useState<string | number | null>(null);
  const modoColunas = celular === 'colunas';
  // A variação só existe na classificação geral.
  const colunas = escolhidas.filter(c => c !== 'variacao' || geral);
  // Com poucas colunas tudo cabe no celular; com muitas, a tabela rola para o lado com nome fixo.
  const rola = modoColunas && colunas.length > 3;
  const classeColuna = (c: ColunaClassificacao) => (!modoColunas && SO_NA_TELA.has(c) ? 'hidden sm:table-cell' : '');
  // Colunas fixas na rolagem lateral (fundo opaco para o texto não passar por baixo).
  const fixa = rola ? 'sticky z-[1] bg-white dark:bg-gray-900' : '';
  const sombra = rola ? 'shadow-[6px_0_6px_-6px_rgba(0,0,0,0.15)] sm:shadow-none' : '';
  const hoverFixa = rola ? 'group-hover:bg-gray-50 dark:group-hover:bg-gray-800' : '';
  const totalColunas = 2 + colunas.length + 1;

  return (
    <>
      <div className="relative overflow-x-auto scrollbar-thin overscroll-x-contain">
        <table className={`w-full ${rola ? 'min-w-[34rem] sm:min-w-0' : ''}`}>
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-800">
              <th className={`${th} text-center ${fixa} left-0 w-11`}>#</th>
              <th className={`${th} text-left ${fixa} left-11 ${sombra}`}>Participante</th>
              {colunas.map(c => (
                <th key={c} className={`${classeColuna(c)} ${th} text-center`} title={c === 'variacao' ? dicaVariacao : CABECALHO[c].dica}>{CABECALHO[c].rotulo}</th>
              ))}
              {!modoColunas && <th className="sm:hidden w-8"><span className="sr-only">Detalhes</span></th>}
              {modoColunas && onAbrir && <th className="w-6"><span className="sr-only">Abrir</span></th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
            {itens.map((p, i) => {
              const expandida = !modoColunas && aberta === p.chave;
              const { bonus, pontosPlacar } = valores(p);
              const clicar = modoColunas
                ? (onAbrir ? () => onAbrir(p) : undefined)
                : () => setAberta(expandida ? null : p.chave);
              return (
                <Fragment key={p.chave}>
                  <tr onClick={clicar} aria-expanded={modoColunas ? undefined : expandida}
                    className={`group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${modoColunas ? (onAbrir ? 'cursor-pointer' : '') : 'cursor-pointer sm:cursor-default'} ${p.status !== 'ativo' ? 'opacity-70' : ''}`}>
                    <td className={`${td} text-center ${fixa} left-0 ${hoverFixa}`}>
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mx-auto ${i < 3 ? 'text-white' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'}`}
                        style={i < 3 ? { backgroundColor: CORES_MEDALHA[i] } : {}}>{p.posicao ?? i + 1}</div>
                    </td>
                    <td className={`${td} ${fixa} left-11 ${rola ? 'max-w-[9.5rem] sm:max-w-none' : ''} ${sombra} ${hoverFixa}`}>
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="hidden min-[400px]:block"><Avatar nome={p.nome} id={p.avatarId} /></span>
                        {onAbrir ? (
                          <button type="button" onClick={e => { e.stopPropagation(); onAbrir(p); }} title="Ver desempenho"
                            className={`text-left text-sm font-medium text-gray-900 dark:text-white truncate hover:underline hover:text-brand-700 dark:hover:text-brand-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 rounded ${modoColunas ? '' : 'max-w-[7.5rem] sm:max-w-none'}`}>
                            {p.nome}
                          </button>
                        ) : (
                          <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[7.5rem] sm:max-w-none">{p.nome}</span>
                        )}
                        {p.status === 'desistente' && <Badge color="yellow" size="sm">Desistente</Badge>}
                      </div>
                    </td>
                    {colunas.map(c => <td key={c} className={`${classeColuna(c)} ${td} text-center`}>{celula(c, p)}</td>)}
                    {!modoColunas && (
                      <td className="sm:hidden pr-2 text-gray-400">
                        <ChevronDown className={`w-4 h-4 transition-transform ${expandida ? 'rotate-180' : ''}`} aria-label={expandida ? 'Recolher detalhes' : 'Ver detalhes'} />
                      </td>
                    )}
                    {modoColunas && onAbrir && <td className="pr-2 text-gray-300 dark:text-gray-600"><ChevronRight className="w-4 h-4" aria-hidden="true" /></td>}
                  </tr>
                  {expandida && (
                    <tr className="sm:hidden bg-gray-50/70 dark:bg-gray-800/40">
                      <td colSpan={totalColunas} className="px-3 py-3 max-w-0">
                        <dl className="grid grid-cols-2 gap-2 text-xs animate-fade-in">
                          {[
                            ['Pontos', pontosPlacar, 'dos placares'],
                            ['Bônus', bonus > 0 ? `+${bonus}` : '0', 'primeiro gol'],
                            ['Cravadas', p.cravadas, 'placar exato'],
                            ['Resultados', p.acertos, 'vencedor ou empate'],
                          ].map(([rotulo, valor, dica]) => (
                            <div key={rotulo} className="min-w-0 rounded-lg bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 px-3 py-2">
                              <dt className="text-gray-400">{rotulo}</dt>
                              <dd className="text-sm font-bold text-gray-900 dark:text-white">{valor}<span className="block text-[10px] font-normal text-gray-400 truncate">{dica}</span></dd>
                            </div>
                          ))}
                        </dl>
                        {onAbrir && (
                          <button type="button" onClick={() => onAbrir(p)}
                            className="mt-2 w-full text-center text-xs font-semibold text-brand-700 dark:text-brand-300 py-2 rounded-lg hover:bg-white dark:hover:bg-gray-900">
                            Ver desempenho por rodada
                          </button>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-3 text-xs text-gray-400 border-t border-gray-100 dark:border-gray-800">
        {!modoColunas && <span className="sm:hidden">Toque em um participante para ver pontos e bônus. </span>}
        {rola && <span className="sm:hidden">Deslize a tabela para o lado para ver todas as colunas. </span>}
        {onAbrir && <span>Toque no nome para ver o desempenho. </span>}
        Total = pontos + bônus. Desempate: total, cravadas, resultados e nome.
      </p>
    </>
  );
}
