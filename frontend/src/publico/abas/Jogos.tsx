import { useState } from 'react';
import { CalendarClock } from 'lucide-react';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import { cartao, LinhaJogo, Rodadas } from '../comum';
import type { JogosApi } from '../tipos';

/** Jogos por rodada: resultados e próximos jogos. */
export function Jogos() {
  const [numero, setNumero] = useState<number | null>(null);
  const { dados, carregando, erro, recarregar } = useRecurso<JogosApi>(numero ? `/jogos?rodada=${numero}` : '/jogos');
  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={5} />;
  const r = dados.rodada;
  return (
    <div className="space-y-4">
      <Rodadas rodadas={dados.rodadas} selecionada={numero ?? r?.numero ?? null} atual={dados.atual} onSelecionar={setNumero} />
      {r && (
        <div className="flex items-center gap-2 px-1">
          <CalendarClock className="w-4 h-4 text-brand-600" />
          <h2 className="font-bold text-gray-900 dark:text-white">{r.nome}</h2>
          <span className="text-xs text-gray-400">{r.comResultado} de {r.jogos} com resultado</span>
        </div>
      )}
      <div className={`space-y-3 transition-opacity ${carregando ? 'opacity-60' : ''}`}>
        {dados.jogos.map((j, i) => <div key={i} className={cartao}><LinhaJogo jogo={j} /></div>)}
        {dados.jogos.length === 0 && <p className="text-sm text-gray-400 text-center py-10">Nenhum jogo cadastrado nesta rodada.</p>}
      </div>
    </div>
  );
}
