document.querySelectorAll('[data-painel-copia]').forEach((painel) => {
    const botao = painel.querySelector('[data-copiar-texto]');
    const texto = painel.querySelector('[data-texto-copia]');
    const status = painel.querySelector('[data-status-copia]');
    botao.addEventListener('click', async () => {
        try {
            if (!navigator.clipboard || !window.isSecureContext) throw new Error('Cópia manual');
            await navigator.clipboard.writeText(texto.value);
            status.textContent = 'Copiado! Cole no WhatsApp.';
        } catch {
            painel.querySelector('[data-previa-copia]').open = true;
            texto.focus();
            texto.select();
            texto.setSelectionRange(0, texto.value.length);
            status.textContent = 'Texto selecionado. Use Copiar no celular ou Ctrl+C no computador.';
        }
    });
});
