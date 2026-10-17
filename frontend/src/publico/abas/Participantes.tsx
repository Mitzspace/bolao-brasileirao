import { useState } from 'react';
import { ChevronRight, Search, Users } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { useRecurso } from '@/lib/useRecurso';
import { cartao, idDoNome, Titulo } from '../comum';
import type { AbrirParticipante, ParticipantesApi } from '../tipos';

/** Lista de participantes; posição e pontos só com a classificação liberada. Tocar abre o desempenho. */
export function Participantes({ onAbrirParticipante }: { onAbrirParticipante: AbrirParticipante }) {
  const { dados, erro, recarregar } = useRecurso<ParticipantesApi>('/participantes');
  const [busca, setBusca] = useState('');
  const [ocultar, setOcultar] = useState(true);
  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={6} />;
  const termo = busca.trim().toLocaleLowerCase('pt-BR');
  const lista = dados.participantes.filter(p =>
    (!ocultar || p.status !== 'desistente') && (!termo || p.nome.toLocaleLowerCase('pt-BR').includes(termo)));
  return (
    <section className={`${cartao} overflow-hidden`}>
      <Titulo icone={<Users className="w-5 h-5" />} titulo={`Participantes (${lista.length})`}
        extra={dados.tabela ? <Badge color="green">Pontos até a {dados.tabela.nome}</Badge> : undefined} />
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar participante" aria-label="Buscar participante"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
        </div>
        <Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" />
      </div>
      <ul className="divide-y divide-gray-50 dark:divide-gray-800/60">
        {lista.map((p, i) => (
          <li key={p.ref ?? i}>
            <button onClick={() => onAbrirParticipante(p)} className="w-full flex items-center gap-3 px-5 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
            <Avatar nome={p.nome} id={idDoNome(p.nome)} size="md" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 dark:text-white truncate">{p.nome}</p>
              {p.status === 'desistente' && <Badge color="yellow" size="sm">Desistente</Badge>}
            </div>
            {p.pontos !== undefined && (
              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-brand-600 dark:text-brand-400">{p.pontos} pts</p>
                <p className="text-xs text-gray-400">{p.posicao ? `${p.posicao}º lugar` : '—'}</p>
              </div>
            )}
            <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 shrink-0" aria-hidden="true" />
            </button>
          </li>
        ))}
        {lista.length === 0 && <li className="px-5 py-8 text-sm text-gray-400 text-center">Ninguém encontrado.</li>}
      </ul>
    </section>
  );
}
