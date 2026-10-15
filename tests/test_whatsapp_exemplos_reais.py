from types import SimpleNamespace
import json
import pytest
from database import db
from models import Jogo, Palpite, PalpiteLog, Rodada
from services.parser_whatsapp import ler_mensagem, rodadas_informadas
from tests.test_acesso_gestao import gestao, sessao

TIMES = [('Flamengo','Fluminense'),('Vasco','Remo'),('São Paulo','Vitória'),
         ('Palmeiras','Corinthians'),('Red Bull Bragantino','Cruzeiro'),
         ('Atlético-MG','Santos'),('Grêmio','Internacional'),('Coritiba','Botafogo'),
         ('Bahia','Mirassol'),('Chapecoense','Athletico-PR')]
PLACARES = [ ['2x0','3x0','2x0','2x1','1x3','2x0','2x0','1x2','3x0','0x3'],
             ['2 x 1','2 x 0','2 x 0','3 x 1','1 x 1','2 x 1','1 x 1','1 x 1','2 x 1','0 x 2'],
             ['1 x 1','1 x 0','2 x 1','3 x 2','1 x 2','2 x 1','2 x 1','1 x 0','3 x 1','1 x 2'] ]


def mensagem(indice):
    marcadores = {0:' ★Pedro' if indice == 0 else ' ★ Pedro',
                  3:' ★Flaco' if indice == 0 else ' ★ Vitor Roque',
                  6:' ★ Carlos Vinicius ' if indice == 0 else ' ★ Carlos Vinícius'}
    return '*Rodada-30*\n\n' + '\n'.join(f'{a} {PLACARES[indice][i]} {b}{marcadores.get(i, "")}' for i,(a,b) in enumerate(TIMES))


@pytest.mark.parametrize('indice', range(3))
def test_tres_mensagens_completas(indice):
    jogos=[SimpleNamespace(id=i+1,time_casa=a,time_fora=b) for i,(a,b) in enumerate(TIMES)]
    texto=mensagem(indice)
    linhas=ler_mensagem(texto,jogos)
    assert len(linhas)==10
    assert [l['jogo_id'] for l in linhas]==list(range(1,11))
    assert not any(l['avisos'] for l in linhas)
    assert [f"{l['casa']}x{l['fora']}" for l in linhas]==[p.replace(' ','') for p in PLACARES[indice]]
    assert linhas[0]['primeiro_gol']=='Pedro'
    assert linhas[3]['primeiro_gol']==('Flaco' if indice==0 else 'Vitor Roque')
    assert linhas[6]['primeiro_gol']==('Carlos Vinicius' if indice==0 else 'Carlos Vinícius')
    assert rodadas_informadas(texto)=={30}


def test_blocos_juntos_nao_misturam_participantes():
    jogos=[SimpleNamespace(id=i+1,time_casa=a,time_fora=b) for i,(a,b) in enumerate(TIMES)]
    linhas=ler_mensagem('\n\n'.join(mensagem(i) for i in range(3)),jogos)
    assert len(linhas)==30
    assert all(any('repetido' in a for a in l['avisos']) for l in linhas)


def test_cabecalho_divergente_e_primeiro_gol_auditado(gestao):
    app,usuarios,bolao,pessoa,rodada,jogo=gestao
    client=app.test_client(); sessao(client,usuarios['responsavel'])
    texto='*Rodada-30*\nA 2x0 B ★ Carlos Vinícius'
    dados={'texto':texto,'participacaoId':pessoa,'rodadaId':rodada}
    url='/interface/api/palpites/previa-whatsapp'
    assert client.post(url,json=dados).status_code==422
    assert Palpite.query.count()==0
    db.session.get(Rodada,rodada).nome='30ª Rodada'
    db.session.get(Jogo,jogo).especial=True
    db.session.commit()
    resposta=client.post(url,json=dados)
    assert resposta.status_code==200
    assert resposta.json['linhas'][0]['primeiro_gol']=='Carlos Vinícius'
    assert resposta.json['jogos'][0]['primeiro_gol_permitido']
    salvar={'participacaoId':pessoa,'rodadaId':rodada,'jogos':{str(jogo):{'casa':'2','fora':'0','primeiroGol':'Carlos Vinícius'}},
            'whatsappToken':resposta.json['token'],'whatsappJogos':str(jogo)}
    assert client.post('/interface/api/palpites',json=salvar).status_code==200
    assert Palpite.query.one().primeiro_gol=='Carlos Vinícius'
    assert json.loads(PalpiteLog.query.one().valores_novos)['texto_original_whatsapp']==texto
