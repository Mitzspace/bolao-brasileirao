import { Award, CircleSlash, Crown, ListOrdered, Star, Target } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import type { Regras } from '@/types';

interface Props {
  aberto: boolean;
  onClose: () => void;
  regras: Regras | null;
  /** 'fora_da_conta' ou 'zero' (rodadas antes da entrada de quem chegou depois). */
  politicaEntrada?: string;
  /** Texto extra no fim (ex.: até qual rodada a classificação foi divulgada). */
  rodape?: string;
}

function pts(n: number) { return `${n} ${n === 1 ? 'ponto' : 'pontos'}`; }

function Exemplo({ palpite, jogo, resultado }: { palpite: string; jogo: string; resultado: string }) {
  return (
    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
      Ex.: palpite <strong className="text-gray-700 dark:text-gray-200 tabular-nums">{palpite}</strong>, jogo terminou <strong className="text-gray-700 dark:text-gray-200 tabular-nums">{jogo}</strong> → {resultado}
    </p>
  );
}

/** Explicação das regras do bolão para o participante (somente leitura). Também serve à gestão. */
export function ComoFuncionaPontuacao({ aberto, onClose, regras, politicaEntrada, rodape }: Props) {
  return (
    <Modal open={aberto} onClose={onClose} title="Como funciona a pontuação" size="lg">
      {!regras ? <p className="text-sm text-gray-400">Carregando as regras…</p> : (
        <div className="space-y-5 text-sm text-gray-700 dark:text-gray-300">
          <p>A cada jogo com resultado, cada palpite vale os pontos abaixo. As regras valem para todas as rodadas deste bolão.</p>

          <div className="grid sm:grid-cols-2 gap-3">
            <div className="rounded-xl border border-gray-100 dark:border-gray-800 p-4">
              <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-white"><Target className="w-4 h-4 text-brand-600" />Jogo comum</div>
              <ul className="mt-2 space-y-1">
                <li className="flex justify-between gap-3"><span>Placar exato (cravada)</span><strong className="text-brand-600 dark:text-brand-400 whitespace-nowrap">{pts(regras.comumExato)}</strong></li>
                <li className="flex justify-between gap-3"><span>Só o vencedor ou o empate</span><strong className="text-brand-600 dark:text-brand-400 whitespace-nowrap">{pts(regras.comumResultado)}</strong></li>
              </ul>
              <Exemplo palpite="2 × 1" jogo="3 × 1" resultado={`acertou o vencedor: ${pts(regras.comumResultado)}`} />
            </div>
            <div className="rounded-xl border border-gold-200 dark:border-gold-800/50 bg-gold-50/50 dark:bg-gold-900/10 p-4">
              <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-white"><Star className="w-4 h-4 text-gold-500 fill-gold-400" />Clássico</div>
              <ul className="mt-2 space-y-1">
                <li className="flex justify-between gap-3"><span>Placar exato (cravada)</span><strong className="text-gold-700 dark:text-gold-300 whitespace-nowrap">{pts(regras.classicoExato)}</strong></li>
                <li className="flex justify-between gap-3"><span>Só o vencedor ou o empate</span><strong className="text-gold-700 dark:text-gold-300 whitespace-nowrap">{pts(regras.classicoResultado)}</strong></li>
              </ul>
              <Exemplo palpite="1 × 1" jogo="1 × 1" resultado={`cravou: ${pts(regras.classicoExato)}`} />
            </div>
          </div>

          <div className="rounded-xl bg-brand-50 dark:bg-brand-900/20 p-4 flex gap-3">
            <Award className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-gray-900 dark:text-white">Bônus de primeiro gol: +{pts(regras.primeiroGol)}</p>
              <p className="mt-1">Nos clássicos, quem acerta quem marcou o primeiro gol ganha o bônus, mesmo errando o placar (vale gol contra). Não vale em jogo 0 × 0.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <CircleSlash className="w-5 h-5 text-gray-400 shrink-0 mt-0.5" />
            <p>Palpite não enviado ou enviado fora do prazo vale 0. {politicaEntrada === 'fora_da_conta'
              ? 'Para quem entrou depois, as rodadas anteriores à entrada ficam fora da conta.'
              : 'Para quem entrou depois, as rodadas anteriores à entrada contam com zero pontos.'}</p>
          </div>

          <div className="flex gap-3">
            <ListOrdered className="w-5 h-5 text-gray-400 shrink-0 mt-0.5" />
            <div>
              <p><strong className="text-gray-900 dark:text-white">Total</strong> = pontos dos placares + bônus.</p>
              <p className="mt-1"><strong className="text-gray-900 dark:text-white">Desempate:</strong> total de pontos, depois mais cravadas, depois mais resultados (vencedor ou empate) e, por fim, ordem alfabética.</p>
            </div>
          </div>

          {rodape && (
            <p className="flex gap-2 items-start rounded-xl bg-gray-50 dark:bg-gray-800 p-3 text-xs text-gray-500 dark:text-gray-400">
              <Crown className="w-4 h-4 shrink-0 text-gold-500" />{rodape}
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}
