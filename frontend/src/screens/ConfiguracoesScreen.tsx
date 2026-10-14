import { useState } from 'react';
import { ArrowRight, Target, UserCog } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { useApp } from '@/context/AppContext';
import { CampeonatosScreen } from '@/screens/CampeonatosScreen';

type Aba = 'campeonatos' | 'responsaveis';

const ABAS: { id: Aba; label: string; icon: typeof Target }[] = [
  { id: 'campeonatos', label: 'Campeonatos', icon: Target },
  { id: 'responsaveis', label: 'Responsáveis', icon: UserCog },
];

/** Configurações do bolão: campeonatos (rodadas e tabela) e responsáveis. */
export function ConfiguracoesScreen() {
  const { dados, bolao } = useApp();
  const [aba, setAba] = useState<Aba>('campeonatos');
  const subtitulo = bolao ? `${bolao.nome} · ${bolao.chave}` : undefined;

  const abas = (
    <div role="tablist" aria-label="Seções das configurações" className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit max-w-full overflow-x-auto scrollbar-thin">
      {ABAS.map(a => {
        const Icon = a.icon;
        const ativa = aba === a.id;
        return (
          <button key={a.id} role="tab" aria-selected={ativa} onClick={() => setAba(a.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${ativa ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            <Icon className="w-4 h-4" />{a.label}
          </button>
        );
      })}
    </div>
  );

  if (aba === 'campeonatos') return <CampeonatosScreen titulo="Configurações" subtitulo={subtitulo} topo={abas} />;

  return (
    <div>
      <Header title="Configurações" subtitle={subtitulo} />
      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        {abas}
        <section className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-6 space-y-4 animate-slide-up">
          <p className="text-sm text-gray-500 dark:text-gray-400">Responsáveis do bolão. Enquanto esta seção é migrada (etapa 7), use a tela atual.</p>
          {dados.links.configuracoes && (
            <a href={dados.links.configuracoes} className="button-primary">Abrir responsáveis <ArrowRight className="w-4 h-4" /></a>
          )}
        </section>
      </div>
    </div>
  );
}
