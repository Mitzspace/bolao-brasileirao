import { useEffect, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Select, Switch, Textarea } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { api, ApiError } from '@/lib/api';
import type { ParticipanteApi, ParticipantesApi } from '@/types';

interface Props {
  aberto: boolean;
  /** null = novo participante. */
  pessoa: ParticipanteApi | null;
  dados: ParticipantesApi;
  onClose: () => void;
  onSalvo: () => void;
}

const botaoSecundario = 'px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';
const botaoPrimario = 'px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-60';

/** Cadastro e edição (mesmos campos da tela atual: sem telefone e sem pagamento). */
export function FormParticipante({ aberto, pessoa, dados, onClose, onSalvo }: Props) {
  const showToast = useToast();
  const [form, setForm] = useState({ nome: '', email: '', observacao: '', rodadaEntradaId: '', responsavel: false });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!aberto) return;
    setErros({});
    setForm(pessoa
      ? { nome: pessoa.nome, email: pessoa.email, observacao: pessoa.observacao, rodadaEntradaId: '', responsavel: pessoa.responsavel }
      : { nome: '', email: '', observacao: '', rodadaEntradaId: dados.rodadaPadraoId ? String(dados.rodadaPadraoId) : '', responsavel: false });
  }, [aberto, pessoa, dados.rodadaPadraoId]);

  const salvar = async () => {
    setSalvando(true);
    setErros({});
    try {
      const r = pessoa
        ? await api.put<{ mensagem: string }>(`/participantes/${pessoa.id}`, { nome: form.nome, email: form.email, observacao: form.observacao, responsavel: form.responsavel })
        : await api.post<{ mensagem: string }>('/participantes', { nome: form.nome, email: form.email, observacao: form.observacao, rodadaEntradaId: form.rodadaEntradaId ? Number(form.rodadaEntradaId) : null });
      showToast(r.mensagem);
      onSalvo();
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.dados.erros) setErros(e.dados.erros as Record<string, string>);
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    } finally { setSalvando(false); }
  };

  const regraEntrada = dados.politicaEntrada === 'fora_da_conta'
    ? 'Neste bolão, as rodadas anteriores à entrada ficam fora da conta.'
    : 'Neste bolão, as rodadas anteriores à entrada contam com zero pontos, sem palpites.';

  return (
    <Modal open={aberto} onClose={salvando ? () => undefined : onClose} title={pessoa ? 'Editar participante' : 'Novo participante'}
      footer={<>
        <button onClick={onClose} disabled={salvando} className={botaoSecundario}>Cancelar</button>
        <button onClick={salvar} disabled={salvando || form.nome.trim().length < 2} className={botaoPrimario}>{salvando ? 'Salvando…' : pessoa ? 'Salvar' : 'Adicionar'}</button>
      </>}>
      <div className="space-y-4">
        <Input label="Nome de exibição" value={form.nome} maxLength={100} onChange={e => setForm({ ...form, nome: e.target.value })}
          placeholder="Como aparece na classificação" error={erros.nome_exibicao} autoFocus />
        <Input label="E-mail de contato (opcional)" type="email" maxLength={100} value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
          placeholder="email@email.com" error={erros.email} hint={pessoa ? 'O e-mail de contato não altera a conta de acesso vinculada.' : undefined} />
        {!pessoa && (
          <div>
            <Select label="Primeira rodada em que participa" value={form.rodadaEntradaId} onChange={e => setForm({ ...form, rodadaEntradaId: e.target.value })}>
              <option value="">Selecione a rodada de entrada</option>
              {dados.rodadas.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
            </Select>
            <p className={`mt-1 text-xs ${erros.rodada_entrada_id ? 'text-red-500' : 'text-gray-400'}`}>{erros.rodada_entrada_id ?? regraEntrada}</p>
          </div>
        )}
        {pessoa && (
          <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
            <Switch checked={form.responsavel} onChange={v => setForm({ ...form, responsavel: v })} label="É responsável?"
              description={pessoa.temConta ? 'Responsáveis lançam palpites e administram o bolão.' : 'O acesso à gestão exige vincular uma conta em Configurações › Responsáveis.'} />
            {erros.responsavel && <p className="mt-2 text-xs text-red-500">{erros.responsavel}</p>}
          </div>
        )}
        <Textarea label="Observação (opcional)" rows={2} value={form.observacao} onChange={e => setForm({ ...form, observacao: e.target.value })} placeholder="Notas sobre o participante…" />
        {!pessoa && <p className="text-xs text-gray-400">A pessoa não precisa de conta de acesso. Nomes e e-mails repetidos não são permitidos neste bolão.</p>}
      </div>
    </Modal>
  );
}
