import { useMemo, useState } from 'react';
import { ClipboardPaste, MessageCircle, Wand2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { PreviaWhatsapp as Previa } from '@/types';

export interface LinhaAplicada { jogoId: number; casa: string; fora: string; primeiroGol: string }

interface Props {
  participacaoId: number;
  rodadaId: number;
  nome: string;
  rodadaNome: string;
  /** Preenche o formulário (nada é gravado) e informa o token assinado da mensagem. */
  onAplicar: (linhas: LinhaAplicada[], token: string) => void;
}

interface LinhaEditavel { usar: boolean; jogoId: string; casa: string; fora: string; primeiro: string; texto: string; avisos: string[] }

const campo = 'w-full px-2 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40';

/** Colar mensagem do WhatsApp → prévia revisável → preencher o formulário (mesma lógica da tela atual). */
export function PreviaWhatsapp({ participacaoId, rodadaId, nome, rodadaNome, onAplicar }: Props) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState('');
  const [status, setStatus] = useState('');
  const [lendo, setLendo] = useState(false);
  const [previa, setPrevia] = useState<Previa | null>(null);
  const [linhas, setLinhas] = useState<LinhaEditavel[]>([]);

  const gerar = async () => {
    setLendo(true); setPrevia(null); setStatus('Lendo mensagem…');
    try {
      const r = await api.post<Previa>('/palpites/previa-whatsapp', { participacaoId, rodadaId, texto });
      if (!r.reconhecido) {
        setStatus('Formato totalmente irreconhecível para esta rodada. Nenhum palpite foi preenchido. Corrija a mensagem ou lance manualmente.');
        return;
      }
      setPrevia(r);
      setLinhas(r.linhas.map(l => ({ usar: true, jogoId: l.jogo_id ? String(l.jogo_id) : '', casa: l.casa, fora: l.fora, primeiro: l.primeiro_gol || '', texto: l.texto, avisos: l.avisos })));
      setStatus('Prévia: confira jogos e placares. Nada foi gravado. Desmarque as linhas que deseja ignorar.');
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Não foi possível ler a mensagem.');
    } finally { setLendo(false); }
  };

  const validacao = useMemo(() => {
    if (!previa) return { linhas: [] as string[][], valido: false };
    const contagem: Record<string, number> = {};
    linhas.filter(l => l.usar && l.jogoId).forEach(l => { contagem[l.jogoId] = (contagem[l.jogoId] ?? 0) + 1; });
    let valido = linhas.some(l => l.usar);
    const alertas = linhas.map(l => {
      const jogo = previa.jogos.find(j => String(j.id) === l.jogoId);
      const lista = [...l.avisos, ...(jogo?.avisos ?? [])];
      const bonusInvalido = !!l.primeiro.trim() && (!jogo?.primeiro_gol_permitido || l.primeiro.length > 100 || l.primeiro.includes('★'));
      if (bonusInvalido) lista.push('Primeiro gol: confira o jogador e se o jogo está cadastrado como clássico.');
      const placarRuim = [l.casa, l.fora].some(v => !/^[0-9]{1,10}$/.test(v) || Number(v) > 2147483647);
      if (l.usar && (!jogo || jogo.bloqueado || bonusInvalido || contagem[l.jogoId] > 1 || placarRuim)) {
        valido = false;
        lista.push('PENDENTE: escolha jogo único e placar válido, ou desmarque esta linha.');
      }
      return lista;
    });
    return { linhas: alertas, valido };
  }, [linhas, previa]);

  const aplicar = () => {
    if (!previa || !validacao.valido) return;
    onAplicar(linhas.filter(l => l.usar).map(l => ({ jogoId: Number(l.jogoId), casa: l.casa, fora: l.fora, primeiroGol: l.primeiro.trim() })), previa.token);
    setStatus('Formulário preenchido. Nenhum palpite foi salvo. Revise os jogos abaixo e salve.');
    setPrevia(null);
  };

  const mudar = (i: number, parcial: Partial<LinhaEditavel>) => setLinhas(ls => ls.map((l, j) => j === i ? { ...l, ...parcial } : l));

  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm overflow-hidden">
      <button onClick={() => setAberto(v => !v)} aria-expanded={aberto}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
        <span className="w-9 h-9 rounded-xl bg-[#25D366]/15 text-[#128C7E] flex items-center justify-center"><MessageCircle className="w-5 h-5" /></span>
        <span className="flex-1">
          <span className="block font-semibold text-gray-900 dark:text-white text-sm">Colar mensagem do WhatsApp</span>
          <span className="block text-xs text-gray-400">Preenche os placares a partir do texto enviado pelo participante</span>
        </span>
        <ClipboardPaste className="w-4 h-4 text-gray-400" />
      </button>
      {aberto && (
        <div className="px-5 pb-5 space-y-3 border-t border-gray-100 dark:border-gray-800 pt-4 animate-fade-in">
          <p className="text-xs text-gray-500 dark:text-gray-400">Participante: <strong>{nome}</strong> · {rodadaNome}. A prévia não grava palpites.</p>
          <textarea value={texto} onChange={e => { setTexto(e.target.value); setPrevia(null); }} rows={5} maxLength={20000}
            placeholder={'Flamengo 2x1 Vasco ★ Pedro\nSantos 0x0 Bahia'} aria-label="Mensagem original"
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          <button onClick={gerar} disabled={lendo || !texto.trim()} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
            <Wand2 className="w-4 h-4" /> Gerar prévia
          </button>
          {status && <p role="status" className="text-sm text-gray-600 dark:text-gray-300">{status}</p>}
          {previa && (
            <>
              <div className="space-y-2">
                {linhas.map((l, i) => (
                  <div key={i} className={`rounded-xl border p-3 space-y-2 ${l.usar && validacao.linhas[i]?.some(a => a.startsWith('PENDENTE')) ? 'border-red-200 bg-red-50/60 dark:border-red-900/40 dark:bg-red-900/10' : 'border-gray-100 dark:border-gray-800'}`}>
                    <label className="flex items-start gap-2 text-sm">
                      <input type="checkbox" checked={l.usar} onChange={e => mudar(i, { usar: e.target.checked })} className="mt-1" aria-label={`Usar linha ${i + 1}`} />
                      <span className="font-mono text-xs text-gray-600 dark:text-gray-300 break-all">{l.texto}</span>
                    </label>
                    <div className="grid grid-cols-[1fr_3.5rem_3.5rem] sm:grid-cols-[1fr_3.5rem_3.5rem_10rem] gap-2">
                      <select value={l.jogoId} onChange={e => mudar(i, { jogoId: e.target.value })} className={campo} aria-label={`Jogo da linha ${i + 1}`}>
                        <option value="">Selecione o jogo</option>
                        {previa.jogos.map(j => <option key={j.id} value={j.id} disabled={j.bloqueado}>{j.nome}</option>)}
                      </select>
                      <input value={l.casa} onChange={e => mudar(i, { casa: e.target.value })} inputMode="numeric" className={`${campo} text-center`} aria-label={`Casa da linha ${i + 1}`} />
                      <input value={l.fora} onChange={e => mudar(i, { fora: e.target.value })} inputMode="numeric" className={`${campo} text-center`} aria-label={`Fora da linha ${i + 1}`} />
                      <input value={l.primeiro} onChange={e => mudar(i, { primeiro: e.target.value })} maxLength={100} placeholder="1º gol ★" className={`${campo} col-span-3 sm:col-span-1`} aria-label={`Primeiro gol da linha ${i + 1}`} />
                    </div>
                    {validacao.linhas[i]?.length > 0 && <p className="text-xs text-gold-700 dark:text-gold-300">{validacao.linhas[i].join(' ')}</p>}
                  </div>
                ))}
              </div>
              <button onClick={aplicar} disabled={!validacao.valido} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50">
                Confirmar prévia e preencher formulário
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
