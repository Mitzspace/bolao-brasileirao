import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api';

interface Recurso<T> {
  dados: T | null;
  carregando: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
}

/** Carrega um GET da API e permite recarregar depois de uma gravação. */
export function useRecurso<T>(caminho: string | null): Recurso<T> {
  const [dados, setDados] = useState<T | null>(null);
  const [carregando, setCarregando] = useState(caminho !== null);
  const [erro, setErro] = useState<string | null>(null);
  const ultimo = useRef(0);

  const recarregar = useCallback(async () => {
    if (caminho === null) return;
    const pedido = ++ultimo.current;
    setCarregando(true);
    setErro(null);
    try {
      const resposta = await api.get<T>(caminho);
      if (pedido === ultimo.current) setDados(resposta);
    } catch (e) {
      if (pedido === ultimo.current) setErro(e instanceof Error ? e.message : 'Erro inesperado.');
    } finally {
      if (pedido === ultimo.current) setCarregando(false);
    }
  }, [caminho]);

  useEffect(() => { void recarregar(); }, [recarregar]);

  return { dados, carregando, erro, recarregar };
}
