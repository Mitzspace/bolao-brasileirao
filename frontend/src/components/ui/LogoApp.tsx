/**
 * Logo da página = o mesmo arquivo usado como favicon da aba.
 *
 * O endereço vem do <link rel="icon" type="image/svg+xml"> do <head> (templates/_icones.html,
 * incluído pela gestão e pela página pública). Assim existe um único arquivo de ícone
 * (static/icones/favicon.svg): trocar o favicon troca também o logo dentro da página.
 */
import { useId } from 'react';
import { TEMAS, useTemaAtivo, type TemaCampeonato } from '@/lib/temaCampeonato';

const RESERVA = '/static/icones/favicon.svg';

function enderecoDoFavicon(): string {
  if (typeof document === 'undefined') return RESERVA;
  const link = document.querySelector<HTMLLinkElement>('link[rel~="icon"][type="image/svg+xml"]')
    ?? document.querySelector<HTMLLinkElement>('link[rel~="icon"]');
  return link?.getAttribute('href') || RESERVA;
}

const ENDERECO = enderecoDoFavicon();

const TAMANHOS = { sm: 'w-10 h-10 rounded-xl', md: 'w-12 h-12 rounded-xl', lg: 'w-16 h-16 rounded-2xl' } as const;

/**
 * Taça dourada sobre as cores do campeonato: logo no lugar do favicon quando o campeonato tem tema.
 * Os ids dos degradês são únicos por instância: no celular a cópia da barra lateral fica oculta
 * (display:none) e, com ids repetidos, o logo do cabeçalho apontava para ela e saía sem cor.
 * O recorte arredondado fica num invólucro (Safari nem sempre recorta o <svg> pelo border-radius).
 */
function TrofeuTema({ tema, className }: { tema: TemaCampeonato; className: string }) {
  const { fundo, taca } = TEMAS[tema];
  const id = useId().replace(/:/g, '');
  const idFundo = `trofeu-fundo-${id}`;
  const idOuro = `trofeu-ouro-${id}`;
  return (
    <span aria-hidden="true" className={`inline-block overflow-hidden ${className}`}>
      <svg viewBox="0 0 64 64" className="block w-full h-full">
        <defs>
          <linearGradient id={idFundo} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={fundo[0]} /><stop offset="1" stopColor={fundo[1]} /></linearGradient>
          <linearGradient id={idOuro} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={taca[0]} /><stop offset="1" stopColor={taca[1]} /></linearGradient>
        </defs>
        <rect width="64" height="64" fill={`url(#${idFundo})`} />
        <path d="M22 12h20v14c0 7-4 12-10 12s-10-5-10-12z" fill={`url(#${idOuro})`} />
        <path d="M22 16h-6c0 8 3 12 8 13M42 16h6c0 8-3 12-8 13" fill="none" stroke={taca[0]} strokeWidth="3" strokeLinecap="round" />
        <path d="M29 38h6v7h-6z" fill={taca[1]} />
        <path d="M23 46h18l2 6H21z" fill={`url(#${idOuro})`} />
      </svg>
    </span>
  );
}

export function LogoApp({ tamanho = 'sm', className = '' }: { tamanho?: keyof typeof TAMANHOS; className?: string }) {
  const tema = useTemaAtivo();
  if (tema) return <TrofeuTema tema={tema} className={`${TAMANHOS[tamanho]} shrink-0 shadow-md select-none ${className}`} />;
  return (
    <img src={ENDERECO} alt="" aria-hidden="true" draggable={false} decoding="async"
      className={`${TAMANHOS[tamanho]} shrink-0 shadow-md select-none ${className}`} />
  );
}
