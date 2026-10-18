import type { Escudo, TabelaApi } from '@/types';

/** Fase eliminatória pelo nome ("Rodada 10 · Oitavas de final", "2ª fase", "Final"...). Fase de grupos/liga não entra. */
const MATA_MATA = /16 avos|oitavas|quartas|semi\s?final|final|terceiro|3º|playoff|eliminat|\dª fase/i;
const TERCEIRO = /terceiro|3º/i;

export const ehMataMata = (nome: string) => MATA_MATA.test(nome);

export interface TimeChave { nome: string; escudo?: Escudo | null }
export interface PernaChave {
  golsA: number | null; golsB: number | null; penA: number | null; penB: number | null; dataTexto: string | null;
}
export interface Confronto {
  chave: string;
  a: TimeChave;
  b: TimeChave;
  pernas: PernaChave[];
  /** Todas as partidas do confronto já terminaram. */
  completo: boolean;
  totalA: number | null;
  totalB: number | null;
  vencedor: 'a' | 'b' | null;
}
export interface FaseChave { nome: string; original: string; confrontos: Confronto[] }

interface JogoChave {
  casa: string; fora: string; escudoCasa?: Escudo | null; escudoFora?: Escudo | null;
  golsCasa: number | null; golsFora: number | null; penCasa: number | null; penFora: number | null;
  dataTexto: string | null; encerrado: boolean;
}

const nomeCurto = (nome: string) => nome.replace(/^Rodada\s+\d+\s*·\s*/i, '');

/** Agrupa as partidas da fase em confrontos (ida e volta ficam juntas). */
function montarFase(nome: string, jogos: JogoChave[]): FaseChave {
  const grupos = new Map<string, JogoChave[]>();
  for (const j of jogos) {
    const chave = [j.casa, j.fora].sort().join('|');
    grupos.set(chave, [...(grupos.get(chave) ?? []), j]);
  }
  const esperadas = Math.max(1, ...[...grupos.values()].map(g => g.length));
  const confrontos = [...grupos.entries()].map(([chave, partidas]): Confronto => {
    const [primeira] = partidas;
    const a: TimeChave = { nome: primeira.casa, escudo: primeira.escudoCasa };
    const b: TimeChave = { nome: primeira.fora, escudo: primeira.escudoFora };
    const pernas = partidas.map((j): PernaChave => {
      const invertida = j.casa !== a.nome;
      const [golsA, golsB] = invertida ? [j.golsFora, j.golsCasa] : [j.golsCasa, j.golsFora];
      const [penA, penB] = invertida ? [j.penFora, j.penCasa] : [j.penCasa, j.penFora];
      return { golsA, golsB, penA, penB, dataTexto: j.dataTexto };
    });
    const completo = partidas.length >= esperadas && partidas.every(j => j.encerrado);
    const soma = (lado: 'golsA' | 'golsB') => pernas.reduce((t, p) => t + (p[lado] ?? 0), 0);
    const temPlacar = pernas.some(p => p.golsA !== null && p.golsB !== null);
    const totalA = temPlacar ? soma('golsA') : null;
    const totalB = temPlacar ? soma('golsB') : null;
    let vencedor: Confronto['vencedor'] = null;
    if (completo && totalA !== null && totalB !== null) {
      const ultima = pernas[pernas.length - 1];
      if (totalA !== totalB) vencedor = totalA > totalB ? 'a' : 'b';
      else if (ultima.penA != null && ultima.penB != null && ultima.penA !== ultima.penB) vencedor = ultima.penA > ultima.penB ? 'a' : 'b';
    }
    return { chave, a, b, pernas, completo, totalA, totalB, vencedor };
  });
  return { nome: nomeCurto(nome), original: nome, confrontos };
}

/**
 * Fases iniciais (ex.: "1ª fase" da Copa do Brasil, playoffs da Sul-Americana) não se encadeiam em
 * metades: entram times novos a cada fase. Ficam fora da chave, que começa na primeira fase que
 * tem ao menos o dobro de confrontos da seguinte.
 */
