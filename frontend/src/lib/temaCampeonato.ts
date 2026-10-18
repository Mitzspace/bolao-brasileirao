import { useEffect, useState } from 'react';

/**
 * Tema visual do campeonato. O servidor manda `tema` em cada bolão (services/competicoes.py);
 * as cores de cada tema ficam em index.css (`:root[data-tema='...']`) e o resto do app usa as
 * classes brand-/gold-/gray- de sempre, que passam a ler essas variáveis.
 */
export type TemaCampeonato = 'copa-do-mundo' | 'libertadores' | 'sul-americana' | 'copa-do-brasil' | 'mineiro' | 'brasileirao';

/** `fundo` = degradê do logo (claro, escuro); `taca` = degradê da taça (claro, escuro). */
export const TEMAS: Record<TemaCampeonato, {
  titulo: string; lema: string; fundo: [string, string]; taca: [string, string]; bandeiras?: string[];
}> = {
  'copa-do-mundo': {
    titulo: 'Copa do Mundo FIFA 2026', lema: 'Estados Unidos · México · Canadá',
    fundo: ['#1e40af', '#172554'], taca: ['#fde047', '#ca8a04'], bandeiras: ['mex', 'usa', 'can'],
  },
  'libertadores': {
    titulo: 'Copa Libertadores', lema: 'A glória eterna da América',
    fundo: ['#44403c', '#0c0a09'], taca: ['#fcd34d', '#d97706'],
  },
  'sul-americana': {
    titulo: 'Copa Sul-Americana', lema: 'A taça do continente',
    fundo: ['#0f766e', '#134e4a'], taca: ['#fde047', '#ca8a04'],
  },
  'copa-do-brasil': {
    titulo: 'Copa do Brasil', lema: 'Mata-mata, ida e volta',
    fundo: ['#15803d', '#14532d'], taca: ['#fde047', '#ca8a04'],
  },
  'brasileirao': {
    titulo: 'Campeonato Brasileiro', lema: 'Série A · pontos corridos',
    fundo: ['#4338ca', '#1e1b4b'], taca: ['#fde047', '#ca8a04'],
  },
  'mineiro': {
    titulo: 'Campeonato Mineiro', lema: 'O estadual das Gerais',
    fundo: ['#b91c1c', '#0c0a09'], taca: ['#fde047', '#ca8a04'],
  },
};

export function temaConhecido(tema?: string | null): TemaCampeonato | null {
  return tema && tema in TEMAS ? tema as TemaCampeonato : null;
}

export function aplicarTemaCampeonato(tema?: string | null) {
  const raiz = document.documentElement;
  const valido = temaConhecido(tema);
  if (valido) raiz.dataset.tema = valido;
  else delete raiz.dataset.tema;
}

/** Aplica o tema enquanto o componente existir (some ao trocar para um bolão sem tema). */
export function useTemaCampeonato(tema?: string | null) {
  useEffect(() => {
    aplicarTemaCampeonato(tema);
    return () => aplicarTemaCampeonato(null);
  }, [tema]);
}

function lerTemaAtivo(): TemaCampeonato | null {
  return temaConhecido(document.documentElement.dataset.tema);
}

/** Tema que está valendo agora na página (para logo e faixa; acompanha a troca de bolão). */
export function useTemaAtivo(): TemaCampeonato | null {
  const [tema, setTema] = useState(lerTemaAtivo);
  useEffect(() => {
    const observador = new MutationObserver(() => setTema(lerTemaAtivo()));
    observador.observe(document.documentElement, { attributes: true, attributeFilter: ['data-tema'] });
    return () => observador.disconnect();
  }, []);
  return tema;
}
