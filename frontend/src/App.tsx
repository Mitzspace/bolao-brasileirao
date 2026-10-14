import { useEffect } from 'react';
import { AppProvider, useApp } from '@/context/AppContext';
import { ToastProvider, useToast } from '@/components/ui/Toast';
import { Sidebar } from '@/components/layout/Sidebar';
import { BottomNav } from '@/components/layout/BottomNav';
import { LoginScreen } from '@/screens/LoginScreen';
import { BoloesScreen } from '@/screens/BoloesScreen';
import { TelaEmMigracao } from '@/screens/TelaEmMigracao';
import { Dashboard } from '@/screens/Dashboard';
import { JogosScreen } from '@/screens/JogosScreen';
import { CampeonatosScreen } from '@/screens/CampeonatosScreen';
import { RodadasScreen } from '@/screens/RodadasScreen';

function CurrentScreen() {
  const { dados, bolao, view } = useApp();
  const l = dados.links;
  // Sem bolão selecionado, todas as abas levam à escolha do bolão.
  if (view === 'boloes' || !bolao) return <BoloesScreen />;
  switch (view) {
    case 'dashboard':
      return <Dashboard />;
    case 'jogos':
      return <JogosScreen />;
    case 'campeonatos':
      return <CampeonatosScreen />;
    case 'rodadas':
      return <RodadasScreen />;
    case 'participantes':
      return <TelaEmMigracao titulo="Participantes" descricao="Cadastro, entrada, desistência e pontos dos participantes. Enquanto esta aba é migrada, use a tela atual."
        atalhos={[{ label: 'Abrir participantes', href: l.participantes, destaque: true }]} />;
    case 'configuracoes':
      return <TelaEmMigracao titulo="Configurações" descricao="Responsáveis do bolão. Enquanto esta aba é migrada, use a tela atual."
        atalhos={[{ label: 'Abrir responsáveis', href: l.configuracoes, destaque: true }]} />;
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
        <CurrentScreen />
      </main>
      <BottomNav />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppProvider>
        <AppContent />
      </AppProvider>
    </ToastProvider>
  );
}
