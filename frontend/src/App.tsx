import { useEffect } from 'react';
import { AppProvider, useApp } from '@/context/AppContext';
import { ToastProvider, useToast } from '@/components/ui/Toast';
import { Sidebar } from '@/components/layout/Sidebar';
import { BottomNav } from '@/components/layout/BottomNav';
import { LoginScreen } from '@/screens/LoginScreen';
import { BoloesScreen } from '@/screens/BoloesScreen';
import { TelaEmMigracao } from '@/screens/TelaEmMigracao';

function CurrentScreen() {
  const { dados, bolao, view } = useApp();
  const l = dados.links;
  // Sem bolão selecionado, todas as abas levam à escolha do bolão.
  if (view === 'boloes' || !bolao) return <BoloesScreen />;
  switch (view) {
    case 'dashboard':
      return <TelaEmMigracao titulo="Dashboard" descricao="Visão geral do bolão. Enquanto esta aba é migrada, use as telas atuais."
        atalhos={[{ label: 'Lançar palpites', href: l.palpites, destaque: true }, { label: 'Classificação', href: l.ranking }, { label: 'Visão geral atual', href: l.dashboard }]} />;
    case 'campeonatos':
      return <TelaEmMigracao titulo="Campeonatos" descricao="Campeonato, rodadas e tabela oficial. Enquanto esta aba é migrada, use as telas atuais."
        atalhos={[{ label: 'Abrir campeonatos', href: l.campeonatos, destaque: true }, { label: 'Tabela oficial', href: l.tabela }]} />;
    case 'rodadas':
      return <TelaEmMigracao titulo="Rodadas" descricao="Jogos, resultados e lançamento de palpites. Enquanto esta aba é migrada, use as telas atuais."
        atalhos={[{ label: 'Lançar palpites', href: l.palpites, destaque: true }, { label: 'Jogos e rodadas', href: l.rodadas }]} />;
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
