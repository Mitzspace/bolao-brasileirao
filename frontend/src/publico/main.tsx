import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { configurarApi } from '@/lib/api';
import { BarraProgresso } from '@/components/layout/BarraProgresso';
import { AppPublico } from './App';
import type { DadosPagina } from './tipos';
import '../index.css';

const elemento = document.getElementById('publico-data');
const dados: DadosPagina = JSON.parse(elemento?.textContent || '{}');
// Somente leitura: nenhuma gravação sai desta página (sem token CSRF).
configurarApi({ base: dados.apiBase, csrfToken: '' });
// Tema segue o celular/computador de quem abre.
const escuro = window.matchMedia?.('(prefers-color-scheme: dark)');
const aplicarTema = () => document.documentElement.classList.toggle('dark', !!escuro?.matches);
aplicarTema();
escuro?.addEventListener?.('change', aplicarTema);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BarraProgresso />
    <AppPublico dados={dados} />
  </StrictMode>
);
