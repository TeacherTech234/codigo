CREATE DATABASE IF NOT EXISTS registro;
USE registro;

CREATE TABLE IF NOT EXISTS informacoes(
    IdUsuario INT AUTO_INCREMENT,
    NomeUsuario VARCHAR(100) NOT NULL UNIQUE,
    SenhaUsuario VARCHAR(255) NOT NULL,
    NomeCompleto VARCHAR(255) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    PRIMARY KEY(IdUsuario)
);

SHOW databases;
SELECT * FROM informacoes;