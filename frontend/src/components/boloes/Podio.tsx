import { Crown } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import type { ItemRanking } from '@/types';

export const CORES_MEDALHA = ['#fbbf24', '#cbd5e1', '#d97706'];
/** Degradês dos degraus do pódio (claro em cima, escuro embaixo): ouro, prata e bronze. */
const DEGRADE_MEDALHA = [
  ['#fde68a', '#d97706'],
  ['#f1f5f9', '#64748b'],
  ['#fdba74', '#9a3412'],
];

/**
 * Pódio do Bolt (2º, 1º, 3º), com os três primeiros da classificação real.
 * Normal: um "palco" escuro de estádio, com refletor e linhas do gramado.
 * Compacto: só os degraus, para quem já está sobre fundo colorido.
 */
export function Podio({ ranking, compacto = false }: { ranking: ItemRanking[]; compacto?: boolean }) {
  const ordem = [1, 0, 2];
  if (compacto) {
    const alturas = ['h-20', 'h-14', 'h-11'];
    return (
      <div className="flex items-end justify-center gap-3 md:gap-8">
        {ranking.slice(0, 3).map((p, i) => (
          <div key={p.participacaoId} className="flex flex-col items-center min-w-0" style={{ order: ordem.indexOf(i) }}>
            {i === 0 && <Crown className="w-5 h-5 text-gold-300 mb-1" />}
            <div className="rounded-full mb-2" style={{ boxShadow: `0 0 0 3px ${CORES_MEDALHA[i]}` }}>
              <Avatar nome={p.nome} id={p.participacaoId} size="md" />
            </div>
            <p className="text-xs font-semibold text-center truncate max-w-[72px]">{p.nome.split(' ')[0]}</p>
            <p className="text-sm font-bold">{p.pontos} pts</p>
            <div className={`${alturas[i]} w-14 rounded-t-lg flex items-start justify-center pt-2 mt-2`} style={{ backgroundColor: CORES_MEDALHA[i] }}>
              <span className="text-white font-bold text-lg">{p.posicao ?? i + 1}º</span>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const alturas = ['h-32 sm:h-36', 'h-24 sm:h-28', 'h-20 sm:h-24'];
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-gray-950 via-brand-950 to-brand-900 px-3 pt-7 text-white shadow-inner">
      <div aria-hidden="true" className="absolute inset-0 linhas-campo opacity-50" />
      <div aria-hidden="true" className="absolute -top-28 left-1/2 -translate-x-1/2 w-96 h-56 rounded-full bg-gold-300/25 blur-3xl" />
      <div className="relative flex items-end justify-center gap-2 sm:gap-5">
        {ranking.slice(0, 3).map((p, i) => (
          <div key={p.participacaoId} className="flex flex-col items-center min-w-0 animate-slide-up" style={{ order: ordem.indexOf(i), animationDelay: `${ordem.indexOf(i) * 80}ms` }}>
            {i === 0 && <Crown className="w-7 h-7 text-gold-300 mb-1 drop-shadow-[0_0_8px_rgba(253,224,71,0.6)]" />}
            <div className="rounded-full mb-2 p-[3px]" style={{ background: `linear-gradient(135deg, ${DEGRADE_MEDALHA[i][0]}, ${DEGRADE_MEDALHA[i][1]})` }}>
              <div className="rounded-full ring-2 ring-gray-950"><Avatar nome={p.nome} id={p.participacaoId} size="lg" /></div>
            </div>
            <p className="text-sm font-semibold text-center truncate max-w-[92px] sm:max-w-[120px]" title={p.nome}>{p.nome.split(' ')[0]}</p>
            <p className="mt-1 mb-2 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-bold backdrop-blur-sm">{p.pontos} pts</p>
            <div className={`${alturas[i]} w-[5.5rem] sm:w-32 rounded-t-2xl relative flex items-start justify-center pt-3 shadow-[inset_0_2px_0_rgba(255,255,255,0.5)]`}
              style={{ background: `linear-gradient(180deg, ${DEGRADE_MEDALHA[i][0]}, ${DEGRADE_MEDALHA[i][1]})` }}>
              <span className="text-3xl font-black text-white/95 drop-shadow-[0_2px_2px_rgba(0,0,0,0.35)]">{p.posicao ?? i + 1}º</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
