import { useState } from 'react';
import { Share2 } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Header } from '@/components/layout/Header';
import { CartaoClassificacao, useClassificacao } from '@/components/boloes/CartaoClassificacao';
import { CompartilharClassificacao } from '@/components/boloes/CompartilharClassificacao';
import { Carregando, ErroCarga } from '@/components/ui/Estado';

/** Tabela de pontuação do bolão selecionado, direto na navegação principal. */
export function TabelaScreen() {
  const { bolao } = useApp();
  // App.tsx só abre esta tela com bolão selecionado.
  return bolao ? <Conteudo bolaoId={bolao.id} subtitulo={`${bolao.campeonato} ${bolao.ano ?? ''}`} /> : null;
}

function Conteudo({ bolaoId, subtitulo }: { bolaoId: number; subtitulo: string }) {
  const { dados, carregando, erro, recarregar, rodadaId, setRodadaId, ocultar, setOcultar } = useClassificacao(bolaoId);
  const [compartilhar, setCompartilhar] = useState(false);
  return (
    <div>
      <Header title="Tabela de pontuação" subtitle={subtitulo}
        actions={dados ? (
          <button onClick={() => setCompartilhar(true)} aria-label="Compartilhar classificação"
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-semibold hover:bg-brand-100 transition-colors">
            <Share2 className="w-4 h-4" /><span className="hidden sm:inline">Compartilhar</span>
          </button>
        ) : undefined} />
      <div className="p-4 md:p-8 pb-28 md:pb-8 space-y-5">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={4} />}
        {dados && (
          <>
            <CartaoClassificacao bolaoId={bolaoId} dados={dados} rodadaId={rodadaId} setRodadaId={setRodadaId} ocultar={ocultar} setOcultar={setOcultar} />
            <CompartilharClassificacao dados={dados} aberto={compartilhar} onClose={() => setCompartilhar(false)} />
          </>
        )}
      </div>
    </div>
  );
}
