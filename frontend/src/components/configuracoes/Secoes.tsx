import { useState, type FormEvent, type ReactNode } from 'react';
import { Check, LogOut, Mail, Moon, Plus, Shield, Sun, Trash2, UserPlus } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Carregando, ErroCarga } from '@/components/ui/Estado';
import { Input, Select, Switch } from '@/components/ui/Form';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { useRecurso } from '@/lib/useRecurso';
import type { ResponsaveisApi } from '@/types';

const botaoPrimario = 'flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm transition-colors disabled:opacity-60';
const botaoSecundario = 'flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors';

export function Cartao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: ReactNode }) {
  return (
    <section className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-5 md:p-6 space-y-5 animate-slide-up">
      <div>
        <h3 className="font-bold text-gray-900 dark:text-white">{titulo}</h3>
        {descricao && <p className="text-sm text-gray-400 mt-0.5">{descricao}</p>}
      </div>
      {children}
    </section>
  );
}

function useEnvio() {
  const showToast = useToast();
  const [enviando, setEnviando] = useState(false);
  const enviar = async (acao: () => Promise<{ mensagem: string }>, depois?: () => void, recarregar = false) => {
    setEnviando(true);
    try {
      const r = await acao();
      if (recarregar) { window.location.reload(); return; }
      showToast(r.mensagem); depois?.();
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    } finally { if (!recarregar) setEnviando(false); }
  };
  return { enviando, enviar };
}

