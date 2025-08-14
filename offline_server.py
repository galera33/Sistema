from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import os
import uvicorn

app = FastAPI()

ARQUIVO_JSON = "dados.json"

# Funções para carregar e salvar dados
def carregar_dados():
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def salvar_dados(lista):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

# Página HTML do formulário
@app.get("/", response_class=HTMLResponse)
def form_page():
    return """
    <html>
        <body>
            <h2>Cadastro de Usuário</h2>
            <form action="/cadastrar" method="post">
                <label>CPF:</label>
                <input type="text" name="cpf" required><br><br>

                <label>Nome:</label>
                <input type="text" name="nome" required><br><br>

                <label>Email:</label>
                <input type="email" name="email" required><br><br>

                <label>Telefone:</label>
                <input type="text" name="telefone" required><br><br>

                <button type="submit">Cadastrar</button>
            </form>
        </body>
    </html>
    """

# Rota para cadastrar usuário e mostrar mensagem de sucesso
@app.post("/cadastrar", response_class=HTMLResponse)
def cadastrar(cpf: str = Form(...), nome: str = Form(...), email: str = Form(...), telefone: str = Form(...)):
    dados = carregar_dados()

    novo_usuario = {
        "cpf": cpf,
        "nome": nome,
        "email": email,
        "telefone": telefone,
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    dados.append(novo_usuario)
    salvar_dados(dados)

    # Página de confirmação com redirecionamento após 5 segundos
    return f"""
    <html>
        <body>
            <h3>Usuário cadastrado com sucesso!</h3>
            <p>Você será redirecionado para cadastrar um novo usuário em 5 segundos...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "/";
                }}, 5000);
            </script>
        </body>
    </html>
    """
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
