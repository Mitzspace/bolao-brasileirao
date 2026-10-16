import { useCallback, useEffect, useRef, useState } from 'react';
import { api, lerDoCache } from './api';

interface Recurso<T> {
  dados: T | null;
  /** true enquanto busca no servidor (inclusive atualizando dados já exibidos). */
  carregando: boolean;
  /** true quando os dados exibidos são do cache e a versão nova ainda não chegou. */
  desatualizado: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
}

/**
 * Carrega um GET da API e permite recarregar depois de uma gravação.
 *
 * Ao voltar para uma aba já visitada, mostra na hora o que estava guardado e
 * atualiza em segundo plano (a barra de progresso no topo indica a atualização).
 */
export function useRecurso<T>(caminho: string | null): Recurso<T> {
  const [dados, setDados] = useState<T | null>(() => (caminho ? lerDoCache<T>(caminho) ?? null : null));
  const [carregando, setCarregando] = useState(caminho !== null);
  const [desatualizado, setDesatualizado] = useState(() => !!(caminho && lerDoCache<T>(caminho) !== undefined));
  const [erro, setErro] = useState<string | null>(null);
  const ultimo = useRef(0);

  const recarregar = useCallback(async () => {
    if (caminho === null) return;
    const pedido = ++ultimo.current;
    const guardado = lerDoCache<T>(caminho);
    if (guardado !== undefined) {
      setDados(guardado);
      setDesatualizado(true);
    }
    setCarregando(true);
    setErro(null);
    try {
      const resposta = await api.get<T>(caminho);
      if (pedido === ultimo.current) {
        setDados(resposta);
        setDesatualizado(false);
      }
    } catch (e) {
      if (pedido === ultimo.current) setErro(e instanceof Error ? e.message : 'Erro inesperado.');
    } finally {
      if (pedido === ultimo.current) setCarregando(false);
    }
  }, [caminho]);

  useEffect(() => { void recarregar(); }, [recarregar]);

  return { dados, carregando, desatualizado, erro, recarregar };
}
