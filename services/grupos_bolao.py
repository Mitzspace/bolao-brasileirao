"""Vários campeonatos no mesmo bolão.

Cada campeonato do bolão é um registro Bolao próprio, com seus jogos, rodadas,
palpites e classificação totalmente isolados (todas as regras existentes já
trabalham por bolão). Os campeonatos extras apontam para o bolão principal em
grupo_id; a interface mostra o grupo como um único bolão com vários campeonatos.
"""
from database import db
from models import Bolao, Campeonato, Participacao
from services.gestao_campeonato import validar_campeonato


def campeonatos_do_grupo(bolao, permitidos):
    """Bolões do mesmo grupo que o usuário pode gerenciar, do mais antigo ao mais novo."""
    raiz = bolao.grupo_raiz_id
    return sorted((b for b in permitidos if b.grupo_raiz_id == raiz), key=lambda b: (b.grupo_id is not None, b.id))


def criar_campeonato_no_grupo(bolao, nome, ano, codigo_api, usuario):
    """Cria o campeonato e o bolão irmão, copiando participantes e responsáveis ativos.

    Os palpites, jogos e créditos não são copiados: o novo campeonato começa zerado.
    """
    nome, ano, codigo_api = validar_campeonato(nome, ano, codigo_api or 'BSA')
    principal = db.session.get(Bolao, bolao.grupo_raiz_id)
    campeonato = Campeonato(nome=nome, ano=ano, codigo_api=codigo_api)
    novo = Bolao(nome=principal.nome, campeonato=campeonato, criador=usuario, grupo_id=principal.id,
                 permite_palpite_proprio=bolao.permite_palpite_proprio,
                 permite_lancamento_por_responsavel=bolao.permite_lancamento_por_responsavel,
                 pontua_desde_entrada=bolao.pontua_desde_entrada,
                 politica_entrada_tardia=bolao.politica_entrada_tardia)
    db.session.add(novo)
    copiados = 0
    for pessoa in Participacao.query.filter_by(bolao_id=bolao.id, status='ativo').order_by(Participacao.id).all():
        db.session.add(Participacao(bolao=novo, usuario_id=pessoa.usuario_id, nome_exibicao=pessoa.nome_exibicao,
                                    email=pessoa.email, papel=pessoa.papel, status='ativo'))
        copiados += 1
    if not any(p.usuario_id == usuario.id for p in novo.participacoes):
        db.session.add(Participacao(bolao=novo, usuario=usuario, nome_exibicao=usuario.nome,
                                    papel='responsavel', status='ativo'))
    db.session.commit()
    return novo, copiados
