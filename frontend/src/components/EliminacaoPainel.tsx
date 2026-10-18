import { useRef, useState, type FormEvent } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Cartao } from '@/components/configuracoes/Secoes';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Input, Select, Switch } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';

type Configuracao = {
  eliminacaoParticipantes: boolean;
  cortes: { id: number; rodadaId: number; rodadaNome: string; classificados: number }[];
  rodadas: { id: number; nome: string }[];
};
type Mensagem = { mensagem: string };

export function EliminacaoPainel() {
  const { dados, carregando, erro, recarregar } = useRecurso<Configuracao>('/eliminacao');
  const toast = useToast();
  const [rodada, setRodada] = useState('');
  const [classificados, setClassificados] = useState('');
  const [enviando, setEnviando] = useState(false);
  const ocupado = useRef(false);

  const enviar = async (acao: () => Promise<Mensagem>, limpar = false) => {
    if (ocupado.current) return;
    ocupado.current = true;
    setEnviando(true);
    try {
      const resposta = await acao();
      toast(resposta.mensagem);
      if (limpar) { setRodada(''); setClassificados(''); }
      await recarregar();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    } finally { ocupado.current = false; setEnviando(false); }
  };
  const adicionar = (e: FormEvent) => {
    e.preventDefault();
    void enviar(() => api.post<Mensagem>('/eliminacao/cortes', {
      rodadaId: Number(rodada), classificados: Number(classificados),
    }), true);
  };

  return (
    <Cartao titulo="Eliminação de participantes"
      descricao="Como os times na copa: ao fim de cada fase, só os mais bem pontuados seguem. Quem é eliminado sai do ranking.">
      {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
      {!dados && carregando && <Carregando linhas={3} />}
      {dados && <fieldset disabled={enviando} className="space-y-5 min-w-0">
        <Switch label="Ativar eliminação de participantes" checked={dados.eliminacaoParticipantes}
          onChange={valor => void enviar(() => api.put<Mensagem>('/eliminacao', { eliminacaoParticipantes: valor }))} />
        <p className="text-xs text-gray-500 dark:text-gray-400">O corte só vale quando todos os jogos até essa rodada têm resultado. Os cortes seguintes devem ter menos classificados.</p>
        {!dados.eliminacaoParticipantes && <p className="text-sm text-gray-500">Eliminação desligada. Os cortes ficam salvos e não retiram ninguém do ranking.</p>}
        <ul className="space-y-2">
          {dados.cortes.map(corte => <li key={corte.id} className="flex items-center justify-between gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
            <span className="text-sm text-gray-700 dark:text-gray-300">Após {corte.rodadaNome}: seguem {corte.classificados} participantes</span>
            <button type="button" aria-label={`Remover corte após ${corte.rodadaNome}`}
              onClick={() => void enviar(() => api.delete<Mensagem>(`/eliminacao/cortes/${corte.id}`))}
              className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20">
              <Trash2 className="w-4 h-4" />
            </button>
          </li>)}
        </ul>
        {!dados.cortes.length && <p className="text-sm text-gray-500">Nenhum corte configurado.</p>}
        <form onSubmit={adicionar} className="space-y-3">
          <Select label="Após a rodada" required value={rodada} onChange={e => setRodada(e.target.value)}>
            <option value="">Selecione uma rodada</option>
            {dados.rodadas.filter(r => !dados.cortes.some(c => c.rodadaId === r.id)).map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </Select>
          <Input label="Participantes que seguem" type="number" min={1} max={2147483647} step={1} required
            value={classificados} onChange={e => setClassificados(e.target.value)} />
          <button type="submit" disabled={enviando || !rodada || !classificados}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm disabled:opacity-60">
            <Plus className="w-4 h-4" /> Adicionar corte
          </button>
        </form>
      </fieldset>}
    </Cartao>
  );
}
