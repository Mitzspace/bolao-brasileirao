import { Calendar, CheckCircle2, Trophy, Users } from 'lucide-react';
import { PainelDashboard, type IndicadorDashboard } from '@/components/dashboard/PainelDashboard';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useRecurso } from '@/lib/useRecurso';
import { idDoNome } from '../comum';
import type { AbrirParticipante, InicioApi } from '../tipos';

/**
 * Dashboard da gestão reaproveitado na página pública, sem "palpites faltantes" e sem lançar palpites.
 * O quarto indicador mostra o líder (ou "Em breve" enquanto a classificação não é divulgada).
 */
export function Inicio({ onVerClassificacao, onAbrirParticipante }: { onVerClassificacao: () => void; onAbrirParticipante: AbrirParticipante }) {
  const { dados, erro, recarregar } = useRecurso<InicioApi>('/inicio');
  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={4} />;
  const r = dados.rodada;
  const lider = dados.lideres?.[0];
  const indicadores: IndicadorDashboard[] = [
    { label: 'Participantes ativos', value: dados.participantesAtivos, icon: Users, color: 'purple' },
    { label: 'Rodada atual', value: r ? `${r.numero}/${r.total}` : '—', icon: Calendar, color: 'blue' },
    { label: dados.tabela ? `Líder até a ${dados.tabela.nome}` : 'Líder', value: lider ? lider.nome : 'Em breve', icon: Trophy, color: 'gold' },
    { label: 'Jogos encerrados na rodada', value: r ? `${r.comResultado}/${r.jogos}` : '—', icon: CheckCircle2, color: 'brand' },
  ];
  return (
    <div className="space-y-6">
      <PainelDashboard
        bolao={dados.bolao}
        saudacao="Acompanhe o bolão"
        rodadaNome={r?.nome}
        indicadores={indicadores}
        top5={dados.lideres?.map(l => ({ chave: l.ref, avatarId: idDoNome(l.nome), nome: l.nome, posicao: l.posicao,
          cravadas: l.cravadas, pontos: l.pontos, variacao: l.variacao })) ?? null}
        notaVariacao={dados.tabela ? `Classificação até a ${dados.tabela.nome}${dados.variacaoReferencia ? ` · variação em relação à ${dados.variacaoReferencia}` : ''}` : null}
        onVerClassificacao={onVerClassificacao}
        onAbrirLider={l => onAbrirParticipante({ ref: String(l.chave), nome: l.nome })}
        jogos={dados.jogos}
      />
    </div>
  );
}
