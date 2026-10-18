import type { FonteApi } from '@/types';

/** Código da liga como a API espera: slug minúsculo na ESPN, maiúsculo nas demais fontes. */
export const normalizarCodigoApi = (fonte: FonteApi, codigo: string) =>
  fonte === 'espn' ? codigo.trim().toLowerCase() : codigo.trim().toUpperCase();
