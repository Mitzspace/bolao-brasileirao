import { Clock, Star } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { TeamCrest } from '@/components/ui/TeamCrest';
import { SeletorRodadas } from '@/components/rodadas/SeletorRodadas';
import type { EstadoRodada, RodadaResumo } from '@/types';
import type { JogoPublico, RodadaPublica } from './tipos';

export const cartao = 'bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800';

const ESTADO: Record<RodadaPublica['situacao'], EstadoRodada> = { encerrada: 'fechada', andamento: 'aberta', agendada: 'aberta' };

/**
 * Rodadas no formato do carrossel do admin, identificadas pelo número (o público não recebe ids).
 * O público só vê "encerrada" ou "aberta" (nunca "pendente", que depende de palpites faltantes).
 */
export function rodadasDoSeletor(rodadas: RodadaPublica[]): RodadaResumo[] {
  return rodadas.map(r => ({ id: r.numero, numero: r.numero, nome: r.nome, estado: ESTADO[r.situacao], faltantes: 0 }));
}

/** Mesmo carrossel de rodadas do admin, dentro de um cartão. */
export function Rodadas({ rodadas, selecionada, atual, onSelecionar }: {
  rodadas: RodadaPublica[]; selecionada: number | null; atual?: number | null; onSelecionar: (numero: number) => void;
}) {
  const lista = rodadasDoSeletor(rodadas);
  return (
    <div className={`${cartao} p-3 min-w-0`}>
      <SeletorRodadas rodadas={lista} selecionadaId={selecionada} atualId={atual ?? null} onSelecionar={onSelecionar} />
    </div>
  );
}

export function StatusJogo({ jogo }: { jogo: JogoPublico }) {
  if (jogo.status === 'encerrado') return <Badge color="green">Encerrado</Badge>;
  if (jogo.status === 'aguardando') return <Badge color="yellow">Em andamento</Badge>;
  return <Badge color="gray">Agendado</Badge>;
}

/** Linha de jogo: escudos, nomes (sigla no celular) e placar ou horário. */
export function LinhaJogo({ jogo, compacto = false }: { jogo: JogoPublico; compacto?: boolean }) {
  const placar = jogo.golsCasa !== null && jogo.golsFora !== null;
  return (
    <div className={compacto ? 'py-3' : 'p-4'}>
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400 mb-2">
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{jogo.dataTexto ?? 'Horário a definir'}</span>
        {jogo.classico && <Badge color="gold" icon={<Star className="w-3 h-3" />}>Clássico</Badge>}
        <span className="ml-auto"><StatusJogo jogo={jogo} /></span>
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sm:gap-4">
        <div className="flex items-center justify-end gap-2 min-w-0">
          <span className="font-semibold text-sm text-gray-900 dark:text-white truncate text-right"><span className="hidden sm:inline">{jogo.casa}</span><span className="sm:hidden">{jogo.escudoCasa.sigla}</span></span>
          <TeamCrest nome={jogo.casa} escudo={jogo.escudoCasa} size="sm" />
        </div>
        <div className={`min-w-[4.5rem] text-center rounded-xl px-3 py-1.5 font-bold ${placar ? 'text-lg text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-800' : 'text-sm text-gray-400'}`}>
          {placar ? `${jogo.golsCasa} × ${jogo.golsFora}` : '×'}
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <TeamCrest nome={jogo.fora} escudo={jogo.escudoFora} size="sm" />
          <span className="font-semibold text-sm text-gray-900 dark:text-white truncate"><span className="hidden sm:inline">{jogo.fora}</span><span className="sm:hidden">{jogo.escudoFora.sigla}</span></span>
        </div>
      </div>
    </div>
  );
}

/** Cabeçalho de seção dentro de um cartão. */
export function Titulo({ icone, titulo, extra }: { icone: React.ReactNode; titulo: string; extra?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
      <span className="text-brand-600">{icone}</span>
      <h2 className="font-bold text-gray-900 dark:text-white">{titulo}</h2>
      {extra && <div className="ml-auto flex items-center gap-2">{extra}</div>}
    </div>
  );
}

/** Número estável a partir do nome: a mesma pessoa tem a mesma cor em todas as abas. */
export function idDoNome(nome: string) {
  let h = 0;
  for (const c of nome) h = (h * 31 + c.charCodeAt(0)) | 0;
  return Math.abs(h);
}
