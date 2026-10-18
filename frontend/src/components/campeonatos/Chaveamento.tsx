import { useMemo } from 'react';
import { Trophy } from 'lucide-react';
import { TeamCrest } from '@/components/ui/TeamCrest';
import {
  CARD_H, CARD_W, GAP_X, TOPO, fasesDaChave, organizarChave,
  type Confronto,
} from '@/lib/chaveamento';
import type { TabelaApi } from '@/types';

function Linha({ time, lado, c }: { time: Confronto['a']; lado: 'a' | 'b'; c: Confronto }) {
  const ganhou = c.vencedor === lado;
  const perdeu = c.vencedor !== null && !ganhou;
  const total = lado === 'a' ? c.totalA : c.totalB;
  return (
    <div className={`flex items-center gap-2 px-2.5 h-[34px] ${ganhou ? 'bg-brand-50/70 dark:bg-brand-900/20' : ''}`}>
      <TeamCrest nome={time.nome} escudo={time.escudo} size="xs" />
      <span title={time.nome} className={`flex-1 min-w-0 truncate text-[13px] ${ganhou ? 'font-bold text-gray-900 dark:text-white' : perdeu ? 'text-gray-400 dark:text-gray-500' : 'font-medium text-gray-700 dark:text-gray-200'}`}>
        {time.nome}
      </span>
      {c.pernas.length > 1 && c.pernas.map((p, i) => (
        <span key={i} className="w-5 text-center text-xs text-gray-400 tabular-nums">{(lado === 'a' ? p.golsA : p.golsB) ?? '–'}</span>
      ))}
      <span className={`w-6 text-center text-sm tabular-nums ${ganhou ? 'font-bold text-brand-700 dark:text-brand-300' : perdeu ? 'text-gray-400' : 'font-semibold text-gray-700 dark:text-gray-200'}`}>
        {total ?? '–'}
      </span>
    </div>
  );
}

function CartaoConfronto({ c, x, y }: { c: Confronto; x?: number; y?: number }) {
  const ultima = c.pernas[c.pernas.length - 1];
  const penaltis = ultima.penA != null && ultima.penB != null ? ` · pên. ${ultima.penA}×${ultima.penB}` : '';
  const rotulo = c.pernas.length > 1 ? 'Ida e volta' : (c.pernas[0].dataTexto ?? 'A definir');
  const posicionado = x !== undefined && y !== undefined;
  return (
    <div style={posicionado ? { left: x, top: y + TOPO, width: CARD_W, height: CARD_H } : undefined}
      className={`${posicionado ? 'absolute' : 'w-full max-w-[13.25rem]'} rounded-xl overflow-hidden bg-white dark:bg-gray-900 shadow-sm border ${c.completo ? 'border-brand-200 dark:border-brand-800/60' : 'border-gray-200 dark:border-gray-700'}`}>
      <p className="h-5 px-2.5 flex items-center text-[10px] font-semibold uppercase tracking-wide text-gray-400 bg-gray-50 dark:bg-gray-800/70 truncate">{rotulo}{penaltis}</p>
      <Linha time={c.a} lado="a" c={c} />
      <div className="border-t border-gray-100 dark:border-gray-800" />
      <Linha time={c.b} lado="b" c={c} />
    </div>
  );
}

/** Chave do mata-mata: uma coluna por fase, com linhas ligando cada confronto ao da fase seguinte. */
export function Chaveamento({ dados }: { dados: TabelaApi }) {
  const { fases, terceiro } = useMemo(() => fasesDaChave(dados), [dados]);
  const chave = useMemo(() => organizarChave(fases), [fases]);
  if (!fases.length) return null;

  const final = fases[fases.length - 1];
  const campeao = final.confrontos.length === 1 && final.confrontos[0].vencedor
    ? final.confrontos[0][final.confrontos[0].vencedor] : null;

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto scrollbar-thin overscroll-x-contain pb-2">
        <div className="relative mx-auto" style={{ width: chave.largura, height: chave.altura + TOPO }}>
          <svg className="absolute inset-0 pointer-events-none" width={chave.largura} height={chave.altura + TOPO} aria-hidden="true">
            {chave.ligacoes.map(({ de, para, lado }) => {
              // Lado esquerdo: sai da borda direita do card e entra na esquerda do próximo; o direito é o espelho.
              const sinal = lado === 'e' ? 1 : -1;
              const x1 = lado === 'e' ? de.x + CARD_W : de.x, y1 = de.y + TOPO + CARD_H / 2;
              const x2 = lado === 'e' ? para.x : para.x + CARD_W, y2 = para.y + TOPO + CARD_H / 2;
              const meio = x1 + (sinal * GAP_X) / 2;
              const avancou = de.vencedor !== null && [para.a.nome, para.b.nome].includes(de[de.vencedor].nome);
              return (
                <path key={`${de.chave}>${para.chave}`} d={`M${x1} ${y1}H${meio}V${y2}H${x2}`} fill="none" strokeWidth={2}
                  strokeLinejoin="round" strokeDasharray={de.completo ? undefined : '4 4'}
                  className={avancou ? 'stroke-brand-500' : 'stroke-gray-300 dark:stroke-gray-600'} />
              );
            })}
          </svg>
          {chave.cabecalhos.map((f, k) => (
            <p key={`${f.nome}-${k}`} style={{ left: f.x, width: CARD_W, top: 0 }}
              className="absolute h-8 flex items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800 text-xs font-bold uppercase tracking-wide text-gray-600 dark:text-gray-300">
              {f.nome}
            </p>
          ))}
          {chave.colunas.flat().map(c => <CartaoConfronto key={`${c.chave}-${c.x}`} c={c} x={c.x} y={c.y} />)}
        </div>
      </div>

      {(campeao || terceiro) && (
        <div className="flex flex-wrap items-start gap-4">
          {campeao && (
            <div className="flex items-center gap-3 rounded-xl border border-gold-200 dark:border-gold-800/40 bg-gold-50 dark:bg-gold-900/20 px-4 py-3">
              <Trophy className="w-6 h-6 text-gold-500" />
              <TeamCrest nome={campeao.nome} escudo={campeao.escudo} size="sm" />
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gold-700 dark:text-gold-300">Campeão</p>
                <p className="font-bold text-gray-900 dark:text-white">{campeao.nome}</p>
              </div>
            </div>
          )}
          {terceiro?.confrontos[0] && (
            <div className="space-y-1.5">
              <p className="text-xs font-bold uppercase tracking-wide text-gray-500">{terceiro.nome}</p>
              <CartaoConfronto c={terceiro.confrontos[0]} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
