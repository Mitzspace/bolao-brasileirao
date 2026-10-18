import { useState } from 'react';
import { Palette, Shield, Target, User, UserCog } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { SecaoAparencia, SecaoPerfil, SecaoResponsaveis, SecaoSeguranca } from '@/components/configuracoes/Secoes';
import { useApp } from '@/context/AppContext';
import { CampeonatosScreen } from '@/screens/CampeonatosScreen';
import { EliminacaoPainel } from '@/components/EliminacaoPainel';

type Aba = 'campeonatos' | 'eliminacao' | 'perfil' | 'seguranca' | 'responsaveis' | 'aparencia';

const ABAS: { id: Aba; label: string; icon: typeof Target }[] = [
  { id: 'campeonatos', label: 'Campeonatos', icon: Target },
  { id: 'eliminacao', label: 'Eliminação', icon: Target },
  { id: 'perfil', label: 'Perfil', icon: User },
  { id: 'seguranca', label: 'Segurança', icon: Shield },
  { id: 'responsaveis', label: 'Responsáveis', icon: UserCog },
  { id: 'aparencia', label: 'Aparência', icon: Palette },
];
const CHAVE = 'bolao-interface-config-aba';

function abaSalva(): Aba {
  try {
    const valor = localStorage.getItem(CHAVE);
    return ABAS.some(a => a.id === valor) ? valor as Aba : 'campeonatos';
  } catch { return 'campeonatos'; }
}

/** Configurações: campeonatos do bolão, conta do responsável, responsáveis e tema. */
export function ConfiguracoesScreen() {
  const { bolao } = useApp();
  const [aba, setAbaEstado] = useState<Aba>(abaSalva);
  const setAba = (nova: Aba) => {
    setAbaEstado(nova);
    try { localStorage.setItem(CHAVE, nova); } catch { /* a aba só não fica lembrada */ }
  };
  const subtitulo = bolao ? `${bolao.nome} · ${bolao.campeonato} ${bolao.ano ?? ''}` : undefined;

  const abas = (
    <div role="tablist" aria-label="Seções das configurações" className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit max-w-full overflow-x-auto no-scrollbar">
      {ABAS.map(a => {
        const Icon = a.icon;
        const ativa = aba === a.id;
        return (
          <button key={a.id} role="tab" aria-selected={ativa} onClick={() => setAba(a.id)}
            className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${ativa ? 'bg-white dark:bg-gray-900 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
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
        <div className="max-w-3xl">
          {aba === 'eliminacao' && (bolao ? <EliminacaoPainel key={bolao.id} /> : <p className="text-sm text-gray-500">Selecione um bolão para configurar a eliminação.</p>)}
          {aba === 'perfil' && <SecaoPerfil />}
          {aba === 'seguranca' && <SecaoSeguranca />}
          {aba === 'responsaveis' && <SecaoResponsaveis />}
          {aba === 'aparencia' && <SecaoAparencia />}
        </div>
      </div>
    </div>
  );
}
