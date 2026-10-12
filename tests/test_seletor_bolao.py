from datetime import datetime, timedelta
from flask import g
from database import db
from models import Bolao, Campeonato, Jogo, Participacao, Participante, Palpite, Resultado, Rodada
from tests.test_ranking_privacidade import contextos


def login(client, usuario):
    with client.session_transaction() as sess:
        sess['_user_id']=str(usuario.id)
        sess['_fresh']=True
    g.pop('_login_user',None)


def estrutura(usuario, campeonato, nome):
    b=Bolao(nome=nome, campeonato=campeonato, criador=usuario)
    p=Participacao(bolao=b, usuario=usuario, nome_exibicao=nome+' pessoa',papel='responsavel')
    db.session.add_all([b,p]);db.session.commit()
    return b,p


def test_meus_palpites_ordena_1_2_9_10(client, participante_teste, campeonato_teste):
    b,p=estrutura(participante_teste,campeonato_teste,'Amigos')
    for n in [10,9,2,1]:
        r=Rodada(nome=f'{n}ª Rodada',campeonato=campeonato_teste)
        j=Jogo(time_casa='A',time_fora='B',rodada=r)
        db.session.add(j);db.session.flush()
        db.session.add(Palpite(participacao=p,jogo=j,gols_casa=1,gols_fora=0))
    db.session.commit();login(client,participante_teste)
    ctx=contextos(client.application,client,'/meus-palpites')
    assert [r.nome for r, _ in ctx['opcoes_rodadas']]==['1ª Rodada','2ª Rodada','9ª Rodada','10ª Rodada']
    assert [i['palpite'].jogo.rodada.nome for i in ctx['itens']]==['1ª Rodada']


def test_dois_boloes_mesmo_campeonato_separam_palpites_ranking_grade(client, participante_teste, jogo_teste):
    a,pa=estrutura(participante_teste,jogo_teste.rodada.campeonato,'Brasileirão 2026')
    b,pb=estrutura(participante_teste,jogo_teste.rodada.campeonato,'Brasileirão 2026')
    jogo_teste.data=datetime.now()-timedelta(days=1)
    db.session.add_all([Resultado(jogo=jogo_teste,gols_casa_real=1,gols_fora_real=0),
        Palpite(participacao=pa,jogo=jogo_teste,gols_casa=1,gols_fora=0),
        Palpite(participacao=pb,jogo=jogo_teste,gols_casa=0,gols_fora=2)])
    db.session.commit();login(client,participante_teste)
    for bolao,part,pontos in [(a,pa,3),(b,pb,0),(a,pa,3)]:
        assert client.post('/boloes/selecionar',data={'bolao_id':bolao.id}).status_code==302
        ctx=contextos(client.application,client,'/meus-palpites')
        assert [i['palpite'].participacao_id for i in ctx['itens']]==[part.id]
        rank=contextos(client.application,client,'/ranking')['ranking']
        assert len(rank)==1 and rank[0]['pontos']==pontos
        grade=contextos(client.application,client,f'/rodada/{jogo_teste.rodada_id}/palpites')
        assert [p.id for p in grade['participantes']]==[part.id]
        admin=contextos(client.application,client,f'/admin/palpites?participante_id={part.id}&rodada_id={jogo_teste.rodada_id}')
        assert admin['palpites_map'][jogo_teste.id].participacao_id==part.id
    assert a.chave!=b.chave
    client.post('/admin/palpites',data={'participante_id':pa.id,'rodada_id':jogo_teste.rodada_id,
        f'casa_{jogo_teste.id}':'4',f'fora_{jogo_teste.id}':'0'})
    assert Palpite.query.filter_by(participacao_id=pa.id).one().gols_casa==4
    assert Palpite.query.filter_by(participacao_id=pb.id).one().gols_casa==0
    html=client.get('/').get_data(as_text=True)
    assert a.chave in html and b.chave in html and a.codigo_convite not in html


def test_seletor_recusa_bolao_alheio_e_rodada_outro_campeonato(client, participante_teste, campeonato_teste):
    a,pa=estrutura(participante_teste,campeonato_teste,'Meu')
    outro=Participante(nome='Outro',email='outro@example.com')
    c=Campeonato(nome='Champions',codigo_api='CL',ano=2026)
    db.session.add_all([outro,c]);db.session.commit()
    b,pb=estrutura(outro,c,'Privado')
    r=Rodada(nome='Rodada 1',campeonato=c);db.session.add(r);db.session.commit()
    login(client,participante_teste)
    assert client.post('/boloes/selecionar',data={'bolao_id':b.id}).status_code==403
    assert client.get(f'/jogos/{r.id}').status_code==404
    assert client.get(f'/rodada/{r.id}/palpites').status_code==404
    assert client.get(f'/tabela?campeonato_id={c.id}').status_code==404
    assert 'Privado' not in client.get('/').get_data(as_text=True)


def test_troca_para_outro_campeonato_e_formulario_antigo(client, participante_teste, campeonato_teste):
    a,pa=estrutura(participante_teste,campeonato_teste,'Brasileirão')
    c=Campeonato(nome='Champions',codigo_api='CL',ano=2026)
    db.session.add(c);db.session.commit()
    b,pb=estrutura(participante_teste,c,'Champions dos amigos')
    r=Rodada(nome='Rodada 1',campeonato=c,aberta=True);db.session.add(r);db.session.commit()
    login(client,participante_teste)
    client.post('/boloes/selecionar',data={'bolao_id':b.id})
    ctx=contextos(client.application,client,'/jogos')
    assert ctx['camp_atual'].id==c.id
    assert client.post(f'/rodada/{r.id}',data={'bolao_id':a.id}).status_code==403
