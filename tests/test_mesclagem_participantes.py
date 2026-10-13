import json
import pytest
from sqlalchemy import text
from database import db
from models import Participacao, ParticipacaoLog, Palpite, Participante
from services.mesclagem_participantes import mesclar_sem_palpites
from tests.test_acesso_gestao import gestao


def test_mescla_vinculo_papel_logs_sem_alterar_palpites(gestao):
    destino = db.session.get(Participacao, gestao[3])
    conta = Participante(nome='Albert', email='albert@example.com')
    db.session.add(conta)
    db.session.flush()
    origem = Participacao(bolao_id=destino.bolao_id, nome_exibicao='Albert(admin)',
        usuario_id=conta.id, papel='responsavel', observacao='Anotação original')
    db.session.add(origem)
    db.session.add(Palpite(participacao=destino, jogo_id=gestao[5], gols_casa=2, gols_fora=1))
    db.session.commit()
    origem_id, destino_id = origem.id, destino.id
    logs_antes = [(l.id, l.valores_novos) for l in origem.logs]
    mesclar_sem_palpites(db.session.connection(), origem_id, destino_id, 'Albert')
    db.session.commit()
    db.session.expire_all()
    assert db.session.get(Participacao, origem_id) is None
    assert destino.usuario_id == conta.id and destino.papel == 'responsavel'
    assert destino.nome_exibicao == 'Albert' and destino.observacao == 'Anotação original'
    assert len(destino.palpites) == 1 and destino.palpites[0].gols_casa == 2
    for id, conteudo in logs_antes:
        log = db.session.get(ParticipacaoLog, id)
        assert log.participacao_id == destino_id and log.valores_novos == conteudo
    log = ParticipacaoLog.query.filter_by(acao='mesclagem').one()
    assert json.loads(log.valores_anteriores)['origem']['id'] == origem_id


@pytest.mark.parametrize('conflito', ['status', 'palpite'])
def test_conflitos_recusados_sem_mutacao(gestao, conflito):
    destino = db.session.get(Participacao, gestao[3])
    origem = Participacao(bolao_id=destino.bolao_id, nome_exibicao='Albert duplicado')
    db.session.add(origem)
    db.session.flush()
    if conflito == 'status':
        origem.status = 'removido'
    else:
        db.session.add(Palpite(participacao=origem, jogo_id=gestao[5], gols_casa=0, gols_fora=0))
    db.session.commit()
    antes = db.session.execute(text('SELECT count(*) FROM participacao_log')).scalar()
    with pytest.raises(ValueError):
        mesclar_sem_palpites(db.session.connection(), origem.id, destino.id, 'Albert')
    assert db.session.execute(text('SELECT count(*) FROM participacao_log')).scalar() == antes
    assert db.session.get(Participacao, origem.id) is origem
