import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis, usePlotArea, useXAxisScale } from 'recharts';
import { useEscuroAtual } from '@/lib/tema';
import type { PontoEvolucao } from './PainelDesempenho';

interface Ponto { chave: string; curto: string; nome: string; pontos: number | null; posicao: number; acumulado: number; cravadas: number }

/**
 * Faixas de toque invisíveis, uma por rodada, ocupando toda a altura do gráfico e a largura
 * entre os vizinhos: tocar em qualquer lugar da "coluna" seleciona a rodada (sem depender de hover
 * e sem precisar acertar o ponto). Não bloqueiam a rolagem vertical da página (touch-action: pan-y).
 */
function FaixasDeToque({ dados, selecionado, onSelecionar }: { dados: Ponto[]; selecionado: number; onSelecionar: (i: number) => void }) {
  const area = usePlotArea();
  const escala = useXAxisScale();
  if (!area || !escala) return null;
  const xs = dados.map(d => escala(d.chave) ?? area.x);
  return (
    <g>
      {xs.map((x, i) => {
        const inicio = i === 0 ? area.x : (xs[i - 1] + x) / 2;
        const fim = i === xs.length - 1 ? area.x + area.width : (x + xs[i + 1]) / 2;
        return (
          <rect key={dados[i].chave} x={inicio} y={area.y} width={Math.max(fim - inicio, 1)} height={area.height}
            fill="transparent" style={{ cursor: 'pointer', touchAction: 'pan-y' }}
            onClick={() => onSelecionar(i)} onMouseEnter={() => onSelecionar(i)}
            aria-hidden={i !== selecionado} />
        );
      })}
    </g>
  );
}

/** Pontos por rodada. Carregado sob demanda para não pesar a abertura da página. */
export default function GraficoPontos({ evolucao }: { evolucao: PontoEvolucao[] }) {
  const escuro = useEscuroAtual();
  const dados: Ponto[] = useMemo(() => evolucao.map(e => ({
    chave: String(e.chave), curto: e.curto, nome: e.rodada, pontos: e.pontos, posicao: e.posicao,
    acumulado: e.acumulado, cravadas: e.cravadas,
  })), [evolucao]);
  const ultimoValido = useMemo(() => {
    for (let i = dados.length - 1; i >= 0; i--) if (dados[i].pontos !== null) return i;
    return dados.length - 1;
  }, [dados]);
  const rotulos = useMemo(() => new Map(dados.map(d => [d.chave, d.curto])), [dados]);
  const [selecionado, setSelecionado] = useState(ultimoValido);
  useEffect(() => { setSelecionado(ultimoValido); }, [ultimoValido]);

  const eixo = escuro ? '#9ca3af' : '#6b7280';
  const atual = dados[selecionado];
  const ir = (delta: number) => setSelecionado(i => Math.min(dados.length - 1, Math.max(0, i + delta)));
  const seta = 'shrink-0 w-11 h-11 rounded-xl flex items-center justify-center border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors';

  return (
    <div>
      <div className="select-none [-webkit-tap-highlight-color:transparent]" style={{ touchAction: 'pan-y' }}
        role="img" aria-label={`Gráfico de pontos por rodada. ${dados.length} rodadas.`}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={dados} margin={{ top: 12, right: 12, bottom: 0, left: -20 }} accessibilityLayer={false}>
            <CartesianGrid strokeDasharray="3 3" stroke={escuro ? '#374151' : '#e5e7eb'} strokeOpacity={0.6} vertical={false} />
            <XAxis dataKey="chave" tickFormatter={v => rotulos.get(String(v)) ?? ''} tick={{ fontSize: 11, fill: eixo }}
              tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={8} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: eixo }} tickLine={false} axisLine={false} />
            {atual && <ReferenceLine x={atual.chave} stroke={escuro ? '#4b5563' : '#d1d5db'} strokeWidth={1.5} />}
            <Line type="monotone" dataKey="pontos" stroke="#059669" strokeWidth={2.5} connectNulls={false} isAnimationActive={false}
              activeDot={false}
              dot={(props: { cx?: number; cy?: number; index?: number }) => {
                const { cx, cy, index } = props;
                if (cx == null || cy == null) return <g key={`p-${index}`} />;
                const ativo = index === selecionado;
                return (
                  <circle key={`p-${index}`} cx={cx} cy={cy} r={ativo ? 7 : 4.5}
                    fill={ativo ? '#059669' : (escuro ? '#111827' : '#fff')} stroke="#059669" strokeWidth={ativo ? 3 : 2} />
                );
              }} />
            <FaixasDeToque dados={dados} selecionado={selecionado} onSelecionar={setSelecionado} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Detalhe da rodada escolhida: fixo abaixo do gráfico, legível no celular e sem cobrir os pontos. */}
      {atual && (
        <div className="mt-3 flex items-center gap-2" aria-live="polite">
          <button onClick={() => ir(-1)} disabled={selecionado <= 0} aria-label="Rodada anterior" className={seta}><ChevronLeft className="w-5 h-5" /></button>
          <div className="flex-1 min-w-0 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-700 px-3 py-2 text-center">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 truncate">{atual.nome}</p>
            {atual.pontos === null ? (
              <p className="text-sm font-semibold text-gray-500 dark:text-gray-400">Fora desta rodada</p>
            ) : (
              <p className="text-base font-bold text-gray-900 dark:text-white">
                {atual.pontos} {atual.pontos === 1 ? 'ponto' : 'pontos'}
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400"> · {atual.posicao}º no geral</span>
              </p>
            )}
            <p className="text-[11px] text-gray-400">{atual.acumulado} pts acumulados · {atual.cravadas} {atual.cravadas === 1 ? 'cravada' : 'cravadas'}</p>
          </div>
          <button onClick={() => ir(1)} disabled={selecionado >= dados.length - 1} aria-label="Próxima rodada" className={seta}><ChevronRight className="w-5 h-5" /></button>
        </div>
      )}
      <p className="mt-2 text-[11px] text-gray-400 text-center">Toque no gráfico ou use as setas para ver cada rodada.</p>
    </div>
  );
}
