import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApp } from '@/context/AppContext';
import type { DetalheParticipanteApi } from '@/types';

/** Pontos por rodada (gráfico do Bolt). Carregado sob demanda para não pesar a abertura da interface. */
export default function GraficoPontos({ evolucao }: { evolucao: DetalheParticipanteApi['evolucao'] }) {
  const { darkMode } = useApp();
  const dados = evolucao.map(e => ({ rodada: e.curto, nome: e.rodada, pontos: e.pontos, posicao: e.posicao }));
  const eixo = darkMode ? '#6b7280' : '#9ca3af';
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={dados} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#374151' : '#e5e7eb'} strokeOpacity={0.6} vertical={false} />
        <XAxis dataKey="rodada" tick={{ fontSize: 11, fill: eixo }} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={8} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: eixo }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ borderRadius: '12px', border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`, fontSize: '12px', background: darkMode ? '#111827' : '#fff', color: darkMode ? '#f3f4f6' : '#111827' }}
          labelFormatter={(_, itens) => (itens?.[0]?.payload as { nome?: string } | undefined)?.nome ?? ''}
          formatter={(valor, _nome, item) => {
            const pos = (item?.payload as { posicao?: number } | undefined)?.posicao;
            return [valor === null || valor === undefined ? 'Fora da rodada' : `${valor} pts · ${pos}º no geral`, 'Pontos'];
          }}
        />
        <Line type="monotone" dataKey="pontos" stroke="#059669" strokeWidth={2.5} connectNulls={false}
          dot={{ fill: '#059669', r: 4 }} activeDot={{ r: 6 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
