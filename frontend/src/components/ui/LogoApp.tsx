/**
 * Logo da página = o mesmo arquivo usado como favicon da aba.
 *
 * O endereço vem do <link rel="icon" type="image/svg+xml"> do <head> (templates/_icones.html,
 * incluído pela gestão e pela página pública). Assim existe um único arquivo de ícone
 * (static/icones/favicon.svg): trocar o favicon troca também o logo dentro da página.
 */
const RESERVA = '/static/icones/favicon.svg';

function enderecoDoFavicon(): string {
  if (typeof document === 'undefined') return RESERVA;
  const link = document.querySelector<HTMLLinkElement>('link[rel~="icon"][type="image/svg+xml"]')
    ?? document.querySelector<HTMLLinkElement>('link[rel~="icon"]');
  return link?.getAttribute('href') || RESERVA;
}

const ENDERECO = enderecoDoFavicon();

const TAMANHOS = { sm: 'w-10 h-10 rounded-xl', md: 'w-12 h-12 rounded-xl', lg: 'w-16 h-16 rounded-2xl' } as const;

export function LogoApp({ tamanho = 'sm', className = '' }: { tamanho?: keyof typeof TAMANHOS; className?: string }) {
  return (
    <img src={ENDERECO} alt="" aria-hidden="true" draggable={false} decoding="async"
      className={`${TAMANHOS[tamanho]} shrink-0 shadow-md select-none ${className}`} />
  );
}
