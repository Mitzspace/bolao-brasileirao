import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Input, Select, Switch } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { DICA_FASE_INICIAL, FASES_INICIAIS } from '@/lib/fases';
import type { FonteApi } from '@/types';

type Acao = 'jogos' | 'informacoes' | 'resultados';

const ACOES: { id: Acao; label: string; desc: string }[] = [
  { id: 'jogos', label: 'Importar jogos', desc: 'Cria e atualiza os jogos (de uma rodada ou do campeonato inteiro) e grava os placares já encerrados.' },
  { id: 'informacoes', label: 'Atualizar horários e resultados', desc: 'Só os jogos já cadastrados: corrige horários e grava os placares encerrados. Não cria jogos.' },
  { id: 'resultados', label: 'Sincronizar resultados', desc: 'Grava os placares encerrados dos jogos que vieram da API.' },
];

const ROTULO_FONTE: Record<FonteApi, string> = {
  'football-data': 'football-data.org',
  'api-football': 'API-Football',
  espn: 'ESPN',
};

/** Ferramentas da API do campeonato (só para o administrador geral). */
export function SincronizarApi({ aberto, onClose, codigoApi, ano, fonteApi = 'football-data', onConcluido }: {
  aberto: boolean; onClose: () => void; codigoApi: string; ano: number | null;
  fonteApi?: FonteApi; onConcluido: () => void;
}) {
  const apiFootball = fonteApi === 'api-football';
  const espn = fonteApi === 'espn';
  const temporadaInteira = apiFootball || espn;
  const showToast = useToast();
  const [acao, setAcao] = useState<Acao>('jogos');
  const [form, setForm] = useState({ completo: temporadaInteira, rodadaApi: '', nomeRodada: '', faseInicial: '', token: '', competicao: '', temporada: '' });
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState('');

  const enviar = async () => {
    setEnviando(true); setResultado('');
    try {
      const r = await api.post<{ mensagem: string }>('/campeonato/sincronizar', {
        acao, ...(!espn ? { token: form.token.trim() } : {}),
        competicao: espn ? form.competicao.trim().toLowerCase() : form.competicao.trim().toUpperCase(), temporada: form.temporada,
        campeonatoCompleto: form.completo, rodadaApi: form.rodadaApi, nomeRodada: form.nomeRodada,
        ...(espn && acao === 'jogos' && form.completo && form.faseInicial ? { faseInicial: form.faseInicial } : {}),
      });
      setResultado(r.mensagem); showToast(r.mensagem); onConcluido();
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível sincronizar.', 'error');
    } finally { setEnviando(false); }
  };

  return (
    <Modal open={aberto} onClose={onClose} title="Sincronizar com a API" size="md"
      footer={<>
        <button onClick={onClose} className="px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800">Fechar</button>
        <button onClick={enviar} disabled={enviando} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium disabled:opacity-60">
          <RefreshCw className={`w-4 h-4 ${enviando ? 'animate-spin' : ''}`} /> {enviando ? 'Sincronizando…' : 'Sincronizar'}
        </button>
      </>}>
      <div className="space-y-4">
        <div className="space-y-2" role="radiogroup" aria-label="O que sincronizar">
          {ACOES.map(a => (
            <label key={a.id} className={`flex gap-3 p-3 rounded-xl border-2 cursor-pointer transition-colors ${acao === a.id ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'}`}>
              <input type="radio" name="acao" checked={acao === a.id} onChange={() => setAcao(a.id)} className="mt-1 accent-brand-600" />
              <span><span className="block text-sm font-medium text-gray-900 dark:text-white">{a.label}</span>
                <span className="block text-xs text-gray-400">{a.desc}</span></span>
            </label>
          ))}
        </div>

        {acao === 'jogos' && (
          <div className="space-y-3">
            <Switch checked={form.completo} onChange={v => setForm({ ...form, completo: v })} label="Campeonato completo"
              description={temporadaInteira ? 'Importa os jogos disponíveis da temporada, organizados por rodadas e fases (1ª fase, oitavas de final…).' : 'Todas as rodadas de uma vez, com o nome da API (Rodada 1, Rodada 2…)'} />
            {espn && form.completo && (
              <div className="space-y-1">
                <Select label="Importar a partir de" value={form.faseInicial} onChange={e => setForm({ ...form, faseInicial: e.target.value })}>
                  {FASES_INICIAIS.map(f => <option key={f.valor} value={f.valor}>{f.rotulo}</option>)}
                </Select>
                <p className="text-xs text-gray-400">{DICA_FASE_INICIAL}</p>
              </div>
            )}
            {!form.completo && (
              <div className="grid grid-cols-2 gap-3">
                <Input label={temporadaInteira ? 'Número da rodada' : 'Rodada na API'} inputMode="numeric" placeholder={temporadaInteira ? 'Ex.: 10' : 'Ex.: 31'} value={form.rodadaApi} onChange={e => setForm({ ...form, rodadaApi: e.target.value.replace(/\D/g, '') })} />
                <Input label="Nome da rodada (opcional)" placeholder="Ex.: 31ª Rodada" maxLength={100} value={form.nomeRodada} onChange={e => setForm({ ...form, nomeRodada: e.target.value })} />
              </div>
            )}
          </div>
        )}
        {acao === 'resultados' && (
          <Input label={temporadaInteira ? "Número da rodada (opcional)" : "Rodada na API (opcional)"} inputMode="numeric" placeholder="Todas" value={form.rodadaApi} onChange={e => setForm({ ...form, rodadaApi: e.target.value.replace(/\D/g, '') })} />
        )}

        <p className="text-xs text-gray-400">
          Fonte: <strong>{ROTULO_FONTE[fonteApi]}</strong>
          {apiFootball ? ', com a chave do servidor. O plano gratuito tem 100 consultas por dia e restrições de temporadas.'
            : espn ? ' (sem token ou chave; API pública não oficial). A disponibilidade dos jogos depende da competição e da temporada.' : '.'}
        </p>
        {espn && <p className="text-xs text-gray-400">Quando a ESPN não informar o número da rodada, os jogos ficam agrupados pela fase. O número usado aqui é o da rodada cadastrada no bolão.</p>}
        <details className="rounded-xl border border-gray-100 dark:border-gray-800 px-4 py-2">
          <summary className="text-sm font-medium text-gray-600 dark:text-gray-300 cursor-pointer">Opções avançadas</summary>
          <div className="grid sm:grid-cols-3 gap-3 py-3">
            <Input label={apiFootball ? 'ID da liga' : espn ? 'Slug da liga' : 'Competição'}
              placeholder={codigoApi || (apiFootball ? '13' : espn ? 'conmebol.libertadores' : 'BSA')}
              maxLength={40} value={form.competicao}
              onChange={e => setForm({ ...form, competicao: espn ? e.target.value.toLowerCase() : e.target.value.toUpperCase() })} />
            <Input label="Temporada" placeholder={ano ? String(ano) : 'Atual'} inputMode="numeric" value={form.temporada} onChange={e => setForm({ ...form, temporada: e.target.value.replace(/\D/g, '') })} />
            {!espn && (
              <Select label={apiFootball ? 'Chave' : 'Token'} value={form.token ? 'outro' : ''} onChange={e => setForm({ ...form, token: e.target.value ? ' ' : '' })}>
                <option value="">Do servidor</option><option value="outro">Informar outro</option>
              </Select>
            )}
            {!espn && form.token !== '' && (
              <div className="sm:col-span-3"><Input label={apiFootball ? 'Chave da API-Football' : 'Token da API'} type="password" autoComplete="off" value={form.token.trim()} onChange={e => setForm({ ...form, token: e.target.value || ' ' })} /></div>
            )}
          </div>
        </details>
        {resultado && <p role="status" className="text-sm text-brand-700 dark:text-brand-300">{resultado}</p>}
      </div>
    </Modal>
  );
}
