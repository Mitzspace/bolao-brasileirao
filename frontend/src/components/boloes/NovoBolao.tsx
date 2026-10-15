import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Input, Select } from '@/components/ui/Form';
import { Avatar } from '@/components/ui/Avatar';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { FontesBolaoApi } from '@/types';

const ETAPAS = ['Dados do bolão', 'Campeonato', 'Participantes'];
const vazio = () => ({ nome: '', campeonato: '', ano: String(new Date().getFullYear()), codigoApi: 'BSA', origemId: '', marcados: [] as number[] });

/** Assistente do Bolt adaptado à criação real: nome, campeonato próprio e cópia opcional de nomes. */
export function NovoBolao({ aberto, onClose }: { aberto: boolean; onClose: () => void }) {
  const showToast = useToast();
  const [etapa, setEtapa] = useState(0);
  const [form, setForm] = useState(vazio);
  const [fontes, setFontes] = useState<FontesBolaoApi | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!aberto) return;
    const caminho = form.origemId ? `/boloes/fontes?origem_id=${form.origemId}` : '/boloes/fontes';
    api.get<FontesBolaoApi>(caminho).then(setFontes).catch(e => setErro(e instanceof Error ? e.message : 'Erro ao carregar bolões.'));
  }, [aberto, form.origemId]);

  const fechar = () => { onClose(); setEtapa(0); setForm(vazio()); setErro(''); };
  const nomeOk = form.nome.trim().length >= 2 && form.nome.trim().length <= 100;
  const campeonatoOk = !!form.campeonato.trim() && /^\d{1,4}$/.test(form.ano) && Number(form.ano) >= 1;
  const pessoas = form.origemId ? fontes?.pessoas ?? [] : [];
  const todos = pessoas.length > 0 && pessoas.every(p => form.marcados.includes(p.id));

  const criar = async () => {
    setSalvando(true); setErro('');
    try {
      await api.post('/boloes', {
        nome: form.nome, campeonato: form.campeonato, ano: form.ano, codigoApi: form.codigoApi,
        origemId: form.origemId ? Number(form.origemId) : null, participacaoIds: form.marcados,
      });
      // Abre a interface já no bolão novo, na aba Participantes (como a tela atual).
      window.location.hash = 'participantes';
      window.location.reload();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Não foi possível criar o bolão.';
      setErro(msg); showToast(msg, 'error'); setSalvando(false);
    }
  };

  const podeAvancar = etapa === 0 ? nomeOk : campeonatoOk;

  return (
    <Modal open={aberto} onClose={fechar} title="Novo bolão" size="lg"
      footer={<>
        {etapa > 0 && <button onClick={() => setEtapa(etapa - 1)} className="px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Voltar</button>}
        {etapa < ETAPAS.length - 1 ? (
          <button onClick={() => setEtapa(etapa + 1)} disabled={!podeAvancar} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-50">Avançar</button>
        ) : (
          <button onClick={criar} disabled={salvando || !nomeOk || !campeonatoOk} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-60">
            <Check className="w-4 h-4" /> {salvando ? 'Criando…' : 'Criar bolão'}
          </button>
        )}
      </>}>
      <div className="flex items-center gap-2 mb-6">
        {ETAPAS.map((s, i) => (
          <div key={s} className="flex items-center gap-2 flex-1">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${i <= etapa ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}`}>
              {i < etapa ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            {i < ETAPAS.length - 1 && <div className={`h-0.5 flex-1 rounded ${i < etapa ? 'bg-brand-600' : 'bg-gray-100 dark:bg-gray-800'}`} />}
          </div>
        ))}
      </div>
      <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">{ETAPAS[etapa]}</p>
      {erro && <p role="alert" className="mb-4 text-sm text-red-600">{erro}</p>}

      {etapa === 0 && (
        <div className="space-y-4">
          <Input label="Nome do bolão" value={form.nome} maxLength={100} autoFocus onChange={e => setForm({ ...form, nome: e.target.value })} placeholder="Ex.: Bolão da Galera"
            hint="Entre 2 e 100 caracteres. Você entra como responsável." />
        </div>
      )}

      {etapa === 1 && (
        <div className="space-y-4">
          <Input label="Campeonato deste bolão" value={form.campeonato} maxLength={100} onChange={e => setForm({ ...form, campeonato: e.target.value })} placeholder="Ex.: Brasileirão Série A" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Temporada" type="number" min={1} max={9999} value={form.ano} onChange={e => setForm({ ...form, ano: e.target.value })} />
            <Input label="Código na API (opcional)" value={form.codigoApi} maxLength={20} onChange={e => setForm({ ...form, codigoApi: e.target.value.toUpperCase() })} hint="BSA = Brasileirão" />
          </div>
          <p className="text-xs text-gray-400">Rodadas e jogos são cadastrados depois, em Configurações › Campeonatos.</p>
        </div>
      )}

      {etapa === 2 && (
        <div className="space-y-3">
          <Select label="Copiar nomes de outro bolão (opcional)" value={form.origemId} onChange={e => setForm({ ...form, origemId: e.target.value, marcados: [] })}>
            <option value="">Começar sem copiar participantes</option>
            {fontes?.fontes.map(b => <option key={b.id} value={b.id}>{b.nome} · {b.campeonato} {b.ano ?? ''}</option>)}
          </Select>
          {form.origemId && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-400">Cada nome vira um participante ativo, sem conta, palpites ou pontos copiados.</p>
                {pessoas.length > 0 && (
                  <button onClick={() => setForm({ ...form, marcados: todos ? [] : pessoas.map(p => p.id) })} className="text-xs font-semibold text-brand-700 dark:text-brand-300 shrink-0 ml-3">
                    {todos ? 'Desmarcar todos' : 'Marcar todos'}
                  </button>
                )}
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto scrollbar-thin">
                {pessoas.map(p => {
                  const marcado = form.marcados.includes(p.id);
                  return (
                    <label key={p.id} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${marcado ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'}`}>
                      <input type="checkbox" checked={marcado} className="w-4 h-4 rounded accent-brand-600"
                        onChange={e => setForm({ ...form, marcados: e.target.checked ? [...form.marcados, p.id] : form.marcados.filter(id => id !== p.id) })} />
                      <Avatar nome={p.nome} id={p.id} />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 flex-1 min-w-0 truncate">{p.nome}</span>
                      {p.status !== 'ativo' && <span className="text-xs text-gray-400">{p.status}</span>}
                    </label>
                  );
                })}
                {fontes && pessoas.length === 0 && <p className="text-sm text-gray-400">Não há outros participantes para copiar.</p>}
              </div>
              {form.marcados.length > 0 && <p className="text-sm text-brand-700 dark:text-brand-300 font-medium">{form.marcados.length} {form.marcados.length === 1 ? 'participante selecionado' : 'participantes selecionados'}</p>}
            </>
          )}
        </div>
      )}
    </Modal>
  );
}
