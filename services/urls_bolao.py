"""URLs por bolão com os mesmos endpoints e compatibilidade dos formulários antigos."""
from flask import current_app, g, redirect, request, url_for
from urllib.parse import urlencode


def registrar_urls_bolao(app):
    for regra in list(app.url_map.iter_rules()):
        endpoint = regra.endpoint
        if endpoint.startswith('admin.'):
            sufixo = regra.rule.removeprefix('/admin')
            if endpoint == 'admin.dashboard':
                sufixo = '/gestao'
            elif endpoint == 'admin.responsaveis':
                sufixo = '/configuracoes'
        elif endpoint.startswith('participante.') and endpoint not in {
                'participante.escolher_bolao', 'participante.selecionar_bolao', 'participante.criar_bolao'}:
            sufixo = regra.rule
        else:
            continue
        app.add_url_rule('/b/<int:bolao_path_id>' + sufixo, endpoint=endpoint,
                         view_func=app.view_functions[endpoint], methods=regra.methods)

    @app.url_value_preprocessor
    def ler_bolao_da_url(endpoint, values):
        g.bolao_path_id = values.pop('bolao_path_id', None) if values else None


def redirecionar_url_antiga():
    if current_app.config['FEATURE_PARTICIPANTE_LOGIN'] or getattr(g, 'bolao_path_id', None):
        return
    from services.contexto_bolao import bolao_atual, rota_depende_de_bolao
    if not bolao_atual() or not rota_depende_de_bolao():
        return
    valores = dict(request.view_args or {})
    valores['bolao_id'] = bolao_atual().id
    destino = url_for(request.endpoint, **valores)
    parametros = [(k, v) for k, v in request.args.items(multi=True) if k != 'bolao_id']
    if parametros:
        destino += '?' + urlencode(parametros)
    # 307 mantém método e corpo dos POSTs antigos, sem gravar duas vezes.
    return redirect(destino, code=302 if request.method in {'GET', 'HEAD'} else 307)
