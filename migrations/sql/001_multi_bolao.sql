-- Schema congelado de 001_multi_bolao; sem dados pessoais.
CREATE TABLE _schema_migrations (id TEXT PRIMARY KEY, aplicado_em TEXT NOT NULL);
CREATE TABLE bolao (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	campeonato_id INTEGER NOT NULL, 
	criador_id INTEGER NOT NULL, 
	codigo_convite VARCHAR(100), 
	permite_palpite_proprio BOOLEAN NOT NULL, 
	permite_lancamento_por_responsavel BOOLEAN NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	criado_em DATETIME NOT NULL, 
	pontua_desde_entrada BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campeonato_id) REFERENCES campeonato (id), 
	FOREIGN KEY(criador_id) REFERENCES participante (id), 
	UNIQUE (codigo_convite)
);
CREATE TABLE bonus_rodada (
	id INTEGER NOT NULL, 
	participante_id INTEGER NOT NULL, 
	rodada_id INTEGER NOT NULL, 
	pontos INTEGER NOT NULL, 
	motivo VARCHAR(100), 
	participacao_id INTEGER NOT NULL, 
	historico BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_bonus_participacao_rodada UNIQUE (participacao_id, rodada_id), 
	FOREIGN KEY(participante_id) REFERENCES participante (id), 
	FOREIGN KEY(rodada_id) REFERENCES rodada (id), 
	FOREIGN KEY(participacao_id) REFERENCES participacao (id)
);
CREATE TABLE campeonato (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	ano INTEGER, 
	codigo_api VARCHAR(20), 
	PRIMARY KEY (id)
);
CREATE TABLE classificacao_cache (
	id INTEGER NOT NULL, 
	campeonato_id INTEGER NOT NULL, 
	dados_json TEXT NOT NULL, 
	atualizado_em DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (campeonato_id), 
	FOREIGN KEY(campeonato_id) REFERENCES campeonato (id)
);
CREATE TABLE jogo (
	id INTEGER NOT NULL, 
	time_casa VARCHAR(100) NOT NULL, 
	time_fora VARCHAR(100) NOT NULL, 
	classico BOOLEAN NOT NULL, 
	especial BOOLEAN, 
	primeiro_marcador VARCHAR(100), 
	encerrado BOOLEAN NOT NULL, 
	data DATETIME, 
	external_fonte VARCHAR(50), 
	external_id VARCHAR(100), 
	rodada_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(rodada_id) REFERENCES rodada (id)
);
CREATE TABLE palpite (
	id INTEGER NOT NULL, 
	gols_casa INTEGER NOT NULL, 
	gols_fora INTEGER NOT NULL, 
	primeiro_gol VARCHAR(100), 
	participante_id INTEGER, 
	participacao_id INTEGER NOT NULL, 
	origem VARCHAR(20), 
	lancado_por INTEGER, 
	criado_em DATETIME, 
	atualizado_em DATETIME, 
	recebido_em DATETIME, 
	lancado_apos_inicio BOOLEAN NOT NULL, 
	auditoria_legada BOOLEAN NOT NULL, 
	jogo_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_palpite_participacao UNIQUE (participacao_id, jogo_id), 
	CONSTRAINT palpite_origem CHECK (origem IS NULL OR origem IN ('responsavel', 'proprio')), 
	CONSTRAINT palpite_gols CHECK (gols_casa >= 0 AND gols_fora >= 0), 
	FOREIGN KEY(participante_id) REFERENCES participante (id), 
	FOREIGN KEY(participacao_id) REFERENCES participacao (id), 
	FOREIGN KEY(lancado_por) REFERENCES participante (id), 
	FOREIGN KEY(jogo_id) REFERENCES jogo (id)
);
CREATE TABLE palpite_log (
	id INTEGER NOT NULL, 
	palpite_id INTEGER NOT NULL, 
	alterado_por INTEGER, 
	alterado_em DATETIME NOT NULL, 
	acao VARCHAR(20) NOT NULL, 
	valores_anteriores TEXT, 
	valores_novos TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(palpite_id) REFERENCES palpite (id), 
	FOREIGN KEY(alterado_por) REFERENCES participante (id)
);
CREATE TABLE participacao (
	id INTEGER NOT NULL, 
	bolao_id INTEGER NOT NULL, 
	usuario_id INTEGER, 
	participante_legado_id INTEGER, 
	nome_exibicao VARCHAR(100) NOT NULL, 
	papel VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	entrou_em DATETIME, 
	entrada_legada BOOLEAN NOT NULL, 
	pontua_desde DATETIME, 
	saiu_em DATETIME, 
	codigo_vinculo VARCHAR(100), 
	PRIMARY KEY (id), 
	CONSTRAINT unique_usuario_bolao UNIQUE (bolao_id, usuario_id), 
	CONSTRAINT unique_legado_bolao UNIQUE (bolao_id, participante_legado_id), 
	CONSTRAINT participacao_papel CHECK (papel IN ('responsavel', 'participante')), 
	CONSTRAINT participacao_status CHECK (status IN ('ativo', 'saiu', 'removido')), 
	FOREIGN KEY(bolao_id) REFERENCES bolao (id), 
	FOREIGN KEY(usuario_id) REFERENCES participante (id), 
	FOREIGN KEY(participante_legado_id) REFERENCES participante (id), 
	UNIQUE (codigo_vinculo)
);
CREATE TABLE participante (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	senha VARCHAR(200), 
	admin BOOLEAN NOT NULL, 
	admin_global BOOLEAN NOT NULL, 
	conta_ativa BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);
CREATE TABLE resultado (
	id INTEGER NOT NULL, 
	gols_casa_real INTEGER NOT NULL, 
	gols_fora_real INTEGER NOT NULL, 
	primeiro_gol_real VARCHAR(100), 
	jogo_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (jogo_id), 
	FOREIGN KEY(jogo_id) REFERENCES jogo (id)
);
CREATE TABLE rodada (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	aberta BOOLEAN, 
	campeonato_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(campeonato_id) REFERENCES campeonato (id)
);
