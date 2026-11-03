import { useRef } from 'react';
import { REGRAS_PADRAO, type Regras } from '@/types';

export const CAMPOS_REGRAS: { chave: keyof Regras; label: string; desc: string; extra?: boolean }[] = [
  { chave: 'comumExato', label: 'Placar exato', desc: 'Jogo comum' },
  { chave: 'comumResultado', label: 'Vencedor ou empate', desc: 'Jogo comum, sem acertar o placar' },
  { chave: 'classicoExato', label: 'Placar exato em clássico', desc: 'Jogo marcado como clássico' },
  { chave: 'classicoResultado', label: 'Vencedor ou empate em clássico', desc: 'Clássico, sem acertar o placar' },
  { chave: 'primeiroGol', label: 'Bônus de primeiro gol', desc: 'No clássico, acertar quem marcou primeiro (vale gol contra; não vale em 0×0)', extra: true },
  { chave: 'penaltisExato', label: 'Placar exato dos pênaltis', desc: 'Jogo decidido nos pênaltis; soma aos pontos do jogo', extra: true },
  { chave: 'penaltisVencedor', label: 'Vencedor nos pênaltis', desc: 'Acertou só quem venceu a disputa de pênaltis', extra: true },
];

export type RegrasEditaveis = Record<keyof Regras, string>;

export function paraEdicao(r: Regras): RegrasEditaveis {
  // Respostas antigas sem as chaves dos pênaltis caem nos valores padrão.
  return Object.fromEntries(CAMPOS_REGRAS.map(c => [c.chave, String(r[c.chave] ?? REGRAS_PADRAO[c.chave])])) as RegrasEditaveis;
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
  if (numeros.penaltisExato < numeros.penaltisVencedor)
    return { regras: null, erro: 'O placar exato dos pênaltis precisa valer pelo menos o mesmo que acertar só o vencedor.' };
  return { regras: numeros, erro: '' };
}

/** Lista de regras no estilo do Bolt (campo numérico + "pts"). */
export function EditorRegras({ valores, onChange, somenteLeitura = false }: { valores: RegrasEditaveis; onChange?: (v: RegrasEditaveis) => void; somenteLeitura?: boolean }) {
  // Bônus de primeiro gol desligado = 0 ponto. Ao religar, volta o último valor usado (ou o padrão).
  const ultimoPrimeiroGol = useRef(Number(valores.primeiroGol) > 0 ? valores.primeiroGol : String(REGRAS_PADRAO.primeiroGol));
  const primeiroGolLigado = Number(valores.primeiroGol || 0) > 0 || valores.primeiroGol === '';
  if (Number(valores.primeiroGol) > 0) ultimoPrimeiroGol.current = valores.primeiroGol;
  const alternarPrimeiroGol = () => onChange?.({ ...valores, primeiroGol: primeiroGolLigado ? '0' : ultimoPrimeiroGol.current });
  return (
    <div className="space-y-3">
      {CAMPOS_REGRAS.map(r => {
        const bonusGol = r.chave === 'primeiroGol';
        const desligado = bonusGol && !primeiroGolLigado;
        return (
        <div key={r.chave} className="flex items-center justify-between gap-4 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{r.label}</p>
            <p className="text-xs text-gray-400">
              {desligado ? 'Desligado: o campo de primeiro gol some do lançamento e ninguém pontua com ele.' : r.desc}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {bonusGol && (
              <button type="button" role="switch" aria-checked={primeiroGolLigado} aria-label="Usar bônus de primeiro gol"
                disabled={somenteLeitura} onClick={alternarPrimeiroGol}
                className={`relative w-12 rounded-full transition-colors shrink-0 disabled:opacity-60 ${primeiroGolLigado ? 'bg-brand-500' : 'bg-gray-300 dark:bg-gray-700'}`}
                style={{ height: '26px' }}>
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${primeiroGolLigado ? 'translate-x-6' : ''}`} />
              </button>
            )}
            {!desligado && <>
            {r.extra && <span className="text-sm font-bold text-gray-400">+</span>}
            <input type="text" inputMode="numeric" maxLength={2} value={valores[r.chave]} readOnly={somenteLeitura}
              aria-label={`${r.label} (pontos)`}
              onChange={e => onChange?.({ ...valores, [r.chave]: e.target.value.replace(/\D/g, '') })}
              className="w-16 h-10 text-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-500/40 read-only:bg-gray-50 dark:read-only:bg-gray-800" />
            <span className="text-xs text-gray-400">pts</span>
            </>}
          </div>
        </div>
        );
      })}
    </div>
  );
}
