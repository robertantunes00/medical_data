import os
import json
import fitz  # PyMuPDF
import pymysql
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import UserMessage, SystemMessage, ImageContentItem, TextContentItem
from azure.core.credentials import AzureKeyCredential

load_dotenv()

#chaves_azure
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

#chamada azure
client = ChatCompletionsClient(
    endpoint=AZURE_OPENAI_ENDPOINT,
    credential=AzureKeyCredential(AZURE_OPENAI_KEY)
)

#login do banco de dados
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "SUA_SENHA",
    "database": "exames_db"
}

def criar_tabelas_se_necessario():
    """Cria as tabelas exames, diagnosticos e medicamentos se não existirem"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
# Tabela de Exames
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

    # Tabela de Diagnósticos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnosticos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paciente VARCHAR(255),
            documento VARCHAR(255),
            descricao TEXT
        )
    """)

    # Tabela de Medicamentos
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

def pdf_to_images(pdf_path):
    """Converte PDF em lista de imagens (bytes)"""
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    return images

def extract_dados_from_pdf(pdf_path):
    """Extrai exames, diagnósticos e medicamentos via Azure GPT Vision"""
    
    images = pdf_to_images(pdf_path)
    all_results = []

    for idx, img in enumerate(images):
        try:
            response = client.complete(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[SystemMessage(content="Você é um assistente médico especializado em extração estruturada de dados clínicos."),
                    UserMessage(content=[
                        TextContentItem(
                            text=
"""
Retorne APENAS um JSON válido no formato:
{
  "paciente": "Nome Completo do Paciente ou null",
  "exames": [
    {
      "nome_exame": "string",
      "valor_exame": "string | null",
      "unidade": "string | null",
      "data_coleta": "string | null"
    }
  ],
  "diagnosticos": ["string"],
  "medicamentos": [
    {
      "nome": "string",
      "dosagem": "string | null"
    }
  ]
}
"""
                        ),
                        ImageContentItem(image_bytes=img)
                    ])
                ],
                temperature=0
            )

            content = response.output_message.content[0].text

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = {
                    "erro": "JSON inválido retornado pelo modelo",
                    "pagina": idx + 1,
                    "conteudo": content
                }

            all_results.append(parsed)

        except Exception as e:
            all_results.append({
                "erro": str(e),
                "pagina": idx + 1
            })

    return all_results

def insert_into_db(data_list, documento_nome):
    """Insere exames, diagnósticos e medicamentos no banco"""

    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for idx, item in enumerate(data_list):
            try:
                # Aceita string JSON ou dict
                dados = item if isinstance(item, dict) else json.loads(item)

                # ---------- EXAMES ----------
                for ex in dados.get("exames", []):
                    if not ex.get("nome_exame"):
                        continue

                    cursor.execute("""
                        INSERT INTO exames
                        (documento, nome_exame, valor_exame, unidade, data_coleta)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        documento_nome,
                        ex.get("nome_exame"),
                        ex.get("valor_exame") or None,
                        ex.get("unidade") or None,
                        ex.get("data_coleta") or None
                    ))

                # ---------- DIAGNÓSTICOS ----------
                for diag in dados.get("diagnosticos", []):
                    if not diag:
                        continue

                    cursor.execute("""
                        INSERT INTO diagnosticos
                        (documento, descricao)
                        VALUES (%s, %s)
                    """, (
                        documento_nome,
                        diag
                    ))

                # ---------- MEDICAMENTOS ----------
                for med in dados.get("medicamentos", []):
                    if not med.get("nome"):
                        continue

                    cursor.execute("""
                        INSERT INTO medicamentos
                        (documento, nome, dosagem, frequencia)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        documento_nome,
                        med.get("nome"),
                        med.get("dosagem") or None,
                        med.get("frequencia") or None
                    ))

            except Exception as e:
                print(f"[Página {idx+1}] Erro ao processar JSON: {e}")

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao inserir dados do documento {documento_nome}: {e}")

    finally:
        if conn:
            conn.close()

def processar_pasta_pdfs(pasta):
    """Processa todos os PDFs da pasta"""
    criar_tabelas_se_necessario()
    arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(".pdf")]

    for arquivo in arquivos:
        caminho_pdf = os.path.join(pasta, arquivo)
        print(f"🔍 Processando: {arquivo}")
        resultados = extract_dados_from_pdf(caminho_pdf)
        insert_into_db(resultados, documento_nome=arquivo)
        print(f"✅ Finalizado: {arquivo}\n")

# 🧪 Execução direta
if __name__ == "__main__":
    pasta_pdfs = "pdfs"  # Substitua pelo caminho da sua pasta
    processar_pasta_pdfs(pasta_pdfs)