from datetime import datetime

from database import db
from flask_login import UserMixin
import secrets
from sqlalchemy.orm import synonym
from sqlalchemy import false


def agora_utc():
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def gerar_codigo():
    return secrets.token_urlsafe(32)


class Participante(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200))
    admin = db.Column(db.Boolean, default=False, nullable=False)
    admin_global = db.Column(db.Boolean, default=False, nullable=False)
    conta_ativa = db.Column(db.Boolean, default=True, nullable=False)

    palpites = db.relationship("Palpite", backref="participante", lazy=True,
                               foreign_keys="Palpite.participante_id")

    @property
    def is_active(self):
        return self.conta_ativa


# Mantém tabela, IDs, hashes e imports antigos durante a transição.
Usuario = Participante


class Bolao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    campeonato_id = db.Column(db.Integer, db.ForeignKey("campeonato.id"), nullable=False)
    criador_id = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=False)
    codigo_convite = db.Column(db.String(100), unique=True, nullable=True, default=gerar_codigo)
    permite_palpite_proprio = db.Column(db.Boolean, nullable=False, default=False)
    permite_lancamento_por_responsavel = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(20), nullable=False, default="ativo")
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc)
    pontua_desde_entrada = db.Column(db.Boolean, nullable=False, default=True)
    politica_entrada_tardia = db.Column(db.String(20), nullable=False,
        default="fora_da_conta", server_default="fora_da_conta")
    # Vários campeonatos no mesmo bolão: cada campeonato é um Bolao próprio (jogos,
    # palpites e classificação isolados) ligado ao bolão principal por grupo_id.
    grupo_id = db.Column(db.Integer, db.ForeignKey("bolao.id"), nullable=True)
    # Regras de pontuação do bolão (valem para todas as rodadas, inclusive as já jogadas).
    pontos_comum_exato = db.Column(db.Integer, nullable=False, default=3, server_default="3")
    pontos_comum_resultado = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    pontos_classico_exato = db.Column(db.Integer, nullable=False, default=5, server_default="5")
    pontos_classico_resultado = db.Column(db.Integer, nullable=False, default=3, server_default="3")
    pontos_primeiro_gol = db.Column(db.Integer, nullable=False, default=2, server_default="2")
    # Disputa de pênaltis: palpite próprio do placar dos pênaltis.
    pontos_penaltis_exato = db.Column(db.Integer, nullable=False, default=3, server_default="3")
    pontos_penaltis_vencedor = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    # Link público de consulta (somente leitura, sem login). Vazio = link desligado.
    codigo_publico = db.Column(db.String(64), unique=True, nullable=True)
    # Classificação pública liberada até esta rodada (inclusive). Vazio = oculta.
    rodada_publica_id = db.Column(db.Integer, db.ForeignKey("rodada.id"), nullable=True)
    # Corte por fase: quem fica fora dos classificados sai do ranking.
    eliminacao_participantes = db.Column(db.Boolean, nullable=False, default=False, server_default=false())
    __table_args__ = (db.CheckConstraint(
        "politica_entrada_tardia IN ('zero', 'fora_da_conta')", name="bolao_entrada_tardia"),)
    campeonato = db.relationship("Campeonato", backref="boloes")
    criador = db.relationship("Participante")
    rodada_publica = db.relationship("Rodada", foreign_keys=[rodada_publica_id])

    @property
    def grupo_raiz_id(self):
        """Id do bolão principal do grupo (o próprio id quando não há grupo)."""
        return self.grupo_id or self.id

    @property
    def chave(self):
        """Identificação pública estável; não concede acesso nem substitui convite."""
        return f"BOL-{self.id:06d}"


class CorteEliminacao(db.Model):
    """Após a rodada indicada, só os `classificados` melhores seguem no bolão."""
    __tablename__ = "corte_eliminacao"

    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey("bolao.id"), nullable=False)
    rodada_id = db.Column(db.Integer, db.ForeignKey("rodada.id"), nullable=False)
    classificados = db.Column(db.Integer, nullable=False)
    bolao = db.relationship("Bolao", backref="cortes_eliminacao")
    rodada = db.relationship("Rodada")
    __table_args__ = (
        db.UniqueConstraint("bolao_id", "rodada_id", name="unique_corte_bolao_rodada"),
        db.CheckConstraint("classificados > 0", name="corte_classificados"),
    )


class Participacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bolao_id = db.Column(db.Integer, db.ForeignKey("bolao.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    # Identidade original para compatibilidade; não representa uma conta vinculada.
    participante_legado_id = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    papel = db.Column(db.String(20), nullable=False, default="participante")
    status = db.Column(db.String(20), nullable=False, default="ativo")
    entrou_em = db.Column(db.DateTime, nullable=True, default=agora_utc)
    entrada_legada = db.Column(db.Boolean, nullable=False, default=False)
    pontua_desde = db.Column(db.DateTime, nullable=True, default=agora_utc)
    saiu_em = db.Column(db.DateTime, nullable=True)
    rodada_entrada_id = db.Column(db.Integer, db.ForeignKey("rodada.id"), nullable=True)
    rodada_desistencia_id = db.Column(db.Integer, db.ForeignKey("rodada.id"), nullable=True)
    motivo_desistencia = db.Column(db.Text, nullable=True)
    desistencia_registrada_em = db.Column(db.DateTime, nullable=True)
    desistencia_registrada_por = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    rodada_entrada = db.relationship("Rodada", foreign_keys=[rodada_entrada_id])
    rodada_desistencia = db.relationship("Rodada", foreign_keys=[rodada_desistencia_id])
    autor_desistencia = db.relationship("Participante", foreign_keys=[desistencia_registrada_por])
    codigo_vinculo = db.Column(db.String(100), unique=True, nullable=True)
    bolao = db.relationship("Bolao", backref="participacoes")
    usuario = db.relationship("Participante", foreign_keys=[usuario_id], backref="participacoes")
    participante_legado = db.relationship("Participante", foreign_keys=[participante_legado_id])

    @property
    def nome(self):
        return self.nome_exibicao

    @property
    def admin(self):
        return self.papel == 'responsavel'
    __table_args__ = (
        db.UniqueConstraint("bolao_id", "usuario_id", name="unique_usuario_bolao"),
        db.UniqueConstraint("bolao_id", "participante_legado_id", name="unique_legado_bolao"),
        db.CheckConstraint("papel IN ('responsavel', 'participante')", name="participacao_papel"),
        db.CheckConstraint("status IN ('ativo', 'saiu', 'removido', 'desistente')", name="participacao_status"),
    )


class ParticipacaoLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participacao_id = db.Column(db.Integer, db.ForeignKey("participacao.id"), nullable=False, index=True)
    alterado_por = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    alterado_em = db.Column(db.DateTime, nullable=False, default=agora_utc)
    acao = db.Column(db.String(32), nullable=False)
    valores_anteriores = db.Column(db.Text, nullable=True)
    valores_novos = db.Column(db.Text, nullable=False)
    participacao = db.relationship("Participacao", backref="logs")
    autor = db.relationship("Participante")


class Campeonato(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer)
    codigo_api = db.Column(db.String(40), default="BSA", nullable=True)
    # Provedor: football-data (BSA…), api-football (id numérico) ou espn (slug, ex.: conmebol.libertadores).
    fonte_api = db.Column(db.String(20), nullable=False, default="football-data", server_default="football-data")

    rodadas = db.relationship("Rodada", backref="campeonato", lazy=True)


class ClassificacaoCache(db.Model):
    __tablename__ = "classificacao_cache"

    id = db.Column(db.Integer, primary_key=True)
    campeonato_id = db.Column(
        db.Integer, db.ForeignKey("campeonato.id"), nullable=False, unique=True
    )
    dados_json = db.Column(db.Text, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    campeonato = db.relationship(
        "Campeonato",
        backref=db.backref("classificacao_cache", uselist=False, cascade="all, delete-orphan"),
    )


class Rodada(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    aberta = db.Column(db.Boolean, default=True)
    campeonato_id = db.Column(
        db.Integer, db.ForeignKey("campeonato.id"), nullable=False, index=True
    )

    # Ordem fixa: jogos com posição da planilha primeiro (na ordem da planilha);
    # os demais (vindos da API ou cadastrados à mão) por data e horário.
    jogos = db.relationship("Jogo", backref="rodada", lazy=True, order_by=lambda: ordem_dos_jogos())


def ordem_dos_jogos():
    """Posição da planilha; sem posição, data e horário (sem horário por último); depois id."""
    return (Jogo.ordem.is_(None), Jogo.ordem, Jogo.data.is_(None), Jogo.data, Jogo.id)


class Jogo(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    time_casa = db.Column(db.String(100), nullable=False)
    time_fora = db.Column(db.String(100), nullable=False)
    classico = db.Column(db.Boolean, default=False, nullable=False)
    especial = synonym("classico")
    _especial_legado = db.Column("especial", db.Boolean, default=False)
    primeiro_marcador = db.Column(db.String(100), nullable=True)
    encerrado = db.Column(db.Boolean, default=False, nullable=False)
    data = db.Column(db.DateTime)
    external_fonte = db.Column(db.String(50))
    external_id = db.Column(db.String(100))
    # Posição do jogo na aba da planilha importada (nula para jogos da API).
    ordem = db.Column(db.Integer, nullable=True)
    # Jogo de mata-mata que pode ser decidido nos pênaltis (jogo único ou volta).
    pode_penaltis = db.Column(db.Boolean, nullable=False, default=False, server_default=false())
    rodada_id = db.Column(
        db.Integer, db.ForeignKey("rodada.id"), nullable=False, index=True
    )

    resultado = db.relationship("Resultado", backref="jogo", uselist=False)
    palpites = db.relationship("Palpite", backref="jogo", lazy=True)

    def bloqueado(self):
        """Palpite bloqueado se encerrado manualmente OU se a data já passou."""
        if self.encerrado:
            return True
        if self.data is None:
            return False
        from services.relogio import agora_brasilia
        return agora_brasilia() >= self.data

    @property
    def data_formatada(self):
        """Retorna a data e hora formatadas do jogo."""
        if self.data:
            return self.data.strftime("%d/%m/%Y às %H:%M")
        if self.encerrado:
            return "Partida finalizada"
        return "Horário a definir"


class Palpite(db.Model):

    situacao = db.Column(db.String(20), nullable=False, default="valido", server_default="valido")

    @property
    def situacao_label(self):
        return {"valido": "Válido", "nao_enviado": "Não enviou palpite", "fora_prazo": "Fora do prazo"}.get(self.situacao, "Válido")


    id = db.Column(db.Integer, primary_key=True)
    gols_casa = db.Column(db.Integer, nullable=False)
    gols_fora = db.Column(db.Integer, nullable=False)
    # Placar previsto da disputa de pênaltis (só em jogos com pode_penaltis).
    penaltis_casa = db.Column(db.Integer, nullable=True)
    penaltis_fora = db.Column(db.Integer, nullable=True)
    jogador_primeiro_gol = db.Column("primeiro_gol", db.String(100))
    primeiro_gol = synonym("jogador_primeiro_gol")
    participante_id = db.Column(
        db.Integer, db.ForeignKey("participante.id"), nullable=True
    )
    participacao_id = db.Column(db.Integer, db.ForeignKey("participacao.id"), nullable=False)
    origem = db.Column(db.String(20), nullable=True)
    lancado_por = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=True, default=agora_utc)
    atualizado_em = db.Column(db.DateTime, nullable=True, default=agora_utc)
    recebido_em = db.Column(db.DateTime, nullable=True)
    lancado_apos_inicio = db.Column(db.Boolean, nullable=False, default=False)
    auditoria_legada = db.Column(db.Boolean, nullable=False, default=False)
    excluido_por_desistencia = db.Column(db.Boolean, nullable=False, default=False, server_default=false())
    participacao = db.relationship("Participacao", backref="palpites")
    autor = db.relationship("Participante", foreign_keys=[lancado_por])
    jogo_id = db.Column(
        db.Integer, db.ForeignKey("jogo.id"), nullable=False, index=True
    )

    __table_args__ = (
        db.UniqueConstraint("participacao_id", "jogo_id", name="unique_palpite_participacao"),
        db.CheckConstraint("origem IS NULL OR origem IN ('responsavel', 'proprio')", name="palpite_origem"),
        db.CheckConstraint("gols_casa >= 0 AND gols_fora >= 0", name="palpite_gols"),
        db.CheckConstraint("(penaltis_casa IS NULL AND penaltis_fora IS NULL) OR "
                           "(penaltis_casa >= 0 AND penaltis_fora >= 0)", name="palpite_penaltis"),
    )


class PalpiteLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    palpite_id = db.Column(db.Integer, db.ForeignKey("palpite.id"), nullable=False, index=True)
    alterado_por = db.Column(db.Integer, db.ForeignKey("participante.id"), nullable=True)
    alterado_em = db.Column(db.DateTime, nullable=False, default=agora_utc)
    acao = db.Column(db.String(20), nullable=False)
    valores_anteriores = db.Column(db.Text, nullable=True)
    valores_novos = db.Column(db.Text, nullable=False)
    palpite = db.relationship("Palpite", backref="logs")


class Resultado(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    gols_casa_real = db.Column(db.Integer, nullable=False)
    gols_fora_real = db.Column(db.Integer, nullable=False)
    # Placar ao fim do tempo normal + prorrogação fica em gols_*_real; pênaltis à parte.
    penaltis_casa_real = db.Column(db.Integer, nullable=True)
    penaltis_fora_real = db.Column(db.Integer, nullable=True)
    primeiro_gol_real = db.Column(db.String(100))
    jogo_id = db.Column(
        db.Integer, db.ForeignKey("jogo.id"), nullable=False, unique=True
    )


class BonusRodada(db.Model):
    """Bônus extra conquistado pelo participante em determinada rodada (ex: acertar 1º gol)."""

    id = db.Column(db.Integer, primary_key=True)
    participante_id = db.Column(
        db.Integer, db.ForeignKey("participante.id"), nullable=False
    )
    rodada_id = db.Column(
        db.Integer, db.ForeignKey("rodada.id"), nullable=False
    )
    pontos = db.Column(db.Integer, default=0, nullable=False)
    motivo = db.Column(db.String(100), default="Bônus")
    participacao_id = db.Column(db.Integer, db.ForeignKey("participacao.id"), nullable=False)
    historico = db.Column(db.Boolean, nullable=False, default=True)
    participacao = db.relationship("Participacao", backref="creditos_historicos")

    participante = db.relationship("Participante", backref="bonus_list")
    rodada = db.relationship("Rodada", backref="bonus_list")

    __table_args__ = (
        db.UniqueConstraint("participacao_id", "rodada_id", name="unique_bonus_participacao_rodada"),
    )
