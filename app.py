import os
import google.generativeai as genai
import mysql.connector
import json
import time
import re

# 1. CONFIGURAÇÕES
API_KEY = ""
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash' 
model = genai.GenerativeModel(MODEL_NAME)

db_base_config = {
    'host': "localhost",
    'user': "root",
    'password': "",
    'database': "medicaldata"
}

pasta_pdfs = r'C:\Users\rtans\Desktop\Extração Médica Final\exames'

def processar_lote_arquivos():
    conn = mysql.connector.connect(**db_base_config)
    cursor = conn.cursor()
    
    arquivos = [f for f in os.listdir(pasta_pdfs) if f.lower().endswith(".pdf")]
    
    for nome_arquivo in arquivos:
        print(f"- Analisando Documento {nome_arquivo}")
        caminho_completo = os.path.join(pasta_pdfs, nome_arquivo)
        
        try:
            # FAZ O UPLOAD DO ARQUIVO PARA A API DO GOOGLE
            # Isso permite que o Gemini "leia" o PDF original, mesmo que seja imagem
            arquivo_gemini = genai.upload_file(path=caminho_completo, display_name=nome_arquivo)
            
            # Aguarda o processamento do arquivo (necessário para PDFs)
            while arquivo_gemini.state.name == "PROCESSING":
                time.sleep(2)
                arquivo_gemini = genai.get_file(arquivo_gemini.name)

            prompt = [
                arquivo_gemini,
                f"""Atue como um extrator de dados médicos de alta precisão. 
                Analise este documento (PDF) e extraia os dados para JSON.
                
                No campo 'documento', use exatamente: {nome_arquivo}
                
                Regras Cruciais:
                1. Localize o nome do paciente no cabeçalho.
                2. Extraia cada item do exame (ex: Hemoglobina, Glicose) com seu valor e unidade.
                3. Datas devem ser YYYY-MM-DD.
                
                Retorne apenas o JSON puro:
                {{
                  "exames": [{{ "paciente": "...", "documento": "...", "nome_exame": "...", "valor_exame": "...", "unidade": "...", "data_coleta": "..." }}],
                  "diagnosticos": [],
                  "medicamentos": []
                }}"""
            ]

            response = model.generate_content(prompt)
            
            # Limpeza e inserção
            texto_json = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            json_data = json.loads(texto_json)
            for item in json_data.get('exames', []):
                cursor.execute("""
                    INSERT INTO exames (paciente, documento, nome_exame, valor_exame, unidade, data_coleta) 
                    VALUES (%s,%s,%s,%s,%s,%s)""",
                    (item.get('paciente'), item.get('documento'), item.get('nome_exame'), 
                     item.get('valor_exame'), item.get('unidade'), item.get('data_coleta')))
            
            conn.commit()
            print(f"✓ {nome_arquivo} processado com sucesso.")

            genai.delete_file(arquivo_gemini.name)
            
            time.sleep(5) # Delay para evitar limite de cota

        except Exception as e:
            print(f"X Erro ao processar {nome_arquivo}: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    processar_lote_arquivos()
