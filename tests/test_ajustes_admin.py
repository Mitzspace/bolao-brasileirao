"""Ajustes do perfil de administrador: lembrar login e bolão, log com origem, gaveta e aviso do WhatsApp."""
import json
import re

from flask import g

from database import db
from models import Jogo, Palpite, PalpiteLog, Participacao
from services import cache_publico
from services.contexto_bolao import COOKIE_ULTIMO_BOLAO
from tests.test_api_palpites import preparar
from tests.test_interface import entrar, gestao  # noqa: F401


def _cookie(client, nome):
    return client.get_cookie(nome)


def _salvar(client, pessoa, rodada, jogos, **extra):
    return client.post('/interface/api/palpites', json={
        'participacaoId': pessoa.id, 'rodadaId': rodada.id, 'jogos': jogos, **extra})


# ---------- Manter conectado e último bolão ----------

def test_manter_conectado_grava_cookie_de_login_lembrado(client, gestao):
    usuario, _ = gestao
    g.pop('_login_user', None)
    client.post('/login', data={'email': usuario.email, 'senha': '123456', 'lembrar': '1'})
    assert _cookie(client, 'remember_token') is not None
    client.get('/logout')
    assert _cookie(client, 'remember_token') is None


def test_sem_manter_conectado_nao_grava_cookie_de_login(client, gestao):
    usuario, _ = gestao
    g.pop('_login_user', None)
    client.post('/login', data={'email': usuario.email, 'senha': '123456'})
    assert _cookie(client, 'remember_token') is None