function aparar(fases: FaseChave[]): { fases: FaseChave[]; fora: FaseChave[] } {
  let inicio = 0;
  fases.forEach((f, i) => {
    if (i < fases.length - 1 && f.confrontos.length < 2 * fases[i + 1].confrontos.length) inicio = i + 1;
  });
  return { fases: fases.slice(inicio), fora: fases.slice(0, inicio) };
}

/** Fases eliminatórias (em ordem) e a disputa de 3º lugar, que fica fora das colunas da chave. `fora` = fases iniciais, só em lista. */
export function fasesDaChave(dados: TabelaApi): { fases: FaseChave[]; terceiro: FaseChave | null; fora: FaseChave[] } {
  const origem: { nome: string; jogos: JogoChave[] }[] = dados.confrontos.length
    ? dados.confrontos.filter(f => ehMataMata(f.nome)).map(f => ({
      nome: f.nome,
      jogos: f.jogos.map(j => ({
        casa: j.casa, fora: j.fora, escudoCasa: j.escudoCasa, escudoFora: j.escudoFora,
        golsCasa: j.golsCasa, golsFora: j.golsFora, penCasa: j.penaltisCasa ?? null, penFora: j.penaltisFora ?? null,
        dataTexto: j.dataTexto, encerrado: j.status === 'encerrado',
      })),
    }))
    : dados.mataMata.map(f => ({
      nome: f.nome,
      jogos: f.jogos.map(j => ({
        casa: j.casa, fora: j.fora, golsCasa: j.gols_casa, golsFora: j.gols_fora, penCasa: null, penFora: null,
        dataTexto: j.horario, encerrado: j.status === 'FINISHED' || j.status === 'AWARDED',
      })),
    }));
  const todas = origem.filter(f => f.jogos.length).map(f => montarFase(f.nome, f.jogos));
  const { fases, fora } = aparar(todas.filter(f => !TERCEIRO.test(f.nome)));
  return { fases, fora, terceiro: todas.find(f => TERCEIRO.test(f.nome)) ?? null };
}

export const CARD_W = 212;
export const CARD_H = 92;
export const GAP_X = 52;
export const GAP_Y = 14;
export const TOPO = 40;

export interface ConfrontoPosicionado extends Confronto { x: number; y: number }
/** `lado` 'e': a linha sai da borda direita do card de origem; 'd': da borda esquerda (lado direito da chave). */
export interface Ligacao { de: ConfrontoPosicionado; para: ConfrontoPosicionado; lado: 'e' | 'd' }
export interface Cabecalho { nome: string; x: number }

const compartilha = (x: Confronto, y: Confronto) =>
  [x.a.nome, x.b.nome].some(n => n === y.a.nome || n === y.b.nome);
const PASSO = CARD_H + GAP_Y;
const colunaX = (k: number) => k * (CARD_W + GAP_X);

/** Coloca cada confronto na altura média dos que o alimentam; sem alimentadores, espalha na coluna. */
function posicionar(colunas: Confronto[][], xDe: (k: number) => number, alturaBase: number) {
  const posicionadas: ConfrontoPosicionado[][] = [];
  colunas.forEach((col, k) => {
    const itens = col.map((c, i) => {
      let y: number;
      if (k === 0) y = i * PASSO;
      else {
        const pais = posicionadas[k - 1].filter(p => compartilha(p, c));
        y = pais.length ? pais.reduce((t, p) => t + p.y, 0) / pais.length
          : ((i + 0.5) * alturaBase) / col.length - PASSO / 2;
      }
      return { ...c, x: xDe(k), y };
    }).sort((m, n) => m.y - n.y);
    for (let i = 1; i < itens.length; i++) itens[i].y = Math.max(itens[i].y, itens[i - 1].y + PASSO);
    posicionadas.push(itens);
  });
  return posicionadas;
}

function ligar(colunas: ConfrontoPosicionado[][], lado: Ligacao['lado']) {
  const ligacoes: Ligacao[] = [];
  colunas.forEach((col, k) => {
    if (k === 0) return;
    col.forEach(para => colunas[k - 1].filter(de => compartilha(de, para)).forEach(de => ligacoes.push({ de, para, lado })));
  });
  return ligacoes;
}

