(() => {
    const form = document.querySelector('[data-lancamento]');
    if (!form) return;
    const texto = document.getElementById('mensagem-whatsapp');
    const status = document.getElementById('status-whatsapp');
    const painel = document.getElementById('previa-whatsapp');
    const ler = document.getElementById('ler-whatsapp');
    painel.addEventListener('keydown', event => {
        if (event.key === 'Enter' && event.target.matches('input')) {
            event.preventDefault();
            event.stopPropagation();
        }
    });
    const node = (tag, text, classe) => {
        const el = document.createElement(tag);
        if (text) el.textContent = text;
        if (classe) el.className = classe;
        return el;
    };
    let geracao = 0;
    texto.addEventListener('input', () => { geracao++; painel.replaceChildren(); });
    ler.addEventListener('click', async () => {
        const atual = ++geracao;
        painel.replaceChildren();
        status.textContent = 'Lendo mensagem…';
        ler.disabled = true;
        const dados = new FormData();
        ['csrf_token', 'participante_id', 'rodada_id'].forEach(nome => dados.set(nome, form.elements[nome].value));
        dados.set('texto', texto.value);
        try {
            const response = await fetch(form.dataset.previaUrl, {method:'POST', body:dados});
            const resultado = await response.json();
            if (atual !== geracao) return;
            if (!response.ok) throw new Error(resultado.erro || 'Não foi possível ler a mensagem. Confira sua sessão e tente novamente.');
            if (!resultado.reconhecido) {
                status.textContent = 'Formato totalmente irreconhecível para esta rodada. Nenhum palpite foi preenchido. Corrija a mensagem ou lance manualmente.';
                return;
            }
            status.textContent = 'Prévia: corrija os jogos e placares. Nada foi gravado. Desmarque as linhas que deseja ignorar.';
            const linhas = [];
            const tabela = node('table', '', 'ui-table');
            const cabecalho = node('tr');
            ['Usar', 'Mensagem / alertas', 'Jogo da rodada', 'Casa', 'Fora', 'Primeiro gol (★)'].forEach(t => cabecalho.append(node('th', t)));
            const head = node('thead'); head.append(cabecalho); tabela.append(head);
            const body = node('tbody'); tabela.append(body);
            for (const [indice, item] of resultado.linhas.entries()) {
                const tr = node('tr');
                const usar = node('input'); usar.type = 'checkbox'; usar.checked = true; usar.setAttribute('aria-label', `Usar linha ${indice + 1}`);
                const celulaUsar = node('td'); celulaUsar.append(usar); tr.append(celulaUsar);
                const descricao = node('td'); descricao.append(node('p', item.texto));
                const avisos = node('p', '', 'text-accent'); descricao.append(avisos); tr.append(descricao);
                const select = node('select'); select.setAttribute('aria-label', `Jogo da linha ${indice + 1}`);
                const vazio = node('option', 'Selecione o jogo'); vazio.value = ''; select.append(vazio);
                for (const jogo of resultado.jogos) {
                    const option = node('option', jogo.nome); option.value = jogo.id; option.disabled = jogo.bloqueado; select.append(option);
                }
                select.value = item.jogo_id || '';
                const celulaJogo = node('td'); celulaJogo.append(select); tr.append(celulaJogo);
                const inputs = ['casa', 'fora'].map(lado => {
                    const input = node('input'); input.type = 'text'; input.inputMode = 'numeric'; input.value = item[lado]; input.style.width = '4rem';
                    input.setAttribute('aria-label', `${lado} da linha ${indice + 1}`);
                    const td = node('td'); td.append(input); tr.append(td); return input;
                });
                const primeiro = node('input'); primeiro.type = 'text'; primeiro.maxLength = 100; primeiro.value = item.primeiro_gol || '';
                primeiro.setAttribute('aria-label', `Primeiro gol da linha ${indice + 1}`);
                const tdPrimeiro = node('td'); tdPrimeiro.append(primeiro); tr.append(tdPrimeiro);
                body.append(tr);
                linhas.push({item, usar, select, inputs, primeiro, avisos, tr});
            }
            const atualizar = () => {
                const contagem = {};
                linhas.filter(l => l.usar.checked && l.select.value).forEach(l => contagem[l.select.value] = (contagem[l.select.value] || 0) + 1);
                let valido = true;
                for (const l of linhas) {
                    const jogo = resultado.jogos.find(j => String(j.id) === l.select.value);
                    const alertas = [...l.item.avisos, ...(jogo?.avisos || [])];
                    const bonusInvalido = l.primeiro.value.trim() && (!jogo?.primeiro_gol_permitido || l.primeiro.value.length > 100 || l.primeiro.value.includes('★'));
                    if (bonusInvalido) alertas.push('Primeiro gol: confira o jogador e se o jogo está cadastrado como clássico. Não será descartado automaticamente.');
                    if (l.usar.checked && (!jogo || jogo.bloqueado || bonusInvalido || contagem[l.select.value] > 1 || l.inputs.some(i => !/^[0-9]{1,10}$/.test(i.value) || Number(i.value)>2147483647))) {
                        valido = false; alertas.push('PENDENTE: escolha jogo único e placar válido, ou desmarque esta linha.');
                        l.tr.style.background = 'rgba(248,113,113,.12)';
                    } else l.tr.style.background = '';
                    l.avisos.textContent = alertas.join(' ');
                }
                aplicar.disabled = !valido || !linhas.some(l => l.usar.checked);
            };
            const scroll = node('div', '', 'table-scroll mt-3'); scroll.append(tabela); painel.append(scroll);
            const aplicar = node('button', 'Confirmar prévia e preencher formulário', 'ui-button mt-3'); aplicar.type = 'button'; painel.append(aplicar);
            linhas.forEach(l => [l.usar, l.select, l.primeiro, ...l.inputs].forEach(el => el.addEventListener('input', atualizar)));
            atualizar();
            aplicar.addEventListener('click', () => {
                atualizar();
                if (aplicar.disabled || atual !== geracao) return;
                const ids = [];
                for (const l of linhas.filter(l => l.usar.checked)) {
                    const id = l.select.value;
                    form.elements[`casa_${id}`].value = l.inputs[0].value;
                    form.elements[`fora_${id}`].value = l.inputs[1].value;
                    if (l.primeiro.value.trim()) {
                        form.elements[`primeiro_${id}`].value = l.primeiro.value.trim();
                        const toggle = document.getElementById('incluir-primeiro');
                        if (toggle.getAttribute('aria-expanded') !== 'true') toggle.click();
                    }
                    ids.push(id);
                }
                form.elements.whatsapp_token.value = resultado.token;
                form.elements.whatsapp_jogos.value = ids.join(',');
                status.textContent = 'Formulário preenchido. Nenhum palpite foi salvo. Revise abaixo e use Salvar e ficar ou Salvar e próximo participante.';
                aplicar.disabled = true;
            });
        } catch (erro) { status.textContent = erro.message; }
        finally { ler.disabled = false; }
    });
})();
