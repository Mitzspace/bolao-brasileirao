import { useState } from 'react';
import { Mail, Lock, ArrowRight, Shield } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { LogoApp } from '@/components/ui/LogoApp';

const estilosMensagem = {
  error: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300',
  success: 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300',
  info: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300',
};

export function LoginScreen() {
  const { dados } = useApp();
  const [loading, setLoading] = useState(false);

  const handleSubmit = () => {
    setLoading(true);
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-brand-50 via-white to-gold-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <div aria-hidden="true" className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-72 h-72 bg-brand-200/40 dark:bg-brand-900/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-72 h-72 bg-gold-200/40 dark:bg-gold-900/20 rounded-full blur-3xl" />
        {/* Linhas do gramado ao fundo: meio-campo, círculo central e as duas grandes áreas. */}
        <svg viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 w-full h-full text-brand-600/[0.07] dark:text-brand-400/[0.06]">
          <g fill="none" stroke="currentColor" strokeWidth="4">
            <rect x="60" y="60" width="1080" height="680" rx="8" />
            <line x1="600" y1="60" x2="600" y2="740" />
            <circle cx="600" cy="400" r="110" />
            <circle cx="600" cy="400" r="6" fill="currentColor" />
            <rect x="60" y="230" width="170" height="340" />
            <rect x="970" y="230" width="170" height="340" />
            <rect x="60" y="320" width="60" height="160" />
            <rect x="1080" y="320" width="60" height="160" />
          </g>
        </svg>
      </div>

      <div className="relative w-full max-w-md">
        <div className="flex flex-col items-center mb-8 animate-fade-in">
          <LogoApp tamanho="lg" className="shadow-lg mb-4" />
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white">Gestão de bolões</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Palpites e classificação do seu bolão</p>
        </div>

        <form action={dados.links.login} method="POST" onSubmit={handleSubmit} className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md rounded-3xl shadow-xl p-6 md:p-8 animate-slide-up border border-white dark:border-gray-800 ring-1 ring-gray-900/5 dark:ring-white/5">
          <input type="hidden" name="csrf_token" value={dados.csrfToken} />
          <input type="hidden" name="nova_interface" value="1" />
          {dados.mensagens.map((mensagem, index) => (
            <p key={index} role={mensagem.tipo === 'error' ? 'alert' : 'status'} className={`mb-4 rounded-xl p-3 text-sm ${estilosMensagem[mensagem.tipo]}`}>{mensagem.texto}</p>
          ))}
          <div className="flex items-center gap-2 mb-6 p-3 rounded-xl bg-gold-50 dark:bg-gold-900/20 border border-gold-200 dark:border-gold-800/40">
            <Shield className="w-5 h-5 text-gold-600 shrink-0" />
            <p className="text-sm text-gold-800 dark:text-gold-300 font-medium">Acesso restrito aos responsáveis pelo bolão</p>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">E-mail</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  id="email"
                  name="email"
                  autoComplete="email"
                  required
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 transition-colors"
                  placeholder="seu@email.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="senha" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Senha</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="password"
                  id="senha"
                  name="senha"
                  autoComplete="current-password"
                  required
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <label className="flex items-start gap-3 cursor-pointer select-none rounded-xl p-1 -m-1">
              <input type="checkbox" name="lembrar" value="1" defaultChecked
                className="mt-0.5 w-5 h-5 rounded border-gray-300 dark:border-gray-600 text-brand-600 accent-brand-600 focus:ring-2 focus:ring-brand-500/40" />
              <span>
                <span className="block text-sm font-medium text-gray-700 dark:text-gray-300">Manter conectado</span>
                <span className="block text-xs text-gray-400">Continua conectado por 30 dias neste aparelho. Desmarque em computador compartilhado.</span>
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-6 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-br from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white font-semibold shadow-md shadow-brand-600/25 transition-all disabled:opacity-60"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                Entrar
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-gray-400 mt-5">
            Esqueceu a senha? Peça ao administrador do sistema para redefinir.
          </p>
        </form>
      </div>
    </div>
  );
}
