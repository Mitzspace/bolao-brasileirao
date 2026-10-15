import { useEffect, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Select, Textarea } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { AcaoDesistencia, PalpiteGuardado, ParticipanteApi, ParticipantesApi, PreviaDesistencia } from '@/types';

const TITULOS: Record<AcaoDesistencia, string> = {
  registrar: 'Registrar desistência', corrigir: 'Editar desistência',
  reativar: 'Reativar participante', restaurar: 'Restaurar palpites guardados',
};
const botaoSecundario = 'px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';
const botaoPrimario = 'px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-60';

function ListaPalpites({ itens, situacao }: { itens: PalpiteGuardado[]; situacao?: boolean }) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-800 divide-y divide-gray-50 dark:divide-gray-800 max-h-56 overflow-y-auto scrollbar-thin">
      {itens.map(p => (
        <div key={p.id} className="flex items-center gap-3 px-3 py-2 text-sm">
          <span className="text-xs text-gray-400 w-20 shrink-0">{p.rodada}</span>
          <span className="flex-1 min-w-0 truncate text-gray-700 dark:text-gray-300">{p.jogo}</span>
          <span className="font-semibold text-gray-900 dark:text-white">{p.palpite}</span>
          {situacao && <span className="text-[11px] text-gray-400 hidden sm:inline">{p.jaGuardado ? 'Já guardado' : 'Será guardado'}</span>}
        </div>
      ))}
    </div>
  );
}

/** Mesmo fluxo da tela atual: escolher → revisar a prévia (nada gravado) → confirmar. */
export function DesistenciaModal({ pessoa, acao, dados, onClose, onConcluido }: {
  pessoa: ParticipanteApi | null; acao: AcaoDesistencia; dados: ParticipantesApi; onClose: () => void; onConcluido: (logout: boolean) => void;
}) {
  const showToast = useToast();
  const [rodadaId, setRodadaId] = useState('');
  const [motivo, setMotivo] = useState('');
  const [previa, setPrevia] = useState<PreviaDesistencia | null>(null);
  const [restaurar, setRestaurar] = useState<'' | 'sim' | 'nao'>('');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!pessoa) return;
    setRodadaId(String(pessoa.rodadaDesistencia?.id ?? dados.rodadaPadraoId ?? ''));
    setMotivo(pessoa.motivoDesistencia);
    setPrevia(null); setRestaurar(''); setErro('');
  }, [pessoa, acao, dados.rodadaPadraoId]);

  const pedeRodada = acao === 'registrar' || acao === 'corrigir';
  const corpo = () => ({ acao, rodadaId: pedeRodada && rodadaId ? Number(rodadaId) : null, motivo: pedeRodada ? motivo : '' });

  const revisar = async () => {
    if (!pessoa) return;
    setOcupado(true); setErro('');
    try { setPrevia(await api.post<PreviaDesistencia>(`/participantes/${pessoa.id}/desistencia`, corpo())); }
    catch (e) { setErro(e instanceof Error ? e.message : 'Não foi possível gerar a prévia.'); }
    finally { setOcupado(false); }
  };

  const confirmar = async () => {
    if (!pessoa || !previa) return;
    setOcupado(true); setErro('');
    try {
      const r = await api.post<{ mensagem: string; logout: boolean }>(`/participantes/${pessoa.id}/desistencia`,
        { ...corpo(), confirmar: true, token: previa.token, restaurar: restaurar || undefined });
      showToast(r.mensagem);
      onConcluido(r.logout);
      onClose();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível confirmar.');
      setPrevia(null); // dados mudaram: volta para revisar de novo
    } finally { setOcupado(false); }
  };

  const p = previa?.previa;
  return (
    <Modal open={!!pessoa} onClose={ocupado ? () => undefined : onClose} title={`${TITULOS[acao]} · ${pessoa?.nome ?? ''}`} size="lg"
      footer={<>
        <button onClick={previa ? () => setPrevia(null) : onClose} disabled={ocupado} className={botaoSecundario}>{previa ? 'Voltar sem salvar' : 'Cancelar'}</button>
        {previa
          ? <button onClick={confirmar} disabled={ocupado || (!!p?.restauraveis.length && !restaurar)} className={botaoPrimario}>{ocupado ? 'Confirmando…' : 'Confirmar alteração'}</button>
          : <button onClick={revisar} disabled={ocupado || (pedeRodada && !rodadaId)} className={botaoPrimario}>{ocupado ? 'Gerando prévia…' : 'Revisar alteração'}</button>}
      </>}>
      <div className="space-y-4">
        {erro && <p role="alert" className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-sm text-red-700 dark:text-red-300">{erro}</p>}
        {!previa && (
          <>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              <strong className="text-gray-700 dark:text-gray-200">{dados.regraDesistencia}.</strong> As rodadas anteriores continuam valendo; a partir da desistência,
              a pessoa sai do lançamento, das pendências e do ranking da rodada. O ranking geral mantém os pontos anteriores.
            </p>
            {pedeRodada ? (
              <>
                <Select label={dados.regraDesistencia} value={rodadaId} onChange={e => setRodadaId(e.target.value)}>
                  <option value="">Selecione a rodada</option>
                  {dados.rodadas.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
                </Select>
                <Textarea label="Motivo ou observação (opcional)" rows={3} value={motivo} onChange={e => setMotivo(e.target.value)} />
                <p className="text-xs text-gray-400">Data e responsável pelo registro são preenchidos automaticamente na confirmação.</p>
              </>
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-300">Vamos mostrar os palpites guardados antes de confirmar. Você escolhe se esse lote volta a valer.</p>
            )}
          </>
        )}
        {p && (
          <>
            <div className="p-3 rounded-xl bg-gold-50 dark:bg-gold-900/20 text-sm text-gold-800 dark:text-gold-200">
              Nenhuma alteração foi gravada. {p.acao === 'reativar' ? 'A participação será reativada.' : p.rodada && pedeRodada ? `Desistência a partir de ${p.rodada}.` : 'Revise os palpites que podem voltar a valer.'}
              {p.motivo && <span className="block mt-1"><strong>Motivo:</strong> {p.motivo}</span>}
            </div>
            {p.posteriores.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-semibold text-gold-700 dark:text-gold-300">{p.posteriores.length} palpite(s) a partir da desistência serão guardados como “após desistência”, fora da pontuação.</p>
                <ListaPalpites itens={p.posteriores} situacao />
              </div>
            )}
            {p.restauraveis.length > 0 && (
              <fieldset className="space-y-2">
                <legend className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Palpites que podem voltar a valer</legend>
                <ListaPalpites itens={p.restauraveis} />
                <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300 pt-2">
                  <input type="radio" name="restaurar" checked={restaurar === 'sim'} onChange={() => setRestaurar('sim')} className="mt-1 accent-brand-600" />
                  Confirmo que estes palpites devem voltar a valer, conforme os resultados oficiais.
                </label>
                <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="radio" name="restaurar" checked={restaurar === 'nao'} onChange={() => setRestaurar('nao')} className="mt-1 accent-brand-600" />
                  Manter guardados e fora da pontuação por enquanto.
                </label>
              </fieldset>
            )}
            {p.acao === 'reativar' && <p className="text-xs text-gray-400">Reativar a participação não concede acesso de responsável. Esse acesso é administrado em Configurações.</p>}
            {p.acao === 'restaurar' && !p.restauraveis.length && <p className="text-sm text-gray-500">Não há palpites guardados que possam voltar a valer.</p>}
          </>
        )}
      </div>
    </Modal>
  );
}
