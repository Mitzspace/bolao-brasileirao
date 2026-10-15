from types import SimpleNamespace
import json
import pytest
from database import db
from models import Palpite, PalpiteLog
from services.parser_whatsapp import ler_mensagem
from tests.test_acesso_gestao import gestao, sessao


def jogos():
    return [SimpleNamespace(id=1,time_casa='Flamengo',time_fora='Vasco'),
            SimpleNamespace(id=2,time_casa='Atlético-MG',time_fora='Corinthians')]


@pytest.mark.parametrize('texto', ['Flamengo 2x1 Vasco','Flamengo 2 x 1 Vasco','2x1','2-1','2 a 1','2 - 1','1) 2x1','1 - Flamengo 2x1 Vasco','Flamengo FC 2x1 Vasco EC'])
def test_formatos(texto):
    item = ler_mensagem(texto,jogos())[0]
    assert (item['jogo_id'],item['casa'],item['fora']) == (1,'2','1')


def test_alias_ordem_repeticao_ambiguidade_e_desconhecido():
    assert ler_mensagem('Galo 12x10 Timão',jogos())[0]['jogo_id'] == 2
    assert ler_mensagem('2) 2-1',jogos())[0]['jogo_id'] == 2
    itens = ler_mensagem('2x1\nFlamengo 3x2 Vasco',jogos())
    assert all(any('repetido' in a for a in i['avisos']) for i in itens)
    assert 'ORDEM' in itens[0]['avisos'][0]
    assert any('Ambíguo' in a for a in ler_mensagem('Flamengo 1x0 Vasco',jogos()+[jogos()[0]])[0]['avisos'])
    assert ler_mensagem('qualquer texto',jogos())[0]['jogo_id'] is None
    assert ler_mensagem('Time desconhecido 2x1 Vasco',jogos())[0]['jogo_id'] is None
    assert ler_mensagem('2x1 e 3x2',jogos())[0]['jogo_id'] is None


def test_previa_nao_grava_e_texto_original_fica_no_log(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    client=app.test_client(); sessao(client,usuarios['responsavel'])
    dados={'participacaoId':pessoa,'rodadaId':rodada,'texto':'A 2x1 B'}
    resposta=client.post('/interface/api/palpites/previa-whatsapp',json=dados)
    assert resposta.status_code == 200
    assert Palpite.query.count() == PalpiteLog.query.count() == 0
    token=resposta.json['token']
    salvar={'participacaoId':pessoa,'rodadaId':rodada,'jogos':{str(jogo):{'casa':'2','fora':'1'}},
            'whatsappToken':token,'whatsappJogos':str(jogo)}
    assert client.post('/interface/api/palpites',json=salvar).status_code == 200
    assert json.loads(PalpiteLog.query.one().valores_novos)['texto_original_whatsapp'] == dados['texto']
    assert client.post('/interface/api/palpites',json=salvar).status_code == 200
    assert PalpiteLog.query.count() == 2  # Mesmo placar, nova mensagem auditada.
    assert json.loads(PalpiteLog.query.order_by(PalpiteLog.id.desc()).first().valores_anteriores)['gols_casa'] == 2
    salvar['whatsappToken']='adulterado'
    salvar['jogos'][str(jogo)]['casa']='4'
    assert client.post('/interface/api/palpites',json=salvar).status_code == 422
    assert Palpite.query.one().gols_casa == 2


def test_previa_exige_responsavel_e_limita_texto(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    client=app.test_client(); sessao(client,usuarios['responsavel'])
    dados={'participacaoId':pessoa,'rodadaId':rodada,'texto':'x'*20001}
    assert client.post('/interface/api/palpites/previa-whatsapp',json=dados).status_code == 422
    sessao(client,usuarios['comum'])
    assert client.post('/interface/api/palpites/previa-whatsapp',json=dados).status_code == 403
