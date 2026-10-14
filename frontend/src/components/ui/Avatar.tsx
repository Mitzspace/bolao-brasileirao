const cores = ['#059669', '#d97706', '#2563eb', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#4f46e5', '#65a30d', '#ea580c'];

/** Círculo com iniciais, no estilo do Bolt. A cor é só visual, derivada do id. */
export function Avatar({ nome, id, size = 'sm' }: { nome: string; id: number; size?: 'sm' | 'md' | 'lg' }) {
  const iniciais = nome.split(/\s+/).filter(Boolean).map(n => n[0]).slice(0, 2).join('').toUpperCase() || '?';
  const tamanho = size === 'lg' ? 'w-14 h-14 text-lg' : size === 'md' ? 'w-10 h-10 text-sm' : 'w-8 h-8 text-xs';
  return (
    <div className={`${tamanho} rounded-full flex items-center justify-center text-white font-bold shrink-0`} style={{ backgroundColor: cores[Math.abs(id) % cores.length] }} aria-hidden="true">
      {iniciais}
    </div>
  );
}
