import { ArrowRight, Calendar, Target, Trophy, Users, Settings } from 'lucide-react';
import { AppProvider, useApp } from '@/context/AppContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { BottomNav } from '@/components/layout/BottomNav';
import { Header } from '@/components/layout/Header';
import { BolaoSelector } from '@/components/layout/BolaoSelector';
import { LoginScreen } from '@/screens/LoginScreen';
import { BoloesScreen } from '@/screens/BoloesScreen';
import type { View } from '@/types';

const labels: Record<View, string> = {
  dashboard: 'Dashboard', campeonatos: 'Campeonatos', rodadas: 'Rodadas',
  participantes: 'Participantes', boloes: 'Bolões', configuracoes: 'Configurações',
};
function CurrentScreen() {
  const { dados, bolao, view, setView } = useApp();
  if (view === 'boloes' || !bolao) return <BoloesScreen />;
  if (view === 'dashboard') return <div className="space-y-6">
    <section className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
      <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4" />
      <div className="relative"><p className="text-white/80 text-sm">Bem-vindo de volta!</p><h2 className="text-2xl font-bold mt-1 break-words">{bolao.nome}</h2><p className="text-white/80 text-sm mt-2">{bolao.campeonato} {bolao.ano ?? ''}</p>
        <a href={dados.links.palpites} className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white text-brand-700 rounded-xl font-semibold text-sm hover:bg-brand-50"><Target className="w-4 h-4" /> Lançar palpites <ArrowRight className="w-4 h-4" /></a>
      </div>
    </section>
    <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {([
        ['campeonatos', Target, 'Campeonatos'], ['rodadas', Calendar, 'Jogos e rodadas'],
        ['participantes', Users, 'Participantes'], ['configuracoes', Settings, 'Responsáveis'],
      ] as const).map(([key, Icon, label]) => <button key={key} onClick={() => setView(key)} className="panel p-5 text-left hover:border-brand-300 dark:hover:border-brand-700">
        <div className="w-11 h-11 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-600 flex items-center justify-center mb-3"><Icon className="w-5 h-5" /></div><span className="font-semibold">{label}</span><p className="text-xs text-gray-400 mt-1">Acessar gestão</p>
      </button>)}
    </div>
    <section className="panel p-5"><h2 className="font-bold flex items-center gap-2"><Trophy className="w-5 h-5 text-brand-600" /> Classificação do bolão</h2><p className="text-sm text-gray-500 mt-2">Consulte os pontos e a classificação atual.</p><a href={dados.links.ranking} className="button-primary mt-4">Ver classificação <ArrowRight className="w-4 h-4" /></a></section>
  </div>;
  return <section className="panel p-6 space-y-4">
    <h2 className="text-lg font-bold">{labels[view]}</h2>
    <p className="text-sm text-gray-500 dark:text-gray-400">Acesse a tela atual para gerenciar {view === 'configuracoes' ? 'os responsáveis deste bolão' : labels[view].toLocaleLowerCase('pt-BR')}. O novo visual desta seção será integrado nas próximas etapas.</p>
    <div className="flex flex-wrap gap-3">
      <a href={dados.links[view]} className="button-primary">Abrir {labels[view]} <ArrowRight className="w-4 h-4" /></a>
      {view === 'rodadas' && <a href={dados.links.palpites} className="button-primary">Lançar palpites</a>}
      {view === 'campeonatos' && <a href={dados.links.tabela} className="button-primary">Tabela oficial</a>}
    </div>
    {view === 'configuracoes' && <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
      <p className="text-sm font-medium">{dados.usuario?.nome}</p>
      <p className="text-xs text-gray-500 break-all mt-1">{dados.usuario?.email}</p>
      <a href={dados.links.logout} className="inline-block mt-4 rounded-xl bg-red-50 dark:bg-red-900/20 px-4 py-2.5 text-sm font-semibold text-red-600">Sair da conta</a>
    </div>}
  </section>;
}
function AppContent() {
  const { usuario, dados, bolao, view } = useApp();
  if (!usuario) return <LoginScreen />;
  return <div className="flex h-screen h-dvh overflow-hidden">
    <Sidebar />
    <main id="conteudo" className="flex-1 min-w-0 overflow-y-auto scrollbar-thin">
      <Header title={labels[view]} subtitle={bolao ? `${bolao.nome} · ${bolao.chave}` : 'Selecione seu bolão'} />
      <div className="p-4 md:p-8 space-y-6 pb-28 md:pb-8">
        {dados.mensagens.map((message, index) => <p key={index} role="status" className="rounded-xl bg-gold-50 text-gold-800 border border-gold-200 p-3 text-sm">{message}</p>)}
        <section className="panel p-4"><BolaoSelector /><a href={dados.links.boloes} className="inline-block text-xs text-brand-600 dark:text-brand-400 mt-3 hover:underline">Abrir sistema atual</a></section>
        <CurrentScreen />
      </div>
    </main>
    <BottomNav />
  </div>;
}
export default function App() {
  return <AppProvider><AppContent /></AppProvider>;
}
