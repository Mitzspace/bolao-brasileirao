import json
from flask import render_template
from models import ClassificacaoCache
from database import db
from services.escudos import escudo_time, fonte_segura
from config_escudos import ESCUDOS_POR_API_ID, ESCUDOS_POR_NOME


def test_override_local_e_fallback_api(app):
    with app.test_request_context():
        d=escudo_time('CA Paranaense',1768,'https://crests.football-data.org/1768.png')
        assert d['fontes']==['/static/escudos/athletico-pr.png','https://crests.football-data.org/1768.png']
        for nome in ['Athletico-PR','Athletico Paranaense','Paranaense']:
            assert escudo_time(nome)['fontes'][0]=='/static/escudos/athletico-pr.png'


def test_arquivo_ausente_e_fontes_invalidas(app,monkeypatch):
    monkeypatch.setitem(ESCUDOS_POR_API_ID,1768,'escudos/nao-existe.png')
    monkeypatch.setitem(ESCUDOS_POR_NOME,'athletico pr','escudos/nao-existe.png')
    with app.test_request_context():
        assert escudo_time('Athletico-PR',1768,'https://example.com/crest.png')['fontes']==['https://example.com/crest.png']
        assert escudo_time('Time Novo')['iniciais']=='TN'
        assert fonte_segura('../.env') is None
        assert fonte_segura('javascript:alert(1)') is None


def test_cache_por_campeonato_e_reserva(app,campeonato_teste):
    db.session.add(ClassificacaoCache(campeonato_id=campeonato_teste.id,dados_json=json.dumps({'standings':[{'table':[{'team':{'id':1783,'name':'Clube Sem Escudo Local','shortName':'Sem Escudo','crest':'https://example.com/fla.png'}}]}]})))
    db.session.commit()
    with app.test_request_context():
        assert escudo_time('Sem Escudo',campeonato_id=campeonato_teste.id)['fontes']==['https://example.com/fla.png']
        assert escudo_time('Sem Escudo',campeonato_id=999)['fontes']==[]
        # Escudo local primeiro e o da API como reserva.
        fontes = escudo_time('Athletico-PR', 1768, 'https://example.com/antigo.png')['fontes']
        assert fontes[0] == '/static/escudos/athletico-pr.png' and 'https://example.com/antigo.png' in fontes


def test_todos_os_times_do_campeonato_tem_escudo_local(app):
    times = ['Athletico-PR', 'Atlético-MG', 'Bahia', 'Botafogo', 'Chapecoense', 'Corinthians', 'Coritiba',
             'Cruzeiro', 'Flamengo', 'Fluminense', 'Grêmio', 'Internacional', 'Mirassol', 'Palmeiras',
             'Red Bull Bragantino', 'Remo', 'Santos', 'São Paulo', 'Vasco', 'Vitória',
             'CR Flamengo', 'SE Palmeiras', 'Clube do Remo', 'EC Vitória', 'CA Mineiro']
    with app.test_request_context():
        for nome in times:
            fontes = escudo_time(nome)['fontes']
            assert fontes and fontes[0].startswith('/static/escudos/'), nome
