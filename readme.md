# 📄 Extração de Dados Médicos com Gemini + MySQL

## 📌 Visão Geral

Este projeto realiza a **extração automatizada de dados médicos** a partir de **arquivos PDF de exames laboratoriais**, utilizando o modelo **Gemini (Google Generative AI)**. Os dados estruturados são normalizados em **JSON** e persistidos em um banco de dados **MySQL**, permitindo análises posteriores, dashboards ou integração com pipelines de dados.

O sistema foi projetado para lidar tanto com PDFs textuais quanto PDFs escaneados (imagem).

---

## 🏗 Arquitetura do Pipeline

1. Leitura de arquivos PDF em diretório local
2. Upload do PDF para a API do Gemini
3. Processamento e extração semântica dos dados médicos
4. Retorno estruturado em JSON
5. Validação e normalização dos dados
6. Inserção no banco MySQL
7. Exclusão do arquivo da API do Gemini

```
PDF → Gemini API → JSON → MySQL
```

---

## 🧠 Dados Extraídos

Atualmente, o sistema extrai:

### Exames laboratoriais

* Nome do paciente
* Documento de origem
* Nome do exame (ex: Hemoglobina, Glicose)
* Valor do exame
* Unidade de medida
* Data de coleta

### Estrutura JSON esperada

```json
{
  "exames": [
    {
      "paciente": "Nome do Paciente",
      "documento": "arquivo.pdf",
      "nome_exame": "Hemoglobina",
      "valor_exame": "13.5",
      "unidade": "g/dL",
      "data_coleta": "2024-01-12"
    }
  ],
  "diagnosticos": [],
  "medicamentos": []
}
```

---

## 🛠 Tecnologias Utilizadas

* **Python 3.10+**
* **Google Generative AI (Gemini)**
* **MySQL**
* Bibliotecas:

  * `google-generativeai`
  * `mysql-connector-python`
  * `json`
  * `re`
  * `os`

---

## ⚙️ Configuração do Ambiente

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/extracao-medica-gemini.git
cd extracao-medica-gemini
```

### 2. Criar ambiente virtual (opcional)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variável de ambiente (API Key)

**Windows (PowerShell):**

```powershell
setx GOOGLE_API_KEY "SUA_API_KEY"
```

**Linux / Mac:**

```bash
export GOOGLE_API_KEY="SUA_API_KEY"
```

---

## 🗄 Estrutura do Banco de Dados

### Tabela `exames`

```sql
CREATE TABLE exames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente VARCHAR(255),
    documento VARCHAR(255),
    nome_exame VARCHAR(255),
    valor_exame VARCHAR(50),
    unidade VARCHAR(50),
    data_coleta DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ▶️ Execução

1. Coloque os PDFs no diretório configurado:

```
/Extração Médica Final/exames
```

2. Execute o script principal:

```bash
python main.py
```

O sistema processará todos os PDFs do diretório, exibindo logs no terminal.

---

## 🚀 Possíveis Evoluções

* Detecção de duplicidade (idempotência)
* Suporte a diagnósticos e medicamentos
* Pipeline ETL com Airflow
* Exportação para Data Warehouse
* Dashboard com Power BI / Metabase
* Criptografia de dados sensíveis

---

## 👨‍💻 Autor

Projeto desenvolvido para estudos e aplicações em **Engenharia de Dados, IA aplicada à saúde e ETL**.

---

## 📄 Licença

Este projeto é de uso educacional e experimental. Para uso comercial ou em produção, avalie requisitos legais (LGPD, HIPAA).
