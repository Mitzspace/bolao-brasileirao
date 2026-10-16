import { useState } from 'react';
import { Hourglass, Trophy, Users } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { Variacao } from '@/components/ui/Variacao';
import { Podio } from '@/components/boloes/Podio';
import { useRecurso } from '@/lib/useRecurso';
import type { ItemRanking } from '@/types';
import { cartao, idDoNome, Titulo } from '../comum';
import type { ClassificacaoApi } from '../tipos';

/** Mensagem enquanto o admin não libera a classificação. */
export function TabelaEmBreve() {
  return (
    <div className={`${cartao} p-8 flex flex-col items-center text-center`}>
      <div className="w-16 h-16 rounded-2xl bg-gold-50 dark:bg-gold-900/20 flex items-center justify-center mb-4">
        <Hourglass className="w-8 h-8 text-gold-500" />
      </div>
      <h2 className="text-lg font-bold text-gray-900 dark:text-white">A classificação será divulgada em breve</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-sm">Enquanto isso, acompanhe os jogos e os palpites das partidas que já terminaram.</p>
    </div>
  );
}

/** Classificação liberada pelo admin: geral até a rodada liberada ou de uma rodada. */
export function Tabela() {
  const [rodada, setRodada] = useState('');
  const [ocultar, setOcultar] = useState(true);
  const params = new URLSearchParams();
  if (rodada) params.set('rodada', rodada);
  if (!ocultar) params.set('desistentes', 'mostrar');
  const { dados, carregando, erro, recarregar } = useRecurso<ClassificacaoApi>(`/classificacao?${params}`);

  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={4} />;
  if (!dados.liberada) return <TabelaEmBreve />;

  const geral = !dados.rodada;
  const podio = dados.itens.map(i => ({ ...i, participacaoId: idDoNome(i.nome) })) as unknown as ItemRanking[];
  return (
    <section className={`${cartao} overflow-hidden`} aria-labelledby="titulo-tabela">
      <Titulo icone={<Trophy className="w-5 h-5" />} titulo="Classificação"
        extra={<Badge color="green">Até a {dados.ate.nome}</Badge>} />
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <select value={rodada} onChange={e => setRodada(e.target.value)} aria-label="Filtrar classificação"
          className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
          <option value="">Geral (até a {dados.ate.nome})</option>
          {[...dados.rodadas].reverse().map(r => <option key={r.numero} value={r.numero}>Somente a {r.nome}</option>)}
        </select>
        <div className="sm:ml-auto"><Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" /></div>
      </div>
      <div className={`transition-opacity ${carregando ? 'opacity-60' : ''}`}>
        {dados.itens.length === 0 ? (
          <EmptyState icon={<Users className="w-10 h-10" />} title="Ninguém na classificação ainda" />
        ) : (
          <>
            <div className="p-5 bg-gradient-to-b from-brand-50 to-transparent dark:from-brand-900/20"><Podio ranking={podio} /></div>
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-800 text-xs font-semibold text-gray-400 uppercase">
                    <th className="text-center py-3 px-2">#</th>
                    <th className="text-left py-3 px-2">Participante</th>
                    <th className="text-center py-3 px-2" title="Placares exatos">Crav.</th>
                    <th className="hidden sm:table-cell text-center py-3 px-2" title="Vencedor ou empate certo, sem placar exato">Result.</th>
                    <th className="hidden sm:table-cell text-center py-3 px-2" title="Bônus">Bônus</th>
                    <th className="text-center py-3 px-2">Pts</th>
                    {geral && <th className="text-center py-3 px-2" title="Variação em relação à rodada anterior">Var.</th>}
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map(i => (
                    <tr key={`${i.posicao}-${i.nome}`} className="border-b border-gray-50 dark:border-gray-800/60 last:border-0">
                      <td className="text-center py-3 px-2 text-sm font-bold text-gray-500">{i.posicao}º</td>
                      <td className="py-3 px-2">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Avatar nome={i.nome} id={idDoNome(i.nome)} />
                          <span className="font-medium text-sm text-gray-900 dark:text-white truncate">{i.nome}</span>
                          {i.status === 'desistente' && <Badge color="yellow" size="sm">Desistente</Badge>}
                        </div>
                      </td>
                      <td className="text-center py-3 px-2 text-sm text-gray-600 dark:text-gray-300">{i.cravadas}</td>
                      <td className="hidden sm:table-cell text-center py-3 px-2 text-sm text-gray-600 dark:text-gray-300">{i.acertos}</td>
                      <td className="hidden sm:table-cell text-center py-3 px-2 text-sm text-gray-600 dark:text-gray-300">{i.bonus}</td>
                      <td className="text-center py-3 px-2 text-sm font-bold text-brand-600 dark:text-brand-400">{i.pontos}</td>
                      {geral && <td className="text-center py-3 px-2"><Variacao valor={i.variacao} /></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
