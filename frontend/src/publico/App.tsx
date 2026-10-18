import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, HelpCircle, LayoutDashboard, Moon, PencilLine, Sun, Trophy, Users } from 'lucide-react';
import { Drawer } from '@/components/ui/Drawer';
import { ComoFuncionaPontuacao } from '@/components/regras/ComoFuncionaPontuacao';
import { useRecurso } from '@/lib/useRecurso';
import { useTema } from '@/lib/tema';
import { useTemaCampeonato } from '@/lib/temaCampeonato';
import { FaixaTema } from '@/components/ui/FaixaTema';
import { Inicio } from './abas/Inicio';
import { Jogos } from './abas/Jogos';
import { Palpites } from './abas/Palpites';
import { Participantes } from './abas/Participantes';
import { Tabela } from './abas/Tabela';
import { DetalhePublico } from './DetalhePublico';
import type { AbrirParticipante, DadosPagina, InicioApi } from './tipos';
import { LogoApp } from '@/components/ui/LogoApp';

const ABAS = [
  { id: 'inicio', label: 'Início', longo: 'Dashboard', icon: LayoutDashboard },
  { id: 'classificacao', label: 'Classificação', longo: 'Classificação', icon: Trophy },
  { id: 'jogos', label: 'Jogos', longo: 'Jogos e tabela', icon: CalendarClock },
  { id: 'palpites', label: 'Palpites', longo: 'Palpites', icon: PencilLine },
  { id: 'participantes', label: 'Participantes', longo: 'Participantes', icon: Users },
] as const;
type Aba = typeof ABAS[number]['id'];

function abaDoEndereco(): Aba {
  const valor = window.location.hash.slice(1);
  return (ABAS.find(a => a.id === valor)?.id) ?? 'inicio';
}

/** Página pública do bolão: somente leitura, pensada para o celular, com tema claro/escuro. */
export function AppPublico({ dados }: { dados: DadosPagina }) {
  const [aba, setAba] = useState<Aba>(abaDoEndereco);
  const { escuro, alternar } = useTema('bolao-publico-tema', 'sistema');
  const [participante, setParticipante] = useState<{ ref: string; nome: string } | null>(null);
  const [regrasAbertas, setRegrasAbertas] = useState(false);
  // As regras vêm junto com o Início (mesma resposta em cache); só busca quando o modal abre.
  const { dados: inicio } = useRecurso<InicioApi>(regrasAbertas ? '/inicio' : null);

  useEffect(() => {
    const mudar = () => setAba(abaDoEndereco());
    window.addEventListener('hashchange', mudar);
    return () => window.removeEventListener('hashchange', mudar);
  }, []);
  const ir = (nova: Aba) => {
    window.location.hash = nova;
    setAba(nova);
    window.scrollTo({ top: 0 });
  };
  const abrir: AbrirParticipante = useCallback(p => setParticipante({ ref: p.ref, nome: p.nome }), []);
  const fecharParticipante = useCallback(() => setParticipante(null), []);
  const fecharRegras = useCallback(() => setRegrasAbertas(false), []);
  const b = dados.bolao;
  useTemaCampeonato(b.tema);
  const botaoTopo = 'shrink-0 h-10 min-w-10 px-2.5 rounded-xl flex items-center justify-center gap-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors';

  return (
    <div className="min-h-screen min-h-dvh pb-24 md:pb-10">
      <FaixaTema />
      <header className="sticky top-0 z-30 bg-white/85 dark:bg-gray-900/85 backdrop-blur-md border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
          <LogoApp />
          <div className="min-w-0 flex-1">
            <h1 className="font-bold text-gray-900 dark:text-white leading-tight truncate">{b.nome}</h1>
            <p className="text-xs text-gray-400 truncate">{b.campeonato} {b.ano ?? ''} · consulta</p>
          </div>
          <button onClick={() => setRegrasAbertas(true)} className={botaoTopo} aria-label="Como funciona a pontuação" title="Como funciona a pontuação">
            <HelpCircle className="w-5 h-5" /><span className="hidden sm:inline text-sm font-medium">Como funciona</span>
          </button>
          <button onClick={alternar} className={botaoTopo} aria-label={escuro ? 'Usar tema claro' : 'Usar tema escuro'} title={escuro ? 'Tema claro' : 'Tema escuro'}>
            {escuro ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
        <nav aria-label="Seções" className="hidden md:block max-w-5xl mx-auto px-6">
          <div className="flex gap-1 -mb-px">
            {ABAS.map(a => {
              const Icon = a.icon;
              const ativa = aba === a.id;
              return (
                <button key={a.id} onClick={() => ir(a.id)} aria-current={ativa ? 'page' : undefined}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${ativa ? 'border-brand-600 text-brand-700 dark:text-brand-300' : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}`}>
                  <Icon className="w-4 h-4" />{a.longo}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-6 py-5 animate-fade-in" key={aba}>
        {aba === 'inicio' && <Inicio onVerClassificacao={() => ir('classificacao')} onAbrirParticipante={abrir} />}
        {aba === 'classificacao' && <Tabela onAbrirParticipante={abrir} onRegras={() => setRegrasAbertas(true)} />}
        {aba === 'jogos' && <Jogos rotuloTabela="Tabela do campeonato" />}
        {aba === 'palpites' && <Palpites onAbrirParticipante={abrir} />}
        {aba === 'participantes' && <Participantes onAbrirParticipante={abrir} />}
      </main>

      <nav aria-label="Seções" className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-1 py-1.5 flex items-center justify-around safe-area-bottom">
        {ABAS.map(a => {
          const Icon = a.icon;
          const ativa = aba === a.id;
          return (
            <button key={a.id} onClick={() => ir(a.id)} aria-current={ativa ? 'page' : undefined}
              className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-1.5 rounded-lg transition-colors ${ativa ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'}`}>
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium truncate max-w-full">{a.label}</span>
            </button>
          );
        })}
      </nav>

      <Drawer open={!!participante} onClose={fecharParticipante} title="Desempenho do participante" width="max-w-xl">
        {participante && <DetalhePublico key={participante.ref} refPublica={participante.ref} nome={participante.nome} />}
      </Drawer>

      <ComoFuncionaPontuacao aberto={regrasAbertas} onClose={fecharRegras}
        regras={inicio?.regras ?? null} politicaEntrada={inicio?.regras.politicaEntrada}
        rodape={inicio ? (inicio.tabela
          ? `A classificação e os palpites estão divulgados até a ${inicio.tabela.nome}. As rodadas seguintes aparecem quando os organizadores liberarem.`
          : 'A classificação e os palpites aparecem quando os organizadores liberarem a primeira rodada.') : undefined} />
    </div>
  );
}
