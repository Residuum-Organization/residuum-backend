-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS mydb DEFAULT CHARACTER SET utf8 ;
-- -----------------------------------------------------
-- Schema residum
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema residum
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS residum DEFAULT CHARACTER SET utf8mb4 ;
USE mydb ;

-- -----------------------------------------------------
-- Table residum.endereco
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.endereco (
  id_end INT(11) NOT NULL AUTO_INCREMENT,
  rua VARCHAR(100) NOT NULL,
  bairro VARCHAR(50) NOT NULL,
  numero INT(11) NOT NULL,
  cep CHAR(8) NOT NULL,
  cidade VARCHAR(10) NOT NULL,
  PRIMARY KEY (id_end))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table residum.ponto_de_coleta
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.ponto_de_coleta (
  id_ponto INT(11) NOT NULL AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  capacidade FLOAT NOT NULL,
  endereco INT(11) NOT NULL,
  PRIMARY KEY (id_ponto),
  INDEX endereco (endereco ASC) VISIBLE,
  CONSTRAINT ponto_de_coleta_ibfk_1
    FOREIGN KEY (endereco)
    REFERENCES residum.endereco (id_end))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table residum.coleta
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.coleta (
  id_coleta INT(11) NOT NULL AUTO_INCREMENT,
  data_coleta DATETIME NOT NULL,
  status_col TINYINT(1) NOT NULL,
  volume_total FLOAT NOT NULL,
  observacao VARCHAR(50) NOT NULL,
  ponto_de_coleta_id_ponto INT(11) NOT NULL,
  PRIMARY KEY (id_coleta),
  INDEX fk_coleta_ponto_de_coleta1_idx (ponto_de_coleta_id_ponto ASC) VISIBLE,
  CONSTRAINT fk_coleta_ponto_de_coleta1
    FOREIGN KEY (ponto_de_coleta_id_ponto)
    REFERENCES residum.ponto_de_coleta (id_ponto)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table residum.descarte
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.descarte (
  id_descarte INT(11) NOT NULL AUTO_INCREMENT,
  data_desc DATETIME NOT NULL,
  quantidade FLOAT NOT NULL,
  tipo_residuo ENUM('papelao', 'plastico', 'metal', 'papel', 'cobre', 'vidro', 'pilhas', 'baterias', 'aluminio') NULL DEFAULT NULL,
  observacao VARCHAR(50) NOT NULL,
  coleta_id_coleta INT(11) NOT NULL,
  PRIMARY KEY (id_descarte),
  INDEX fk_descarte_coleta1_idx (coleta_id_coleta ASC) VISIBLE,
  CONSTRAINT fk_descarte_coleta1
    FOREIGN KEY (coleta_id_coleta)
    REFERENCES residum.coleta (id_coleta)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table residum.pontuacao
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.pontuacao (
  id_pontuacao INT(11) NOT NULL AUTO_INCREMENT,
  pontos INT(11) NOT NULL,
  data_reg DATETIME NOT NULL,
  descarte_id_descarte INT(11) NOT NULL,
  PRIMARY KEY (id_pontuacao),
  INDEX fk_pontuacao_descarte1_idx (descarte_id_descarte ASC) VISIBLE,
  CONSTRAINT fk_pontuacao_descarte1
    FOREIGN KEY (descarte_id_descarte)
    REFERENCES residum.descarte (id_descarte)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table residum.usuario
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.usuario (
  id INT(11) NOT NULL AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  telefone CHAR(11) NOT NULL,
  senha_hash VARCHAR(100) NULL DEFAULT NULL,
  pontuacao INT(11) NOT NULL,
  descarte_id_descarte INT(11) NOT NULL,
  PRIMARY KEY (id),
  INDEX pontuacao (pontuacao ASC) VISIBLE,
  INDEX fk_usuario_descarte1_idx (descarte_id_descarte ASC) VISIBLE,
  CONSTRAINT usuario_ibfk_1
    FOREIGN KEY (pontuacao)
    REFERENCES residum.pontuacao (id_pontuacao),
  CONSTRAINT fk_usuario_descarte1
    FOREIGN KEY (descarte_id_descarte)
    REFERENCES residum.descarte (id_descarte)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


-- -----------------------------------------------------
-- Table mydb.sorteio
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mydb.sorteio (
  idsorteio INT NULL,
  descricao VARCHAR(45) NOT NULL,
  cod_cupom INT NOT NULL,
  vencedor INT NOT NULL,
  usuario_id INT(11) NOT NULL,
  PRIMARY KEY (idsorteio),
  INDEX fk_sorteio_usuario_idx (usuario_id ASC) VISIBLE,
  CONSTRAINT fk_sorteio_usuario
    FOREIGN KEY (usuario_id)
    REFERENCES residum.usuario (id)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table mydb.participantes_sort
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mydb.participantes_sort (
  idparticipantes_sort INT NULL AUTO_INCREMENT,
  cod_sorteio INT NOT NULL,
  id_usuario INT NOT NULL,
  sorteio_idsorteio INT NOT NULL,
  usuario_id INT(11) NOT NULL,
  PRIMARY KEY (idparticipantes_sort),
  INDEX fk_participantes_sort_sorteio1_idx (sorteio_idsorteio ASC) VISIBLE,
  INDEX fk_participantes_sort_usuario1_idx (usuario_id ASC) VISIBLE,
  CONSTRAINT fk_participantes_sort_sorteio1
    FOREIGN KEY (sorteio_idsorteio)
    REFERENCES mydb.sorteio (idsorteio)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT fk_participantes_sort_usuario1
    FOREIGN KEY (usuario_id)
    REFERENCES residum.usuario (id)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table mydb.estoque
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mydb.estoque (
  id_estoque INT NULL AUTO_INCREMENT,
  tipo_material VARCHAR(45) NOT NULL,
  quantidade FLOAT NOT NULL,
  data DATETIME NOT NULL,
  ponto_de_coleta_id_ponto INT(11) NOT NULL,
  PRIMARY KEY (id_estoque),
  INDEX fk_estoque_ponto_de_coleta1_idx (ponto_de_coleta_id_ponto ASC) VISIBLE,
  CONSTRAINT fk_estoque_ponto_de_coleta1
    FOREIGN KEY (ponto_de_coleta_id_ponto)
    REFERENCES residum.ponto_de_coleta (id_ponto)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

USE residum ;

-- -----------------------------------------------------
-- Table residum.campanha
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS residum.campanha (
  id_campanha INT(11) NOT NULL AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  desc_camp VARCHAR(100) NOT NULL,
  data_inic DATETIME NOT NULL,
  data_fim DATETIME NOT NULL,
  coleta_id_coleta INT(11) NOT NULL,
  PRIMARY KEY (id_campanha),
  INDEX fk_campanha_coleta1_idx (coleta_id_coleta ASC) VISIBLE,
  CONSTRAINT fk_campanha_coleta1
    FOREIGN KEY (coleta_id_coleta)
    REFERENCES residum.coleta (id_coleta)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;