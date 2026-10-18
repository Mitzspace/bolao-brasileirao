/** Fases a partir das quais dá para importar jogos de copas (valor = estágio enviado à API). */
export const FASES_INICIAIS: { valor: string; rotulo: string }[] = [
  { valor: '', rotulo: 'Todas as fases (desde a 1ª)' },
  { valor: 'LAST_32', rotulo: '16 avos de final em diante' },
  { valor: 'LAST_16', rotulo: 'Oitavas de final em diante' },
  { valor: 'QUARTER_FINALS', rotulo: 'Quartas de final em diante' },
  { valor: 'SEMI_FINALS', rotulo: 'Semifinais em diante' },
  { valor: 'FINAL', rotulo: 'Só a final' },
];

export const DICA_FASE_INICIAL = 'Jogos de fases anteriores não são importados, nem pela atualização automática.';
