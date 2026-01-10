import os
import json
import fitz  # PyMuPDF
import pymysql
import pytesseract
from PIL import Image
from dotenv import load_dotenv

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# =========================
# CONFIGURAÇÕES
# =========================

load_dotenv()

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "SUA_SENHA",
    "database": "exames_db",
    "charset": "utf8mb4"
}

client = ChatCompletionsClient(
    endpoint=AZURE_OPENAI_ENDPOINT,
    credential=AzureKeyCredential(AZURE_OPENAI_KEY)
)

SYSTEM_PROMPT = """
Você é um sistema de extração de informações estruturadas a partir de documentos clínicos.
Extraia apenas informações explicitamente presentes no texto.
Nunca invente dados.
Retorne APENAS JSON válido.
"""

# =========================
# BANCO DE DADOS
# =========================

def criar_tabelas_se_necessario():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exames (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paciente VARCHAR(255),
            documento VARCHAR(255),
            nome_exame VARCHAR(255),
            valor_exame VARCHAR(50),
            unidade VARCHAR(50),
            data_coleta DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnosticos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paciente VARCHAR(255),
            documento VARCHAR(255),
            descricao TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paciente VARCHAR(255),
            documento VARCHAR(255),
            nome VARCHAR(255),
            dosagem VARCHAR(100)
        )
    """)

    conn.commit()
    conn.close()

# =========================
# PDF → TEXTO (OCR fallback)
# =========================

def pdf_to_text(pdf_path):
    doc = fitz.open(pdf_path)
    paginas_texto = []

    for page in doc:
        texto = page.get_text().strip()

        if not texto:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texto = pytesseract.image_to_string(img, lang="por")

        paginas_texto.append(texto)

    return paginas_texto

# =========================
# GPT → JSON
# =========================

def extract_dados_from_text(texto):
    response = client.complete(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            SystemMessage(content=SYSTEM_PROMPT),
            UserMessage(content=f"""
Texto do documento:
\"\"\"
{texto}
\"\"\"

Retorne APENAS um JSON no formato:

{{
  "paciente": "string | null",
  "exames": [
    {{
      "nome_exame": "string",
      "valor_exame": "string | null",
      "unidade": "string | null",
      "data_coleta": "string | null"
    }}
  ],
  "diagnosticos": ["string"],
  "medicamentos": [
    {{
      "nome": "string",
      "dosagem": "string | null"
    }}
  ]
}}
""")
        ],
        temperature=0
    )

    return json.loads(response.output_message.content[0].text)

# =========================
# JSON → BANCO
# =========================

def insert_into_db(dados, documento):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    paciente = dados.get("paciente")

    for ex in dados.get("exames", []):
        cursor.execute("""
            INSERT INTO exames
            (paciente, documento, nome_exame, valor_exame, unidade, data_coleta)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            paciente,
            documento,
            ex.get("nome_exame"),
            ex.get("valor_exame"),
            ex.get("unidade"),
            ex.get("data_coleta")
        ))

    for diag in dados.get("diagnosticos", []):
        cursor.execute("""
            INSERT INTO diagnosticos
            (paciente, documento, descricao)
            VALUES (%s, %s, %s)
        """, (
            paciente,
            documento,
            diag
        ))

    for med in dados.get("medicamentos", []):
        cursor.execute("""
            INSERT INTO medicamentos
            (paciente, documento, nome, dosagem)
            VALUES (%s, %s, %s, %s)
        """, (
            paciente,
            documento,
            med.get("nome"),
            med.get("dosagem")
        ))

    conn.commit()
    conn.close()

# =========================
# PIPELINE FINAL
# =========================

def processar_pasta_pdfs(pasta):
    criar_tabelas_se_necessario()

    for arquivo in os.listdir(pasta):
        if not arquivo.lower().endswith(".pdf"):
            continue

        caminho = os.path.join(pasta, arquivo)
        print(f"🔍 Processando: {arquivo}")

        paginas = pdf_to_text(caminho)

        for texto in paginas:
            if texto.strip():
                try:
                    dados = extract_dados_from_text(texto)
                    insert_into_db(dados, documento=arquivo)
                except Exception as e:
                    print(f"❌ Erro ao processar página: {e}")

        print(f"✅ Finalizado: {arquivo}\n")

# =========================
# EXECUÇÃO
# =========================

if __name__ == "__main__":
    processar_pasta_pdfs("pdfs")
