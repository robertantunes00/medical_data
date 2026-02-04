import google.generativeai as genai

# Configure sua chave
genai.configure(api_key="AIzaSyC7NbebKojksRYiKOXMy5Ao55gzfmkOy6U")

print("--- Listando Modelos Disponíveis ---")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Modelo: {m.name}")
            print(f"Versão: {m.version}")
            print(f"Descrição: {m.description}")
            print("-" * 30)
except Exception as e:
    print(f"Erro ao listar modelos: {e}")