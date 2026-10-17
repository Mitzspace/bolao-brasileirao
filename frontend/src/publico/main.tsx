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
// Tema: o App segue o aparelho até a pessoa escolher claro/escuro (escolha salva no navegador).

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BarraProgresso />
    <AppPublico dados={dados} />
  </StrictMode>
);
