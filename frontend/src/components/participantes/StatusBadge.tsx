import { Badge } from '@/components/ui/Badge';
import type { StatusParticipacao } from '@/types';

const ROTULOS: Record<StatusParticipacao, { texto: string; cor: 'green' | 'yellow' | 'gray' }> = {
  ativo: { texto: 'Ativo', cor: 'green' },
  desistente: { texto: 'Desistente', cor: 'yellow' },
  removido: { texto: 'Removido', cor: 'gray' },
  saiu: { texto: 'Saiu', cor: 'gray' },
};

export function StatusBadge({ status, size = 'sm' }: { status: StatusParticipacao; size?: 'sm' | 'md' }) {
  const r = ROTULOS[status] ?? { texto: status, cor: 'gray' as const };
  return <Badge color={r.cor} size={size}>{r.texto}</Badge>;
}
