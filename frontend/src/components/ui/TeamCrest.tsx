import { useState } from 'react';
import type { Escudo } from '@/types';

interface TeamCrestProps {
  nome: string;
  /** Fontes e iniciais calculadas no servidor por services/escudos.py. */
  escudo?: Escudo | null;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

const sizes = {
  xs: 'w-7 h-7 text-[9px]',
  sm: 'w-9 h-9 text-[10px]',
  md: 'w-12 h-12 text-xs',
  lg: 'w-16 h-16 text-sm',
  xl: 'w-20 h-20 text-base',
};

/** Escudo oficial quando houver; senão o círculo com as iniciais, como no Bolt. */
export function TeamCrest({ nome, escudo, size = 'md' }: TeamCrestProps) {
  const fontes = escudo?.fontes ?? [];
  const [indice, setIndice] = useState(0);
  const fonte = fontes[indice];
  const iniciais = escudo?.iniciais ?? (nome.split(/\s+/).slice(0, 2).map(p => p[0]).join('').toUpperCase() || '?');

  if (fonte) {
    return (
      <div className={`${sizes[size]} rounded-full flex items-center justify-center shrink-0 bg-white dark:bg-gray-800 shadow-sm ring-2 ring-white dark:ring-gray-800 overflow-hidden`} title={nome}>
        <img src={fonte} alt="" loading="lazy" className="w-[78%] h-[78%] object-contain" onError={() => setIndice(i => i + 1)} />
      </div>
    );
  }
  return (
    <div className={`${sizes[size]} rounded-full flex items-center justify-center font-bold shrink-0 shadow-sm ring-2 ring-white dark:ring-gray-800 bg-gray-700 text-white`} title={nome}>
      {iniciais}
    </div>
  );
}
