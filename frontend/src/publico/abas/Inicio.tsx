import { CalendarClock, Trophy, Users, CheckCircle2 } from 'lucide-react';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import { cartao, LinhaJogo, Titulo } from '../comum';
import type { InicioApi } from '../tipos';
import { Tabela, TabelaEmBreve } from './Tabela';

function Indicador({ icone, rotulo, valor }: { icone: React.ReactNode; rotulo: string; valor: React.ReactNode }) {
  return (
    <div className={`${cartao} p-4 flex items-center gap-3 min-w-0`}>
      <div className="w-10 h-10 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-600 flex items-center justify-center shrink-0">{icone}</div>
      <div className="min-w-0">
        <p className="text-xs text-gray-400">{rotulo}</p>
        <p className="text-lg font-bold text-gray-900 dark:text-white truncate">{valor}</p>
      </div>
    </div>
  );
}

/** Dashboard público: indicadores, jogos da rodada atual e classificação (se liberada). */
export function Inicio() {
  const { dados, erro, recarregar } = useRecurso<InicioApi>('/inicio');
  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={4} />;
  const r = dados.rodada;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Indicador icone={<Users className="w-5 h-5" />} rotulo="Participantes" valor={dados.participantesAtivos} />
        <Indicador icone={<CalendarClock className="w-5 h-5" />} rotulo="Rodada atual" valor={r ? `${r.numero}ª de ${r.total}` : '—'} />
        <Indicador icone={<CheckCircle2 className="w-5 h-5" />} rotulo="Jogos encerrados" valor={r ? `${r.comResultado} de ${r.jogos}` : '—'} />
        <Indicador icone={<Trophy className="w-5 h-5" />} rotulo="Líder"
          valor={dados.lideres?.[0] ? <span className="text-gold-600 dark:text-gold-400">{dados.lideres[0].nome}</span> : 'Em breve'} />
      </div>

      {r && (
        <section className={`${cartao} overflow-hidden`}>
          <Titulo icone={<CalendarClock className="w-5 h-5" />} titulo={r.nome} />
          <div className="divide-y divide-gray-100 dark:divide-gray-800 px-4">
            {dados.jogos.map((j, i) => <LinhaJogo key={i} jogo={j} compacto />)}
            {dados.jogos.length === 0 && <p className="py-6 text-sm text-gray-400 text-center">Nenhum jogo cadastrado nesta rodada.</p>}
          </div>
        </section>
      )}

      {dados.tabela ? <Tabela /> : <TabelaEmBreve />}
    </div>
  );
}
