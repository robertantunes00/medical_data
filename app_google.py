import os
import google.generativeai as genai
import mysql.connector
import json
import time
import re

# 1. CONFIGURAÇÕES
API_KEY = "AIzaSyC7NbebKojksRYiKOXMy5Ao55gzfmkOy6U"
genai.configure(api_key=API_KEY)

MODEL_NAME = 'gemini-2.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

db_base_config = {
    'host': "localhost",
    'user': "root",
    'password': "192401"
}
DB_NAME = "medicaldata"
pasta_csvs = r'C:\Users\rtans\Desktop\Extração Médica Final\exames'

def setup_banco_de_dados():
    """Cria o banco e as tabelas se não existirem."""
    try:
        conn = mysql.connector.connect(**db_base_config)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        
        # Tabelas conforme o seu prompt
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exames (
                id INT AUTO_INCREMENT PRIMARY KEY,
                paciente VARCHAR(255),
                documento VARCHAR(255),
                nome_exame VARCHAR(255),
                valor_exame VARCHAR(100),
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
                dosagem VARCHAR(255)
            )
        """)
        conn.commit()
        print(f"--- Banco de dados '{DB_NAME}' pronto ---")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao configurar banco: {e}")
        exit()

def extrair_json_puro(texto):
    try:
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        return match.group(0) if match else texto
    except:
        return texto

def processar_lote_arquivos():
    setup_banco_de_dados()
    
    # Controle de Log apenas em memória/terminal
    stats = {"total": 0, "sucessos": 0, "falhas": []}

    conn = None
    try:
        conn = mysql.connector.connect(**db_base_config, database=DB_NAME)
        cursor = conn.cursor()
        
        arquivos = [f for f in os.listdir(pasta_csvs) if f.endswith(".csv")]
        stats["total"] = len(arquivos)
        
        for nome_arquivo in arquivos:
            print(f">>> Processando: {nome_arquivo}")
            try:
                with open(os.path.join(pasta_csvs, nome_arquivo), "r", encoding="utf-8") as f:
                    conteudo = f.read()

                # SEU PROMPT ORIGINAL
                prompt = f"""
                Atue como um extrator de dados médicos. Analise o texto abaixo e extraia informações para as tabelas.
                
                Informações para as tabelas:
                1. exames (paciente, documento, nome_exame, valor_exame, unidade, data_coleta)
                2. diagnosticos (paciente, documento, descricao)
                3. medicamentos (paciente, documento, nome, dosagem)
                
                Regras:
                - Converta datas para o formato SQL: YYYY-MM-DD.
                - Separe o valor numérico da unidade (ex: valor: "129", unidade: "mg/dL").
                - No campo 'documento', use exatamente o texto: {nome_arquivo}
                - Se não houver medicamentos ou diagnósticos, retorne a lista vazia [].

                Retorne APENAS o JSON puro:
                {{
                  "exames": [{{ "paciente": "...", "documento": "...", "nome_exame": "...", "valor_exame": "...", "unidade": "...", "data_coleta": "..." }}],
                  "diagnosticos": [{{ "paciente": "...", "documento": "...", "descricao": "..." }}],
                  "medicamentos": [{{ "paciente": "...", "documento": "...", "nome": "...", "dosagem": "..." }}]
                }}

                Texto: {conteudo}
                """

                response = model.generate_content(prompt)
                json_data = json.loads(extrair_json_puro(response.text))

                # Inserções no banco
                for item in json_data.get('exames', []):
                    cursor.execute("INSERT INTO exames (paciente, documento, nome_exame, valor_exame, unidade, data_coleta) VALUES (%s,%s,%s,%s,%s,%s)",
                                   (item.get('paciente'), item.get('documento'), item.get('nome_exame'), item.get('valor_exame'), item.get('unidade'), item.get('data_coleta')))
                
                for item in json_data.get('diagnosticos', []):
                    cursor.execute("INSERT INTO diagnosticos (paciente, documento, descricao) VALUES (%s,%s,%s)",
                                   (item.get('paciente'), item.get('documento'), item.get('descricao')))

                for item in json_data.get('medicamentos', []):
                    cursor.execute("INSERT INTO medicamentos (paciente, documento, nome, dosagem) VALUES (%s,%s,%s,%s)",
                                   (item.get('paciente'), item.get('documento'), item.get('nome'), item.get('dosagem')))

                conn.commit()
                print(f"✓ Sucesso.")
                stats["sucessos"] += 1
                time.sleep(4) # Delay para quota gratuita

            except Exception as e:
                erro_msg = str(e)
                stats["falhas"].append((nome_arquivo, erro_msg))
                print(f"X Erro: {erro_msg[:60]}...")
                if conn: conn.rollback()
                
                # Se bater na cota, encerra o loop
                if "429" in erro_msg or "quota" in erro_msg.lower():
                    print("\n!!! Interrompido por limite de cota da API.")
                    break

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
        
        # RESUMO DA TENTATIVA NO TERMINAL
        print("\n" + "="*50)
        print(f"RESUMO DA EXECUÇÃO ({MODEL_NAME})")
        print("="*50)
        print(f"Total de Arquivos: {stats['total']}")
        print(f"Processados com Sucesso: {stats['sucessos']}")
        print(f"Falhas Encontradas: {len(stats['falhas'])}")
        
        if stats['falhas']:
            print("\nLista de Falhas:")
            for arq, err in stats['falhas']:
                print(f"- {arq}: {err[:80]}")
        print("="*50)

if __name__ == "__main__":
    processar_lote_arquivos()