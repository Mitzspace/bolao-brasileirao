import type { Regras } from '@/types';

export const CAMPOS_REGRAS: { chave: keyof Regras; label: string; desc: string; extra?: boolean }[] = [
  { chave: 'comumExato', label: 'Placar exato', desc: 'Jogo comum' },
  { chave: 'comumResultado', label: 'Vencedor ou empate', desc: 'Jogo comum, sem acertar o placar' },
  { chave: 'classicoExato', label: 'Placar exato em clássico', desc: 'Jogo marcado como clássico' },
  { chave: 'classicoResultado', label: 'Vencedor ou empate em clássico', desc: 'Clássico, sem acertar o placar' },
  { chave: 'primeiroGol', label: 'Primeiro gol', desc: 'Bônus no clássico ao acertar quem marcou primeiro (não vale em 0×0)', extra: true },
];

export type RegrasEditaveis = Record<keyof Regras, string>;

export function paraEdicao(r: Regras): RegrasEditaveis {
  return Object.fromEntries(CAMPOS_REGRAS.map(c => [c.chave, String(r[c.chave])])) as RegrasEditaveis;
}

/** Mesmas regras do servidor: inteiros de 0 a 99 e exato ≥ resultado. */
export function validarRegras(r: RegrasEditaveis): { regras: Regras | null; erro: string } {
  const numeros = {} as Regras;
  for (const c of CAMPOS_REGRAS) {
    const v = r[c.chave].trim();
    if (!/^\d{1,2}$/.test(v)) return { regras: null, erro: 'Use números inteiros de 0 a 99.' };
    numeros[c.chave] = Number(v);
  }
  if (numeros.comumExato < numeros.comumResultado || numeros.classicoExato < numeros.classicoResultado)
    return { regras: null, erro: 'O placar exato precisa valer pelo menos o mesmo que acertar só o resultado.' };
  return { regras: numeros, erro: '' };
}

/** Lista de regras no estilo do Bolt (campo numérico + "pts"). */
export function EditorRegras({ valores, onChange, somenteLeitura = false }: { valores: RegrasEditaveis; onChange?: (v: RegrasEditaveis) => void; somenteLeitura?: boolean }) {
  return (
    <div className="space-y-3">
      {CAMPOS_REGRAS.map(r => (
        <div key={r.chave} className="flex items-center justify-between gap-4 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{r.label}</p>
            <p className="text-xs text-gray-400">{r.desc}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {r.extra && <span className="text-sm font-bold text-gray-400">+</span>}
            <input type="text" inputMode="numeric" maxLength={2} value={valores[r.chave]} readOnly={somenteLeitura}
              aria-label={`${r.label} (pontos)`}
              onChange={e => onChange?.({ ...valores, [r.chave]: e.target.value.replace(/\D/g, '') })}
              className="w-16 h-10 text-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-500/40 read-only:bg-gray-50 dark:read-only:bg-gray-800" />
            <span className="text-xs text-gray-400">pts</span>
          </div>
        </div>
      ))}
    </div>
  );
}
