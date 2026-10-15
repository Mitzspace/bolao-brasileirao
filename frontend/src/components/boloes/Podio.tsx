import { Crown } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import type { ItemRanking } from '@/types';

export const CORES_MEDALHA = ['#fbbf24', '#cbd5e1', '#d97706'];

/** Pódio do Bolt (2º, 1º, 3º), com os três primeiros da classificação real. */
export function Podio({ ranking, compacto = false }: { ranking: ItemRanking[]; compacto?: boolean }) {
  const alturas = compacto ? ['h-20', 'h-14', 'h-11'] : ['h-28', 'h-20', 'h-16'];
  const ordem = [1, 0, 2];
  return (
    <div className="flex items-end justify-center gap-3 md:gap-8">
      {ranking.slice(0, 3).map((p, i) => (
        <div key={p.participacaoId} className="flex flex-col items-center min-w-0" style={{ order: ordem.indexOf(i) }}>
          {i === 0 && <Crown className={`${compacto ? 'w-5 h-5 text-gold-300' : 'w-6 h-6 text-gold-500'} mb-1`} />}
          <div className="rounded-full mb-2" style={{ boxShadow: `0 0 0 ${compacto ? 3 : 4}px ${CORES_MEDALHA[i]}` }}>
            <Avatar nome={p.nome} id={p.participacaoId} size={compacto ? 'md' : 'lg'} />
          </div>
          <p className={`text-xs font-semibold text-center truncate ${compacto ? 'max-w-[72px]' : 'max-w-[88px] text-gray-700 dark:text-gray-300'}`}>{p.nome.split(' ')[0]}</p>
          <p className={`text-sm font-bold ${compacto ? '' : 'text-brand-600 dark:text-brand-400'}`}>{p.pontos} pts</p>
          <div className={`${alturas[i]} ${compacto ? 'w-14 rounded-t-lg' : 'w-16 md:w-20 rounded-t-xl'} flex items-start justify-center pt-2 mt-2`} style={{ backgroundColor: CORES_MEDALHA[i] }}>
            <span className="text-white font-bold text-lg">{p.posicao ?? i + 1}º</span>
          </div>
        </div>
      ))}
    </div>
  );
}
