from database import db
from flask_login import UserMixin


class Participante(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200))
    admin = db.Column(db.Boolean, default=False, nullable=False)

    palpites = db.relationship("Palpite", backref="participante", lazy=True)


class Campeonato(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer)

    rodadas = db.relationship("Rodada", backref="campeonato", lazy=True)


class Rodada(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    aberta = db.Column(db.Boolean, default=True)
    campeonato_id = db.Column(
        db.Integer, db.ForeignKey("campeonato.id"), nullable=False
    )

    jogos = db.relationship("Jogo", backref="rodada", lazy=True)


class Jogo(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    time_casa = db.Column(db.String(100), nullable=False)
    time_fora = db.Column(db.String(100), nullable=False)
    especial = db.Column(db.Boolean, default=False)
    encerrado = db.Column(db.Boolean, default=False, nullable=False)
    data = db.Column(db.DateTime)
    external_fonte = db.Column(db.String(50))
    external_id = db.Column(db.String(100))
    rodada_id = db.Column(
        db.Integer, db.ForeignKey("rodada.id"), nullable=False
    )

    resultado = db.relationship("Resultado", backref="jogo", uselist=False)
    palpites = db.relationship("Palpite", backref="jogo", lazy=True)

    def bloqueado(self):
        """Palpite bloqueado se encerrado manualmente OU se a data já passou."""
        if self.encerrado:
            return True
        if self.data is None:
            return False
        from datetime import datetime
        return datetime.now() >= self.data

    @property
    def data_formatada(self):
        """Retorna a data e hora formatadas do jogo."""
        if self.data:
            return self.data.strftime("%d/%m/%Y às %H:%M")
        if self.encerrado:
            return "Partida finalizada"
        return "Horário a definir"



class Palpite(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    gols_casa = db.Column(db.Integer, nullable=False)
    gols_fora = db.Column(db.Integer, nullable=False)
    primeiro_gol = db.Column(db.String(100))
    participante_id = db.Column(
        db.Integer, db.ForeignKey("participante.id"), nullable=False
    )
    jogo_id = db.Column(
        db.Integer, db.ForeignKey("jogo.id"), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("participante_id", "jogo_id", name="unique_palpite"),
    )


class Resultado(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    gols_casa_real = db.Column(db.Integer, nullable=False)
    gols_fora_real = db.Column(db.Integer, nullable=False)
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

    participante = db.relationship("Participante", backref="bonus_list")
    rodada = db.relationship("Rodada", backref="bonus_list")

    __table_args__ = (
        db.UniqueConstraint("participante_id", "rodada_id", name="unique_bonus_rodada"),
    )

