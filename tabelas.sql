CREATE TABLE IF NOT EXISTS exames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente VARCHAR(255),
    documento VARCHAR(255),
    nome_exame VARCHAR(150),
    valor_exame VARCHAR(50), -- Definido como VARCHAR para aceitar valores como "12.5" ou "Positivo"
    unidade VARCHAR(50),
    data_coleta DATE,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);