def test_ultimo_bolao_volta_depois_de_sair_e_entrar(client, app, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    assert client.get('/interface/api/dashboard').status_code == 409  # dois bolões, nada escolhido
    client.post('/interface/selecionar', data={'bolao_id': boloes[1].id})
    assert _cookie(client, COOKIE_ULTIMO_BOLAO) is not None
    # Sessão perdida (outro navegador com o mesmo cookie, sessão expirada): volta ao último bolão.
    cookie = _cookie(client, COOKIE_ULTIMO_BOLAO).value
    novo = app.test_client()
    novo.set_cookie(COOKIE_ULTIMO_BOLAO, cookie)
    entrar(novo, usuario)
    assert novo.get('/interface/api/dashboard').get_json()['bolao']['id'] == boloes[1].id


def test_cookie_de_ultimo_bolao_adulterado_ou_de_outra_conta_e_ignorado(client, app, gestao):
    from models import Participante
    usuario, boloes = gestao
    outro = Participante.query.filter_by(email='outro@example.com').one()
    entrar(client, outro)
    client.post('/interface/selecionar', data={'bolao_id': boloes[2].id})
    cookie_outro = _cookie(client, COOKIE_ULTIMO_BOLAO).value
    for valor in (cookie_outro, 'lixo-adulterado', cookie_outro[:-2] + 'xx'):
        novo = app.test_client()
        novo.set_cookie(COOKIE_ULTIMO_BOLAO, valor)
        entrar(novo, usuario)
        assert novo.get('/interface/api/dashboard').status_code == 409, valor


def test_em_outro_aparelho_usa_o_bolao_do_ultimo_lancamento(client, app, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    assert _salvar(client, bia, r1, {str(j1.id): {'casa': '1', 'fora': '1'}}).status_code == 200
    novo = app.test_client()  # sem sessão e sem cookie
    entrar(novo, gestao[0])
    assert novo.get('/interface/api/dashboard').get_json()['bolao']['id'] == bolao.id


# ---------- Log com origem e gaveta ----------

def test_cada_lancamento_gera_log_com_autor_data_origem_e_antes_depois(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    antes = PalpiteLog.query.count()
    _salvar(client, ana, r1, {str(j1.id): {'casa': '3', 'fora': '2'}, str(j2.id): {'casa': '0', 'fora': '0'}})
    logs = PalpiteLog.query.order_by(PalpiteLog.id).all()[antes:]
    assert len(logs) == 2
    for log in logs:
        assert log.alterado_por == gestao[0].id and log.alterado_em is not None
        assert json.loads(log.valores_novos)['canal'] == 'painel'
    edicao = next(l for l in logs if l.acao == 'alteracao')
    assert json.loads(edicao.valores_anteriores)['gols_casa'] == 1 and json.loads(edicao.valores_novos)['gols_casa'] == 3
    # Salvar de novo sem mudar nada não cria log.
    _salvar(client, ana, r1, {str(j1.id): {'casa': '3', 'fora': '2'}})
    assert PalpiteLog.query.count() == antes + 2


def test_gaveta_mostra_alteracoes_mais_recentes_primeiro(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    _salvar(client, ana, r1, {str(j1.id): {'casa': '3', 'fora': '2'}})
    _salvar(client, ana, r1, {str(j2.id): {'casa': '0', 'fora': '1'}})
    itens = client.get(f'/interface/api/palpites/historico?participacao_id={ana.id}').get_json()['itens']
    assert [i['mudancas'][0]['jogo'] for i in itens] == ['Santos × Bahia', 'Flamengo × Vasco', 'Flamengo × Vasco']
    recente, edicao, original = itens
    assert recente['autor'] == 'Responsável' and recente['canal'] == 'painel' and recente['acao'] == 'Lançou'
    assert re.fullmatch(r'\d\d/\d\d/\d{4} às \d\d:\d\d', recente['quandoTexto'])
    assert edicao['mudancas'][0] == {'jogo': 'Flamengo × Vasco', 'antes': '1 × 0', 'depois': '3 × 2', 'detalhes': []}
    # Palpite gravado sem usuário (importação/script): origem desconhecida.
    assert original['autor'] is None and original['canal'] == 'desconhecida'


def test_gaveta_de_palpite_antigo_sem_nenhum_log(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    palpite = Palpite.query.filter_by(participacao_id=ana.id).one()
    # Simula um palpite de antes do log (sem nenhum registro no histórico).
    db.session.connection().execute(PalpiteLog.__table__.delete().where(PalpiteLog.palpite_id == palpite.id))
    db.session.commit()
    itens = client.get(f'/interface/api/palpites/historico?participacao_id={ana.id}').get_json()['itens']
    assert len(itens) == 1 and itens[0]['canal'] == 'desconhecida' and itens[0]['autor'] is None
    assert itens[0]['mudancas'][0]['depois'] == '1 × 0'


def test_gaveta_so_do_bolao_atual_e_so_para_gestao(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    dono_privado = Participacao.query.filter_by(bolao_id=gestao[1][2].id).first()
    assert client.get(f'/interface/api/palpites/historico?participacao_id={dono_privado.id}').status_code == 404
    client.get('/logout')
    assert client.get(f'/interface/api/palpites/historico?participacao_id={ana.id}').status_code == 401


def _lancar_pelo_whatsapp(client, pessoa, rodada, j1, j2):
    previa = client.post('/interface/api/palpites/previa-whatsapp', json={
        'participacaoId': pessoa.id, 'rodadaId': rodada.id, 'texto': 'Flamengo 2 x 0 Vasco\nSantos 1 x 1 Bahia'}).get_json()
    reconhecidos = [l['jogo_id'] for l in previa['linhas'] if l['jogo_id']]
    assert set(reconhecidos) == {j1.id, j2.id}
    return _salvar(client, pessoa, rodada, {str(j1.id): {'casa': '2', 'fora': '0'}, str(j2.id): {'casa': '1', 'fora': '1'}},
                   whatsappToken=previa['token'], whatsappJogos=','.join(map(str, reconhecidos)))


def test_lancamento_pelo_whatsapp_tem_origem_aviso_e_texto_na_gaveta(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    tela = client.get(f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={bia.id}').get_json()
    assert tela['pessoa']['whatsapp'] is None
    assert _lancar_pelo_whatsapp(client, bia, r1, j1, j2).status_code == 200
    tela = client.get(f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={bia.id}').get_json()
    aviso = tela['pessoa']['whatsapp']
    assert aviso['rodada'] == 'Rodada 1' and re.fullmatch(r'\d\d/\d\d às \d\d:\d\d', aviso['quandoTexto'])
    assert aviso['autor'] == 'Responsável'  # quem colou a mensagem e salvou
    itens = client.get(f'/interface/api/palpites/historico?participacao_id={bia.id}').get_json()['itens']
    assert len(itens) == 1 and itens[0]['canal'] == 'whatsapp' and len(itens[0]['mudancas']) == 2
    assert 'Flamengo 2 x 0 Vasco' in itens[0]['textoWhatsapp']
    # Uma correção posterior pela tela fica registrada como painel; o aviso do WhatsApp continua.
    _salvar(client, bia, r1, {str(j1.id): {'casa': '3', 'fora': '0'}})
    itens = client.get(f'/interface/api/palpites/historico?participacao_id={bia.id}').get_json()['itens']
    assert [i['canal'] for i in itens] == ['painel', 'whatsapp']
    assert itens[0]['mudancas'][0]['antes'] == '2 × 0' and itens[0]['mudancas'][0]['depois'] == '3 × 0'


def test_palpites_completos_abrem_fechados(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    url = f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={ana.id}'
    assert client.get(url).get_json()['pessoa']['completo'] is False  # Ana tem 1 de 2
    _salvar(client, ana, r1, {str(j2.id): {'casa': '1', 'fora': '0'}})
    assert client.get(url).get_json()['pessoa']['completo'] is True


def test_log_e_gaveta_nao_aparecem_no_link_publico(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    _lancar_pelo_whatsapp(client, bia, r1, j1, j2)
    link = client.post(f'/interface/api/boloes/{bolao.id}/publico/link', json={'acao': 'gerar'}).get_json()['link']
    client.put(f'/interface/api/boloes/{bolao.id}/publico/tabela', json={'rodadaId': r1.id})
    client.get('/logout')
    cache_publico.invalidar()
    base = '/publico/' + link.rsplit('/', 1)[1]
    assert client.get(base + '/api/palpites/historico').status_code == 404
    for rota in ('/api/inicio', '/api/palpites?rodada=1', '/api/participantes', '/api/classificacao'):
        texto = client.get(base + rota).get_data(as_text=True)
        for proibido in ('canal', 'whatsapp', 'WhatsApp', 'Flamengo 2 x 0', 'alterado', 'autor', 'historico'):
            assert proibido not in texto, (rota, proibido)


def test_cards_de_boloes_contam_pessoas_com_jogo_em_branco(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    card = next(b for b in client.get('/interface/api/boloes').get_json()['boloes'] if b['id'] == bolao.id)
    painel = client.get('/interface/api/dashboard').get_json()
    assert card['palpitesFaltantes'] == painel['palpitesFaltantes'] == len(painel['pendentes'])
