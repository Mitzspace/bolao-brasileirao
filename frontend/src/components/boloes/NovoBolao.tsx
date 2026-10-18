import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Input, Select } from '@/components/ui/Form';
import { Avatar } from '@/components/ui/Avatar';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { REGRAS_PADRAO, type FontesBolaoApi, type FonteApi } from '@/types';
import { normalizarCodigoApi } from '@/lib/codigoApi';
import { DICA_FASE_INICIAL, FASES_INICIAIS } from '@/lib/fases';
import { EditorRegras, paraEdicao, validarRegras } from './EditorRegras';

const AVISO_API_FOOTBALL = 'O plano gratuito da API-Football tem restrições de temporadas. Confirme o acesso ao ano desejado; ele pode exigir plano pago.';

const ETAPAS = ['Dados do bolão', 'Campeonato', 'Regras', 'Participantes'];
const vazio = () => ({ nome: '', modelo: '', campeonato: '', ano: String(new Date().getFullYear()), codigoApi: '', fonteApi: 'football-data' as FonteApi, eliminacao: false, faseInicial: '', origemId: '', marcados: [] as number[], regras: paraEdicao(REGRAS_PADRAO) });

/** Assistente do Bolt adaptado à criação real: nome, campeonato próprio e cópia opcional de nomes. */
export function NovoBolao({ aberto, onClose }: { aberto: boolean; onClose: () => void }) {
  const showToast = useToast();
  const [etapa, setEtapa] = useState(0);
  const [form, setForm] = useState(vazio);
  const [fontes, setFontes] = useState<FontesBolaoApi | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [verificando, setVerificando] = useState(false);

  useEffect(() => {
    if (!aberto) return;
    const caminho = form.origemId ? `/boloes/fontes?origem_id=${form.origemId}` : '/boloes/fontes';
    api.get<FontesBolaoApi>(caminho).then(setFontes).catch(e => setErro(e instanceof Error ? e.message : 'Erro ao carregar bolões.'));
  }, [aberto, form.origemId]);

  const fechar = () => { onClose(); setEtapa(0); setForm(vazio()); setErro(''); };
  const nomeOk = form.nome.trim().length >= 2 && form.nome.trim().length <= 100;
  const campeonatoOk = !!form.campeonato.trim() && /^\d{1,4}$/.test(form.ano) && Number(form.ano) >= 1;
  const pessoas = form.origemId ? fontes?.pessoas ?? [] : [];
  const regras = validarRegras(form.regras);
  const todos = pessoas.length > 0 && pessoas.every(p => form.marcados.includes(p.id));
  const modelos = fontes?.modelos ?? [];
  const aviso = form.fonteApi === 'api-football' ? AVISO_API_FOOTBALL
    : form.fonteApi === 'espn' ? 'ESPN: importação de jogos e resultados sem token ou chave. API pública não oficial; a disponibilidade depende da competição e da temporada.'
    : modelos.find(m => (m.fonte_api ?? 'football-data') === 'football-data' && m.codigo_api === normalizarCodigoApi('football-data', form.codigoApi))?.aviso;

  const escolherModelo = (chave: string) => {
    const modelo = modelos.find(m => m.chave === chave);
    setForm(atual => ({ ...atual, modelo: chave, campeonato: modelo?.nome ?? '',
      codigoApi: modelo?.codigo_api ?? '', fonteApi: modelo?.fonte_api ?? 'football-data', eliminacao: modelo?.eliminacao ?? false,
      faseInicial: modelo?.fase_inicial ?? '' }));
  };

  const criar = async () => {
    setSalvando(true); setErro('');
    try {
      await api.post('/boloes', {
        nome: form.nome, campeonato: form.campeonato, ano: form.ano, codigoApi: normalizarCodigoApi(form.fonteApi, form.codigoApi), fonte_api: form.fonteApi,
        modelo: form.modelo || undefined, eliminacao_participantes: form.eliminacao,
        faseInicial: form.fonteApi === 'espn' && form.faseInicial ? form.faseInicial : undefined,
        origemId: form.origemId ? Number(form.origemId) : null, participacaoIds: form.marcados, regras: regras.regras,
      });
      // Abre a interface já no bolão novo, na aba Participantes (como a tela atual).
      window.location.hash = 'participantes';
      window.location.reload();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Não foi possível criar o bolão.';
      setErro(msg); showToast(msg, 'error'); setSalvando(false);
    }
  };

  const avancar = async () => {
    if (etapa !== 1) { setEtapa(etapa + 1); return; }
    setVerificando(true); setErro('');
    try {
      await api.post('/boloes/verificar-temporada', {
        campeonato: form.campeonato, ano: form.ano, codigoApi: normalizarCodigoApi(form.fonteApi, form.codigoApi),
        fonte_api: form.fonteApi, modelo: form.modelo || undefined,
      });
      setEtapa(2);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível verificar a temporada.');
    } finally { setVerificando(false); }
  };

  const podeAvancar = etapa === 0 ? nomeOk : etapa === 1 ? campeonatoOk : !!regras.regras;

  return (
    <Modal open={aberto} onClose={fechar} title="Novo bolão" size="lg"
      footer={<>
        {etapa > 0 && <button onClick={() => { setErro(''); setEtapa(etapa - 1); }} className="px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Voltar</button>}
        {etapa < ETAPAS.length - 1 ? (
          <button onClick={avancar} disabled={!podeAvancar || verificando} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-50">{verificando ? 'Verificando temporada…' : 'Avançar'}</button>
        ) : (
          <button onClick={criar} disabled={salvando || !nomeOk || !campeonatoOk || !regras.regras} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-60">
            <Check className="w-4 h-4" /> {salvando ? 'Criando e importando jogos…' : 'Criar bolão'}
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
          <fieldset className="space-y-2">
            <legend className="text-sm font-semibold text-gray-700 dark:text-gray-300">Modelo de competição</legend>
            <p className="text-xs text-gray-400">Escolha um modelo para preencher o campeonato e o código da API. Você pode ajustar os campos depois.</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[...modelos, { chave: '', rotulo: 'Outro campeonato', descricao: 'Preencha nome, fonte e código manualmente.' }].map(modelo => (
                <label key={modelo.chave} className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${form.modelo === modelo.chave ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'}`}>
                  <input type="radio" name="modelo" value={modelo.chave} checked={form.modelo === modelo.chave}
                    onChange={() => escolherModelo(modelo.chave)} className="w-4 h-4 mt-0.5 accent-brand-600 shrink-0" />
                  <span>
                    <span className="block text-sm font-semibold text-gray-700 dark:text-gray-300">{modelo.rotulo}</span>
                    <span className="block text-xs text-gray-400">{modelo.descricao}</span>
                  </span>
                </label>
              ))}
            </div>
            {!fontes && !erro && <p role="status" className="text-xs text-gray-400">Carregando modelos…</p>}
          </fieldset>
          {!form.modelo && (
            <Select label="Fonte dos jogos e resultados" value={form.fonteApi} onChange={e => setForm({ ...form, fonteApi: e.target.value as FonteApi })}>
              <option value="football-data">football-data.org (código, ex.: BSA)</option>
              <option value="espn">ESPN (sem token ou chave)</option>
              <option value="api-football">API-Football (ID da liga, ex.: 13)</option>
            </Select>
          )}
          <Input label="Campeonato deste bolão" value={form.campeonato} maxLength={100} onChange={e => setForm({ ...form, campeonato: e.target.value })} placeholder="Ex.: Brasileirão Série A" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Temporada" type="number" min={1} max={9999} value={form.ano} onChange={e => setForm({ ...form, ano: e.target.value })} />
            <Input label={form.fonteApi === 'api-football' ? 'ID da liga na API (opcional)' : form.fonteApi === 'espn' ? 'Slug na ESPN (opcional)' : 'Código na API (opcional)'}
              value={form.codigoApi} maxLength={40}
              onChange={e => setForm({ ...form, codigoApi: normalizarCodigoApi(form.fonteApi, e.target.value) })}
              hint={form.fonteApi === 'espn' ? 'Libertadores: conmebol.libertadores; Sul-Americana: conmebol.sudamericana; Copa do Brasil: bra.copa_do_brazil; Mineiro: bra.camp.mineiro; Copa do Mundo: fifa.world.' : undefined} />
          </div>
          {form.fonteApi === 'espn' && (
            <div className="space-y-1">
              <Select label="Importar jogos a partir de" value={form.faseInicial} onChange={e => setForm({ ...form, faseInicial: e.target.value })}>
                {FASES_INICIAIS.map(f => <option key={f.valor} value={f.valor}>{f.rotulo}</option>)}
              </Select>
              <p className="text-xs text-gray-400">Para copas de mata-mata. {DICA_FASE_INICIAL}</p>
            </div>
          )}
          {aviso && <p role="status" className="rounded-xl border border-gold-200 dark:border-gold-800/50 bg-gold-50 dark:bg-gold-900/20 p-3 text-sm text-gold-800 dark:text-gold-200">{aviso}</p>}
          <label className="flex items-start gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800 cursor-pointer">
            <input type="checkbox" checked={form.eliminacao} onChange={e => setForm({ ...form, eliminacao: e.target.checked })}
              className="w-4 h-4 mt-0.5 rounded accent-brand-600 shrink-0" />
            <span>
              <span className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Eliminar participantes por fase</span>
              <span className="block text-xs text-gray-400">Como os times na copa: ao fim de cada fase, só os mais bem pontuados seguem no ranking. Os cortes são configurados depois.</span>
            </span>
          </label>
          <p className="text-xs text-gray-400">Depois de criar o bolão, cadastre rodadas e jogos em Configurações › Campeonatos. O administrador geral também pode importar jogos e sincronizar resultados pela fonte selecionada.</p>
        </div>
      )}

      {etapa === 2 && (
        <div className="space-y-3">
          <p className="text-xs text-gray-400">Já vêm com as regras atuais. Dá para mudar depois em Bolões › Ver classificação › Regras.</p>
          <EditorRegras valores={form.regras} onChange={v => setForm({ ...form, regras: v })} />
          {regras.erro && <p role="alert" className="text-sm text-red-600">{regras.erro}</p>}
        </div>
      )}

      {etapa === 3 && (
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
