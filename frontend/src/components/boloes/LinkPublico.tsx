import { useEffect, useState } from 'react';
import { Check, Copy, Eye, EyeOff, Globe, Link2, Lock, RefreshCw, Trophy, Unlock } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { PublicoConfigApi } from '@/types';

type Resposta = PublicoConfigApi & { mensagem: string };

/** Aba "Link público" do bolão: link de consulta sem login e liberação da classificação por rodada. */
export function LinkPublico({ bolaoId }: { bolaoId: number }) {
  const showToast = useToast();
  const { dados, erro, recarregar } = useRecurso<PublicoConfigApi>(`/boloes/${bolaoId}/publico`);
  const [config, setConfig] = useState<PublicoConfigApi | null>(null);
  const [escolha, setEscolha] = useState('');
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [confirmar, setConfirmar] = useState<'regenerar' | 'desativar' | null>(null);

  useEffect(() => { if (dados) setConfig(dados); }, [dados]);
  useEffect(() => { setEscolha(config?.rodadaLiberada ? String(config.rodadaLiberada.id) : ''); }, [config?.rodadaLiberada?.id]);

  const executar = async (nome: string, acao: () => Promise<Resposta>) => {
    setOcupado(nome);
    try {
      const r = await acao();
      setConfig(r);
      showToast(r.mensagem);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
      throw e;
    } finally { setOcupado(null); }
  };
  const link = (acao: 'gerar' | 'desativar') => executar(acao, () => api.post<Resposta>(`/boloes/${bolaoId}/publico/link`, { acao }));
  const tabela = (rodadaId: number | null) => executar('tabela', () => api.put<Resposta>(`/boloes/${bolaoId}/publico/tabela`, { rodadaId }))
    .catch(() => undefined);

  const copiar = async () => {
    if (!config?.link) return;
    try {
      await navigator.clipboard.writeText(config.link);
      setCopiado(true); showToast('Link copiado. Cole no grupo do WhatsApp.');
      setTimeout(() => setCopiado(false), 2000);
    } catch { showToast('Não foi possível copiar. Selecione o link e copie manualmente.', 'error'); }
  };

  if (erro && !config) return <ErroCarga mensagem={erro} onTentar={recarregar} />;
  if (!config) return <Carregando linhas={2} />;

  const comResultado = config.rodadas.filter(r => r.comResultado > 0);
  const liberada = config.rodadaLiberada;
  const mudou = escolha !== (liberada ? String(liberada.id) : '');
  const sugestao = config.sugerida && config.sugerida.id !== liberada?.id ? config.sugerida : null;
  const card = 'bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-5 space-y-4';
  const botaoSec = 'inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60';
  const spinner = <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />;

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Link */}
      <section className={card} aria-labelledby="titulo-link">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center shrink-0"><Globe className="w-5 h-5 text-brand-600" /></div>
          <div className="min-w-0">
            <h3 id="titulo-link" className="font-bold text-gray-900 dark:text-white">Link de consulta</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Os participantes abrem sem login e só conseguem ver. Palpites aparecem apenas dos jogos com resultado lançado; ninguém vê quem falta palpitar.</p>
          </div>
        </div>

        {config.link ? (
          <>
            <div className="flex flex-col sm:flex-row gap-2">
              <input readOnly value={config.link} onFocus={e => e.currentTarget.select()} aria-label="Link público"
                className="flex-1 min-w-0 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-200 font-mono" />
              <div className="flex gap-2">
                <button onClick={copiar} className="flex-1 sm:flex-none button-primary">
                  {copiado ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copiado ? 'Copiado' : 'Copiar'}
                </button>
                <a href={config.link} target="_blank" rel="noopener noreferrer" className={`flex-1 sm:flex-none ${botaoSec}`}>
                  <Eye className="w-4 h-4" /> Ver como participante
                </a>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <button onClick={() => setConfirmar('regenerar')} disabled={!!ocupado} className={botaoSec}><RefreshCw className="w-4 h-4" /> Gerar novo link</button>
              <button onClick={() => setConfirmar('desativar')} disabled={!!ocupado} className={`${botaoSec} text-red-600 dark:text-red-400`}><Lock className="w-4 h-4" /> Desativar</button>
            </div>
          </>
        ) : (
          <button onClick={() => link('gerar').catch(() => undefined)} disabled={!!ocupado} className="button-primary disabled:opacity-60">
            {ocupado === 'gerar' ? spinner : <Link2 className="w-4 h-4" />} Criar link público
          </button>
        )}
      </section>

      {/* Classificação */}
      <section className={card} aria-labelledby="titulo-tabela">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-50 dark:bg-gold-900/20 flex items-center justify-center shrink-0"><Trophy className="w-5 h-5 text-gold-600" /></div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 id="titulo-tabela" className="font-bold text-gray-900 dark:text-white">Classificação para o público</h3>
              {liberada
                ? <Badge color="green" icon={<Unlock className="w-3 h-3" />}>Liberada até a {liberada.nome}</Badge>
                : <Badge color="gray" icon={<EyeOff className="w-3 h-3" />}>Oculta</Badge>}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              O público vê a tabela e os pontos (geral e por rodada) até a rodada escolhida. Rodadas seguintes mostram palpites e placares, mas sem pontos.
            </p>
          </div>
        </div>

        {sugestao && (
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-xl bg-brand-50 dark:bg-brand-900/20 border border-brand-100 dark:border-brand-900/40 p-3">
            <p className="text-sm text-brand-800 dark:text-brand-200 flex-1">A <strong>{sugestao.nome}</strong> é a última rodada com todos os resultados lançados.</p>
            <button onClick={() => tabela(sugestao.id)} disabled={!!ocupado} className="button-primary disabled:opacity-60 shrink-0">
              {ocupado === 'tabela' ? spinner : <Unlock className="w-4 h-4" />} Liberar até a {sugestao.nome}
            </button>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-2 sm:items-end">
          <label className="flex-1 min-w-0">
            <span className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Mostrar ao público até</span>
            <select value={escolha} onChange={e => setEscolha(e.target.value)} disabled={!!ocupado}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40">
              <option value="">Ninguém vê a classificação (oculta)</option>
              {comResultado.map(r => (
                <option key={r.id} value={r.id}>{r.nome} · {r.completa ? 'todos os resultados' : `${r.comResultado} de ${r.jogos} resultados`}</option>
              ))}
            </select>
          </label>
          <button onClick={() => tabela(escolha ? Number(escolha) : null)} disabled={!mudou || !!ocupado} className={`${botaoSec} sm:w-auto`}>
            {ocupado === 'tabela' ? spinner : <Check className="w-4 h-4" />} Aplicar
          </button>
        </div>
        {!config.link && <p className="text-xs text-gray-400">Crie o link acima para o público poder ver.</p>}
      </section>

      <ConfirmDialog open={confirmar === 'regenerar'} onClose={() => setConfirmar(null)} onConfirm={() => link('gerar')}
        title="Gerar um novo link?" confirmLabel="Gerar novo link"
        message="O link atual para de funcionar na hora. Envie o novo link para o grupo depois." />
      <ConfirmDialog open={confirmar === 'desativar'} onClose={() => setConfirmar(null)} onConfirm={() => link('desativar')}
        title="Desativar o link público?" confirmLabel="Desativar" danger
        message="Ninguém mais consegue abrir a página pública. Você pode criar um novo link quando quiser." />
    </div>
  );
}