/**
 * Posiciona os confrontos em colunas. Quem alimenta cada confronto é descoberto pelos times em comum
 * entre uma fase e a seguinte, e a ordem das fases anteriores segue a da seguinte para as linhas não
 * se cruzarem. Com uma final única e pelo menos duas semifinais, a chave se divide em dois lados que
 * convergem para a final no centro (como na Copa do Mundo); senão, segue em colunas da esquerda para a direita.
 */
export function organizarChave(fases: FaseChave[]) {
  const colunas: Confronto[][] = fases.map(f => f.confrontos);
  for (let k = colunas.length - 2; k >= 0; k--) {
    const proxima = colunas[k + 1];
    const indicePai = (c: Confronto) => { const i = proxima.findIndex(p => compartilha(c, p)); return i === -1 ? Infinity : i; };
    colunas[k] = colunas[k].map((c, i) => ({ c, i, pai: indicePai(c) }))
      .sort((m, n) => (m.pai === n.pai ? m.i - n.i : m.pai < n.pai ? -1 : 1)).map(m => m.c);
  }

  const ultima = colunas.length - 1;
  const dividido = colunas.length >= 2 && colunas[ultima].length === 1 && colunas[ultima - 1].length >= 2;

  if (!dividido) {
    const posicionadas = posicionar(colunas, colunaX, Math.max(1, colunas[0]?.length ?? 1) * PASSO);
    return {
      colunas: posicionadas, ligacoes: ligar(posicionadas, 'e'), dividido,
      cabecalhos: fases.map((f, k): Cabecalho => ({ nome: f.nome, x: colunaX(k) })),
      largura: Math.max(0, colunas.length * (CARD_W + GAP_X) - GAP_X),
      altura: Math.max(0, ...posicionadas.flat().map(c => c.y + CARD_H)),
    };
  }

  // Lado de cada confronto: o do confronto seguinte que ele alimenta; nas semifinais, metade para cada lado.
  const lado = new Map<string, 'e' | 'd'>();
  for (let k = ultima - 1; k >= 0; k--) {
    const metade = Math.ceil(colunas[k].length / 2);
    colunas[k].forEach((c, i) => {
      const pai = k === ultima - 1 ? undefined : colunas[k + 1].find(p => compartilha(c, p));
      lado.set(`${k}|${c.chave}`, (pai && lado.get(`${k + 1}|${pai.chave}`)) || (i < metade ? 'e' : 'd'));
    });
  }
  const metades = (l: 'e' | 'd') => colunas.slice(0, ultima).map((col, k) => col.filter(c => lado.get(`${k}|${c.chave}`) === l));
  const esq = metades('e'), dir = metades('d');
  const alturaBase = Math.max(1, esq[0].length, dir[0].length) * PASSO;
  const xFinal = colunaX(ultima);
  const e = posicionar(esq, colunaX, alturaBase);
  const d = posicionar(dir, k => colunaX(2 * ultima - k), alturaBase);

  const [final] = colunas[ultima];
  const semis = [...e[ultima - 1], ...d[ultima - 1]].filter(p => compartilha(p, final));
  const yFinal = semis.length ? semis.reduce((t, p) => t + p.y, 0) / semis.length : (alturaBase - PASSO) / 2;
  const colFinal: ConfrontoPosicionado[] = [{ ...final, x: xFinal, y: yFinal }];
  // A final entra como última coluna de cada lado só para gerar as linhas das semifinais.
  const ligacoes = [...ligar([...e, colFinal], 'e'), ...ligar([...d, colFinal], 'd')];

  return {
    colunas: [...e, colFinal, ...d], ligacoes, dividido,
    cabecalhos: [
      ...fases.slice(0, ultima).map((f, k): Cabecalho => ({ nome: f.nome, x: colunaX(k) })),
      { nome: fases[ultima].nome, x: xFinal },
      ...fases.slice(0, ultima).map((f, k): Cabecalho => ({ nome: f.nome, x: colunaX(2 * ultima - k) })),
    ],
    largura: (2 * ultima + 1) * (CARD_W + GAP_X) - GAP_X,
    altura: Math.max(0, ...[...e.flat(), ...d.flat(), ...colFinal].map(c => c.y + CARD_H)),
  };
}
