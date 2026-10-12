(() => {
    const form = document.querySelector('[data-lancamento]');
    if (!form) return;
    const fields = [...form.querySelectorAll('[data-gols]:not(:disabled)')];
    const automatico = document.getElementById('avanco-automatico');
    const focus = index => {
        if (!fields[index]) return;
        fields[index].focus();
        fields[index].select();
    };
    fields.forEach((input, index) => {
        input.addEventListener('input', event => {
            if (automatico.checked && !event.isComposing && /^[0-9]$/.test(input.value)
                && event.inputType !== 'deleteContentBackward') focus(index + 1);
        });
        input.addEventListener('keydown', event => {
            if (event.key === 'Backspace' && input.value === '') {
                event.preventDefault();
                focus(index - 1);
            }
        });
    });
    form.addEventListener('keydown', event => {
        if (event.key === 'Enter' && event.target.matches('input:not([type=checkbox])')) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
    const toggle = document.getElementById('incluir-primeiro');
    toggle.addEventListener('click', () => {
        const abrir = toggle.getAttribute('aria-expanded') !== 'true';
        toggle.setAttribute('aria-expanded', String(abrir));
        form.querySelectorAll('[data-primeiro]').forEach(el => el.hidden = !abrir);
        toggle.textContent = abrir ? 'Ocultar primeiro gol' : 'Incluir primeiro gol';
    });
    const erro = form.querySelector('[aria-invalid=true]');
    if (erro) erro.focus();
    else focus(fields.findIndex(input => input.value === ''));
})();
