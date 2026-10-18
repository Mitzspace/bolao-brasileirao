import { useEffect } from 'react';
import { AppProvider, useApp } from '@/context/AppContext';
import { ToastProvider, useToast } from '@/components/ui/Toast';
import { Sidebar } from '@/components/layout/Sidebar';
import { BottomNav } from '@/components/layout/BottomNav';
import { FaixaTema } from '@/components/ui/FaixaTema';
import { BarraProgresso } from '@/components/layout/BarraProgresso';
import { LoginScreen } from '@/screens/LoginScreen';
import { BoloesScreen } from '@/screens/BoloesScreen';
import { Dashboard } from '@/screens/Dashboard';
import { JogosScreen } from '@/screens/JogosScreen';
import { ConfiguracoesScreen } from '@/screens/ConfiguracoesScreen';
import { RodadasScreen } from '@/screens/RodadasScreen';
import { PalpitesScreen } from '@/screens/PalpitesScreen';
import { ParticipantesScreen } from '@/screens/ParticipantesScreen';

function CurrentScreen() {
  const { bolao, view } = useApp();
  // Sem bolão selecionado, todas as abas mostram a escolha do bolão, com aviso da aba pedida;
  // ao escolher, a pessoa vai direto para essa aba.
  if (view === 'boloes' || !bolao) return <BoloesScreen destino={view === 'boloes' ? undefined : view} />;
  switch (view) {
    case 'dashboard':
      return <Dashboard />;
    case 'jogos':
      return <JogosScreen />;
    case 'palpites':
      return <PalpitesScreen />;
    case 'rodadas':
      return <RodadasScreen />;
    case 'participantes':
      return <ParticipantesScreen />;
    case 'campeonatos': // endereço antigo: os campeonatos agora ficam em Configurações
    case 'configuracoes':
      return <ConfiguracoesScreen />;
  }
}

function AppContent() {
  const { usuario, dados } = useApp();
  const showToast = useToast();
  useEffect(() => {
    // Mensagens do servidor (ex.: após trocar de bolão) aparecem como avisos do Bolt.
    if (usuario) dados.mensagens.forEach(m => showToast(m.texto, m.tipo));
  }, [usuario, dados, showToast]);

  if (!usuario) return <LoginScreen />;
  return (
    <div className="flex h-screen h-dvh overflow-hidden">
      <Sidebar />
      <main id="conteudo" className="flex-1 min-w-0 overflow-y-auto scrollbar-thin">
        <FaixaTema />
        <CurrentScreen />
      </main>
      <BottomNav />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <BarraProgresso />
      <AppProvider>
        <AppContent />
      </AppProvider>
    </ToastProvider>
  );
}
