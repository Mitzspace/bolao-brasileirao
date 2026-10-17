import { useMemo, useState } from 'react';
import { ChevronDown, Lock, Search } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Switch } from '@/components/ui/Form';
import { useRecurso } from '@/lib/useRecurso';
import { cartao, idDoNome, LinhaJogo, Rodadas } from '../comum';
import type { AbrirParticipante, JogoComPalpites, PalpitePublico, PalpitesApi } from '../tipos';

const SEM_PALPITE: Record<string, string> = { sem_palpite: 'Sem palpite', nao_enviado: 'Não enviou', fora_prazo: 'Fora do prazo' };

function Palpite({ p, pontos, onAbrir }: { p: PalpitePublico; pontos: boolean; onAbrir: AbrirParticipante }) {
  const valido = p.situacao === 'valido';
  return (
    <li className="flex items-center gap-2.5 py-2 min-w-0">
      <Avatar nome={p.nome} id={idDoNome(p.nome)} />
      <span className="flex-1 min-w-0 text-sm text-gray-800 dark:text-gray-200 truncate">
        <button type="button" onClick={() => onAbrir(p)} className="hover:underline text-left">{p.nome}</button>
        {p.status === 'desistente' && <span className="text-xs text-gray-400"> · desistente</span>}
        {p.primeiroGol && <span className="block text-xs text-gold-600 dark:text-gold-400 truncate">1º gol: {p.primeiroGol}</span>}
      </span>
      <span className={`text-sm font-bold tabular-nums ${valido ? 'text-gray-900 dark:text-white' : 'text-xs font-medium text-gray-400'}`}>
        {valido ? `${p.casa} × ${p.fora}` : SEM_PALPITE[p.situacao]}
      </span>
      {pontos && (
        <span className={`min-w-[3rem] text-center text-xs font-bold rounded-full px-2 py-0.5 ${p.pontos ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300' : 'bg-gray-100 text-gray-400 dark:bg-gray-800'}`}>
          {p.pontos} pt{p.pontos === 1 ? '' : 's'}
        </span>
      )}
    </li>
  );
}

function CartaoJogo({ jogo, pontos, liberada, filtro, aberto, onAlternar, onAbrir }: {
  jogo: JogoComPalpites; pontos: boolean; liberada: boolean; filtro: (p: PalpitePublico) => boolean; aberto: boolean;
  onAlternar: () => void; onAbrir: AbrirParticipante;
}) {
  const lista = jogo.palpites?.filter(filtro) ?? [];
  return (
    <div className={`${cartao} overflow-hidden`}>
      <LinhaJogo jogo={jogo} />
      {jogo.revelado ? (
        <>
          <button onClick={onAlternar} aria-expanded={aberto}
            className="w-full flex items-center justify-between gap-2 px-4 py-2.5 border-t border-gray-100 dark:border-gray-800 text-sm font-semibold text-brand-700 dark:text-brand-300 hover:bg-gray-50 dark:hover:bg-gray-800/50">
            {aberto ? 'Esconder palpites' : `Ver palpites (${lista.length})`}
            <ChevronDown className={`w-4 h-4 transition-transform ${aberto ? 'rotate-180' : ''}`} />
          </button>
          {aberto && (
            <ul className="px-4 pb-2 divide-y divide-gray-50 dark:divide-gray-800/60 animate-fade-in">
              {lista.map(p => <Palpite key={p.ref} p={p} pontos={pontos} onAbrir={onAbrir} />)}
              {lista.length === 0 && <li className="py-3 text-sm text-gray-400 text-center">Ninguém com esse nome nesta rodada.</li>}
            </ul>
          )}
        </>
      ) : (
        <p className="flex items-center gap-2 px-4 py-3 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400">
          <Lock className="w-3.5 h-3.5 shrink-0" />
          {liberada ? 'Os palpites aparecem depois que o resultado deste jogo for lançado.' : 'Palpites desta rodada ainda não liberados pelos organizadores.'}
        </p>
      )}
    </div>
  );
}

/** Palpites da rodada: só de rodadas liberadas e jogos com resultado (o servidor nem envia os demais). */
export function Palpites({ onAbrirParticipante }: { onAbrirParticipante: AbrirParticipante }) {
  const [numero, setNumero] = useState<number | null>(null);
  const [busca, setBusca] = useState('');
  const [ocultar, setOcultar] = useState(true);
  const [abertos, setAbertos] = useState<Record<string, boolean>>({});
  const { dados, carregando, erro, recarregar } = useRecurso<PalpitesApi>(numero ? `/palpites?rodada=${numero}` : '/palpites');
  const termo = busca.trim().toLocaleLowerCase('pt-BR');
  const filtro = useMemo(() => (p: PalpitePublico) =>
    (!ocultar || p.status !== 'desistente') && (!termo || p.nome.toLocaleLowerCase('pt-BR').includes(termo)), [ocultar, termo]);

  if (erro && !dados) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!dados) return <Carregando linhas={5} />;
  const r = dados.rodada;
  const chave = (i: number) => `${r?.numero}-${i}`;
  return (
    <div className="space-y-4">
      <Rodadas rodadas={dados.rodadas} selecionada={numero ?? r?.numero ?? null} onSelecionar={n => { setNumero(n); setAbertos({}); }} />
      <div className={`${cartao} p-4 space-y-3`}>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar participante" aria-label="Buscar participante"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
        </div>
        <Switch checked={ocultar} onChange={setOcultar} label="Ocultar desistentes" />
        <p className={`flex items-start gap-2 text-xs ${dados.palpitesLiberados ? 'text-gray-500 dark:text-gray-400' : 'text-gold-700 dark:text-gold-300'}`}>
          {!dados.palpitesLiberados && <Lock className="w-3.5 h-3.5 shrink-0 mt-px" />}
          {dados.palpitesLiberados
            ? 'Rodada liberada: palpites e pontos aparecem nos jogos com resultado.'
            : dados.tabela
              ? `Os palpites estão liberados até a ${dados.tabela.nome}. Esta rodada aparece quando os organizadores liberarem.`
              : 'Os palpites aparecem quando os organizadores liberarem a classificação.'}
        </p>
      </div>
      <div className={`space-y-3 transition-opacity ${carregando ? 'opacity-60' : ''}`}>
        {dados.jogos.map((j, i) => (
          <CartaoJogo key={chave(i)} jogo={j} pontos={dados.pontosLiberados} liberada={dados.palpitesLiberados} filtro={filtro}
            aberto={!!termo || !!abertos[chave(i)]} onAlternar={() => setAbertos(a => ({ ...a, [chave(i)]: !a[chave(i)] }))}
            onAbrir={onAbrirParticipante} />
        ))}
        {dados.jogos.length === 0 && <p className="text-sm text-gray-400 text-center py-10">Nenhum jogo nesta rodada.</p>}
      </div>
    </div>
  );
}
