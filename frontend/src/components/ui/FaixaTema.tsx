import { Trophy } from 'lucide-react';
import { TEMAS, useTemaAtivo } from '@/lib/temaCampeonato';

/** Faixa de abertura do tema do campeonato (cada competição tem a sua); some nos bolões sem tema. */
export function FaixaTema({ className = '' }: { className?: string }) {
  const tema = useTemaAtivo();
  if (!tema) return null;
  const { titulo, lema, bandeiras = [] } = TEMAS[tema];
  return (
    <div className={`relative overflow-hidden bg-gradient-to-r from-brand-900 via-brand-700 to-brand-900 text-white ${className}`}>
      <div aria-hidden="true" className="absolute inset-0 opacity-20 bg-[repeating-linear-gradient(90deg,transparent_0_46px,rgba(255,255,255,.35)_46px_48px)]" />
      <div className="relative max-w-5xl mx-auto px-4 md:px-8 py-2 flex items-center gap-3">
        <Trophy className="w-5 h-5 text-gold-400 shrink-0" />
        <p className="min-w-0 flex-1 truncate text-xs md:text-sm font-bold tracking-wide uppercase">
          {titulo} <span className="hidden sm:inline font-medium normal-case opacity-80">· {lema}</span>
        </p>
        <div className="flex -space-x-1.5 shrink-0">
          {bandeiras.map(c => (
            <img key={c} src={`https://a.espncdn.com/i/teamlogos/countries/500/${c}.png`} alt="" loading="lazy"
              className="w-6 h-6 rounded-full bg-white object-contain p-0.5 ring-2 ring-brand-900" />
          ))}
        </div>
      </div>
    </div>
  );
}