export function SecaoPerfil() {
  const { usuario, logout } = useApp();
  const [nome, setNome] = useState(usuario?.nome ?? '');
  const [trocarEmail, setTrocarEmail] = useState(false);
  const [email, setEmail] = useState({ novo: '', senha: '' });
  const [sair, setSair] = useState(false);
  const { enviando, enviar } = useEnvio();
  if (!usuario) return null;

  const salvarNome = (e: FormEvent) => { e.preventDefault(); void enviar(() => api.put<{ mensagem: string }>('/perfil', { nome }), undefined, true); };
  const salvarEmail = (e: FormEvent) => { e.preventDefault(); void enviar(() => api.put<{ mensagem: string }>('/perfil/email', { email: email.novo, senhaAtual: email.senha }), undefined, true); };

  return (
    <div className="space-y-6">
      <Cartao titulo="Perfil" descricao="Seus dados de acesso ao sistema">
        <form onSubmit={salvarNome} className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white text-2xl font-bold shrink-0">
              {usuario.nome.split(' ').filter(Boolean).map(n => n[0]).slice(0, 2).join('').toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-gray-900 dark:text-white truncate">{usuario.nome}</p>
              <p className="text-sm text-gray-400 truncate">{usuario.email}</p>
            </div>
          </div>
          <Input label="Nome" value={nome} maxLength={100} onChange={e => setNome(e.target.value)}
            hint="Nome da sua conta. O nome que aparece em cada bolão continua o mesmo." />
          <button type="submit" disabled={enviando || nome.trim() === usuario.nome} className={botaoPrimario}>
            <Check className="w-4 h-4" /> Salvar alterações
          </button>
        </form>

        <div className="pt-4 border-t border-gray-100 dark:border-gray-800 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Mail className="w-5 h-5 text-brand-600 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">E-mail de acesso</p>
                <p className="text-xs text-gray-400 truncate">{usuario.email}</p>
              </div>
            </div>
            {!trocarEmail && <button onClick={() => setTrocarEmail(true)} className={botaoSecundario}>Alterar</button>}
          </div>
          {trocarEmail && (
            <form onSubmit={salvarEmail} className="grid sm:grid-cols-2 gap-3 animate-fade-in">
              <Input label="Novo e-mail" type="email" autoComplete="email" required value={email.novo} onChange={e => setEmail({ ...email, novo: e.target.value })} />
              <Input label="Senha atual" type="password" autoComplete="current-password" required value={email.senha} onChange={e => setEmail({ ...email, senha: e.target.value })} />
              <div className="sm:col-span-2 flex gap-2">
                <button type="submit" disabled={enviando} className={botaoPrimario}><Check className="w-4 h-4" /> Salvar e-mail</button>
                <button type="button" onClick={() => { setTrocarEmail(false); setEmail({ novo: '', senha: '' }); }} className={botaoSecundario}>Cancelar</button>
              </div>
            </form>
          )}
        </div>

        <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={() => setSair(true)} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 font-medium text-sm hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors">
            <LogOut className="w-4 h-4" /> Sair da conta
          </button>
        </div>
      </Cartao>
      <ConfirmDialog open={sair} onClose={() => setSair(false)} onConfirm={() => logout()} title="Sair da conta?"
        message="Você precisará fazer login novamente para acessar o sistema." confirmLabel="Sair" danger />
    </div>
  );
}

export function SecaoSeguranca() {
  const vazio = { senhaAtual: '', novaSenha: '', confirmacao: '' };
  const [form, setForm] = useState(vazio);
  const { enviando, enviar } = useEnvio();
  const confere = !form.confirmacao || form.novaSenha === form.confirmacao;
  const salvar = (e: FormEvent) => { e.preventDefault(); void enviar(() => api.put<{ mensagem: string }>('/perfil/senha', form), () => setForm(vazio)); };
  return (
    <Cartao titulo="Segurança" descricao="Troque a senha usada para entrar no sistema">
      <form onSubmit={salvar} className="space-y-3 max-w-md">
        <Input label="Senha atual" type="password" autoComplete="current-password" required value={form.senhaAtual} onChange={e => setForm({ ...form, senhaAtual: e.target.value })} />
        <Input label="Nova senha" type="password" autoComplete="new-password" required minLength={6} value={form.novaSenha} onChange={e => setForm({ ...form, novaSenha: e.target.value })} hint="Mínimo de 6 caracteres." />
        <Input label="Confirmar nova senha" type="password" autoComplete="new-password" required value={form.confirmacao} onChange={e => setForm({ ...form, confirmacao: e.target.value })}
          error={confere ? undefined : 'As senhas não conferem.'} />
        <button type="submit" disabled={enviando || !confere} className={botaoPrimario}><Shield className="w-4 h-4" /> Alterar senha</button>
      </form>
    </Cartao>
  );
}

export function SecaoAparencia() {
  const { darkMode, toggleDarkMode } = useApp();
  return (
    <Cartao titulo="Aparência" descricao="Fica salvo neste navegador">
      <div className="flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          {darkMode ? <Moon className="w-5 h-5 text-brand-600" /> : <Sun className="w-5 h-5 text-gold-600" />}
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Modo escuro</p>
            <p className="text-xs text-gray-400">Alterna entre tema claro e escuro</p>
          </div>
        </div>
        <Switch checked={darkMode} onChange={toggleDarkMode} />
      </div>
    </Cartao>
  );
}

export function SecaoResponsaveis() {
  const { logout } = useApp();
  const showToast = useToast();
  const { dados, carregando, erro, recarregar } = useRecurso<ResponsaveisApi>('/responsaveis');
  const vazio = { participacaoId: '', email: '', nome: '', senha: '' };
  const [form, setForm] = useState(vazio);
  const [remover, setRemover] = useState<ResponsaveisApi['responsaveis'][number] | null>(null);
  const { enviando, enviar } = useEnvio();

  const adicionar = (e: FormEvent) => {
    e.preventDefault();
    void enviar(() => api.post<{ mensagem: string }>('/responsaveis', { ...form, participacaoId: form.participacaoId ? Number(form.participacaoId) : null }),
      () => { setForm(vazio); void recarregar(); });
  };
  const confirmarRemocao = async () => {
    if (!remover) return;
    try {
      const r = await api.delete<{ mensagem: string; logout: boolean }>(`/responsaveis/${remover.id}`);
      showToast(r.mensagem);
      if (r.logout) logout(); else await recarregar();
    } catch (e) { showToast(e instanceof Error ? e.message : 'Não foi possível remover.', 'error'); throw e; }
  };

  return (
    <div className="space-y-6">
      <Cartao titulo="Responsáveis" descricao="O acesso vale só para este bolão. Pelo menos um responsável com conta ativa deve permanecer.">
        {erro && <ErroCarga mensagem={erro} onTentar={recarregar} />}
        {!dados && carregando && <Carregando linhas={2} />}
        {dados && (
          <div className="space-y-2">
            {dados.responsaveis.map(r => (
              <div key={r.id} className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
                <Avatar nome={r.nome} id={r.id} size="md" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{r.nome}</p>
                  <p className="text-xs text-gray-400 truncate">{r.semAcesso ? 'Sem conta habilitada para acesso' : r.email}</p>
                </div>
                {r.souEu && <Badge color="purple" size="sm">Você</Badge>}
                <button onClick={() => setRemover(r)} title="Remover acesso" aria-label={`Remover acesso de ${r.nome}`} className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Cartao>

      {dados && (
        <Cartao titulo="Adicionar responsável" descricao="Informe o e-mail da conta. Para criar uma conta nova, preencha também nome e senha inicial. Contas existentes mantêm a senha.">
          <form onSubmit={adicionar} className="space-y-4">
            <Select label="Vincular a um participante existente" value={form.participacaoId} onChange={e => setForm({ ...form, participacaoId: e.target.value })}>
              <option value="">Usar vínculo da conta ou criar participante</option>
              {dados.participantesSemConta.map(p => <option key={p.id} value={p.id}>{p.nome} · Registro {p.id}</option>)}
            </Select>
            <p className="-mt-2 text-xs text-gray-400">Escolha a pessoa já cadastrada para manter os palpites dela e evitar um segundo registro.</p>
            <div className="grid sm:grid-cols-3 gap-3">
              <Input label="E-mail" type="email" required autoComplete="off" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
              <Input label="Nome (conta nova)" maxLength={100} autoComplete="off" value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <Input label="Senha inicial (conta nova)" type="password" autoComplete="new-password" value={form.senha} onChange={e => setForm({ ...form, senha: e.target.value })} />
            </div>
            <button type="submit" disabled={enviando} className={botaoPrimario}>
              {enviando ? <Plus className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />} Adicionar responsável
            </button>
          </form>
        </Cartao>
      )}

      <ConfirmDialog open={!!remover} onClose={() => setRemover(null)} onConfirm={confirmarRemocao}
        title="Remover acesso?"
        message={remover?.souEu
          ? <>Você vai remover o <strong>seu próprio acesso</strong> a este bolão e sair da conta. A participação e o histórico ficam guardados.</>
          : <>{remover?.nome} deixa de acessar este bolão. A participação e o histórico ficam guardados.</>}
        confirmLabel="Remover acesso" danger />
    </div>
  );
}
