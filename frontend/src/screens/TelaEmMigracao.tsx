import { ArrowRight, ExternalLink } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { useApp } from '@/context/AppContext';

interface Atalho { label: string; href?: string; destaque?: boolean }

/**
 * Tela provisória: enquanto uma aba não é migrada, ela abre a tela atual do
 * sistema no bolão selecionado. Será removida na etapa de limpeza.
 */
export function TelaEmMigracao({ titulo, descricao, atalhos }: { titulo: string; descricao: string; atalhos: Atalho[] }) {
  const { bolao } = useApp();
  return (
    <div>
      <Header title={titulo} subtitle={bolao ? `${bolao.nome} · ${bolao.chave}` : undefined} />
      <div className="p-4 md:p-8 pb-28 md:pb-8">
        <section className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-6 space-y-4 animate-slide-up">
          <p className="text-sm text-gray-500 dark:text-gray-400">{descricao}</p>
          <div className="flex flex-wrap gap-3">
            {atalhos.filter(a => a.href).map(a => (
              <a key={a.label} href={a.href} className={a.destaque ? 'button-primary' : 'inline-flex items-center gap-2 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}>
                {a.label} {a.destaque ? <ArrowRight className="w-4 h-4" /> : <ExternalLink className="w-4 h-4" />}
              </a>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
