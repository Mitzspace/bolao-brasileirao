import { Star } from 'lucide-react';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { Badge } from '@/components/ui/Badge';
import type { JogoBase } from '@/types';

const statusInfo = {
  encerrado: { cor: 'green', texto: 'Encerrado' },
  aguardando: { cor: 'yellow', texto: 'Aguardando resultado' },
  agendado: { cor: 'gray', texto: 'Agendado' },
} as const;

/**
 * Linha de jogo do Bolt em grade fixa: as colunas de escudos, placar e situação
 * ficam alinhadas entre todas as linhas, independentemente do tamanho dos nomes.
 */
export function JogoLinha({ jogo, mostrarData = false }: { jogo: JogoBase; mostrarData?: boolean }) {
  const info = statusInfo[jogo.status];
  const temPlacar = jogo.golsCasa !== null && jogo.golsFora !== null;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_1.75rem_4.75rem_1.75rem_minmax(0,1fr)_0.5rem] sm:grid-cols-[minmax(0,1fr)_1.75rem_5.5rem_1.75rem_minmax(0,1fr)_10.5rem] items-center gap-2 sm:gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate text-right" title={jogo.casa}>
        <span className="hidden sm:inline">{jogo.casa}</span><span className="sm:hidden">{jogo.escudoCasa.sigla}</span>
      </span>
      <TeamCrest nome={jogo.casa} escudo={jogo.escudoCasa} size="xs" />
      {temPlacar ? (
        <div className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800">
          <span className="font-bold text-gray-900 dark:text-white">{jogo.golsCasa}</span>
          <span className="text-gray-400 text-xs">×</span>
          <span className="font-bold text-gray-900 dark:text-white">{jogo.golsFora}</span>
          {jogo.penaltisCasa != null && jogo.penaltisFora != null && (
            <span className="text-[10px] font-semibold text-gray-500" title="Placar dos pênaltis">({jogo.penaltisCasa}×{jogo.penaltisFora})</span>
          )}
        </div>
      ) : (
        <p className="text-[11px] leading-tight font-semibold text-gray-500 dark:text-gray-400 text-center">
          {jogo.dataTexto ? jogo.dataTexto.split(' · ').map((parte, i) => <span key={i} className="block">{parte}</span>) : 'A definir'}
        </p>
      )}
      <TeamCrest nome={jogo.fora} escudo={jogo.escudoFora} size="xs" />
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate" title={jogo.fora}>
        <span className="hidden sm:inline">{jogo.fora}</span><span className="sm:hidden">{jogo.escudoFora.sigla}</span>
      </span>
      <div className="hidden sm:flex items-center justify-end gap-1.5">
        {jogo.classico && <span title="Clássico"><Star className="w-4 h-4 text-gold-500 fill-gold-400" /></span>}
        <Badge color={info.cor}>{info.texto}</Badge>
      </div>
      <span className={`sm:hidden w-2 h-2 rounded-full justify-self-end ${jogo.status === 'encerrado' ? 'bg-brand-500' : jogo.status === 'aguardando' ? 'bg-gold-500' : 'bg-gray-300'}`} title={info.texto} />
      {mostrarData && temPlacar && jogo.dataTexto && (
        <p className="col-span-full text-center text-[11px] text-gray-400 -mt-1">{jogo.dataTexto}</p>
      )}
    </div>
  );
}
