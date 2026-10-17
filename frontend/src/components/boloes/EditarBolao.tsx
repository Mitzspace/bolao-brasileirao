import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Input } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { useApp } from '@/context/AppContext';
import { api } from '@/lib/api';
import type { StatusBolao } from '@/types';

export const OPCOES_STATUS: { valor: StatusBolao; rotulo: string; descricao: string }[] = [
  { valor: 'ativo', rotulo: 'Em andamento', descricao: 'Bolão em uso: tudo pode ser alterado.' },
  { valor: 'finalizado', rotulo: 'Finalizado', descricao: 'Campeonato encerrado. Fica só para consulta.' },
  { valor: 'desistido', rotulo: 'Desistido', descricao: 'Bolão abandonado. Fica só para consulta.' },
];

const botaoSecundario = 'px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';
const botaoPrimario = 'px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-60';

interface Props {
  bolao: { id: number; nome: string; status: StatusBolao };
  aberto: boolean;
  onClose: () => void;
  /** Chamado depois de gravar (ex.: recarregar a classificação). */
  onSalvo?: () => void | Promise<unknown>;
}

/** Editar nome e situação do bolão (vale para todos os campeonatos do mesmo bolão). */
export function EditarBolao({ bolao, aberto, onClose, onSalvo }: Props) {
  const showToast = useToast();
  const { atualizarBoloes } = useApp();
  const [nome, setNome] = useState(bolao.nome);
  const [status, setStatus] = useState<StatusBolao>(bolao.status);
  const [salvando, setSalvando] = useState(false);
  const [confirmar, setConfirmar] = useState(false);

  useEffect(() => {
    if (aberto) { setNome(bolao.nome); setStatus(bolao.status); }
  }, [aberto, bolao.nome, bolao.status]);

  const nomeLimpo = nome.split(/\s+/).filter(Boolean).join(' ');
  const mudouNome = nomeLimpo !== bolao.nome;
  const mudouStatus = status !== bolao.status;
  // Enquanto finalizado/desistido nada pode ser alterado; o nome só muda se o bolão voltar a andamento.
  const nomeTravado = status !== 'ativo';
  const erroNome = !nomeLimpo ? 'Informe o nome do bolão.' : nomeLimpo.length > 100 ? 'No máximo 100 caracteres.' : '';
  const podeSalvar = !salvando && (nomeTravado ? mudouStatus : !erroNome && (mudouNome || mudouStatus));
  const precisaConfirmar = mudouStatus && status !== 'ativo';

  const salvar = async () => {
    setSalvando(true);
    try {
      const gravarNome = async () => {
        if (!mudouNome || nomeTravado) return;
        const r = await api.put<{ ids: number[]; nome: string }>(`/boloes/${bolao.id}`, { nome: nomeLimpo });
        atualizarBoloes(r.ids, { nome: r.nome });
      };
      const gravarStatus = async () => {
        if (!mudouStatus) return undefined;
        const r = await api.put<{ ids: number[]; mensagem: string }>(`/boloes/${bolao.id}/status`, { status });
        atualizarBoloes(r.ids, { status });
        return r.mensagem;
      };
      // Reativar libera a edição, então a situação vem primeiro; nos demais casos o nome vem antes de travar.
      let mensagem: string | undefined;
      if (status === 'ativo') { mensagem = await gravarStatus(); await gravarNome(); }
      else { await gravarNome(); mensagem = await gravarStatus(); }
      showToast(mensagem ?? 'Nome do bolão atualizado.');
      onClose();
      await onSalvo?.();
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
      throw e;
    } finally {
      setSalvando(false);
    }
  };

  return (
    <>
      <Modal open={aberto} onClose={onClose} title="Editar bolão"
        footer={<>
          <button onClick={onClose} className={botaoSecundario}>Cancelar</button>
          <button disabled={!podeSalvar} className={botaoPrimario}
            onClick={() => precisaConfirmar ? setConfirmar(true) : salvar().catch(() => undefined)}>
            <Check className="w-4 h-4" /> Salvar
          </button>
        </>}>
        <div className="space-y-5">
          <Input label="Nome do bolão" value={nome} maxLength={100} disabled={nomeTravado} error={nomeTravado ? undefined : erroNome}
            hint={nomeTravado ? 'Volte para "Em andamento" para renomear.' : 'Participantes, palpites e classificação não mudam.'}
            onChange={e => setNome(e.target.value)} />
          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Situação</legend>
            <div className="space-y-2" role="radiogroup">
              {OPCOES_STATUS.map(o => (
                <label key={o.valor} className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${status === o.valor ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-brand-300'}`}>
                  <input type="radio" name="situacao-bolao" value={o.valor} checked={status === o.valor} onChange={() => setStatus(o.valor)} className="mt-1 accent-brand-600" />
                  <span>
                    <span className="block text-sm font-semibold text-gray-900 dark:text-white">{o.rotulo}</span>
                    <span className="block text-xs text-gray-500 dark:text-gray-400">{o.descricao}</span>
                  </span>
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-400">Dá para desfazer a qualquer momento voltando para "Em andamento".</p>
          </fieldset>
        </div>
      </Modal>
      <ConfirmDialog open={confirmar} onClose={() => setConfirmar(false)} onConfirm={salvar}
        title={status === 'finalizado' ? 'Marcar como finalizado?' : 'Marcar como desistido?'} danger={status === 'desistido'}
        confirmLabel={status === 'finalizado' ? 'Marcar como finalizado' : 'Marcar como desistido'}
        message={<>Enquanto estiver {status === 'finalizado' ? 'finalizado' : 'desistido'}, <strong>nada neste bolão poderá ser alterado</strong> (jogos, resultados, palpites, participantes, regras). Você pode voltar para "Em andamento" a qualquer momento.</>} />
    </>
  );
}
