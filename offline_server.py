from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import pyzbar.pyzbar as pyzbar
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from hashlib import sha256
import base64
import os
import threading
import time
import qrcode
from io import BytesIO
from datetime import datetime
import json
import re

app = FastAPI()

# Configurações
ARQUIVO_JSON = "dados.json"
SECRET_KEY = "SUA_CHAVE_SECRETA_AQUI"  # Substitua pela sua chave secreta
camera_active = False
latest_frame = None
cap = None
decoded_cpf = None

# Funções para dados
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

# Funções de criptografia
def decrypt_cpf(encrypted_base64: str, secret: str) -> str:
    try:
        raw = base64.b64decode(encrypted_base64)
        if len(raw) < 17:
            raise ValueError("Base64 inválido ou muito curto")

        iv = raw[:16]
        ct_b64_ascii = raw[16:]
        ciphertext = base64.b64decode(ct_b64_ascii)

        key_hex = sha256(secret.encode('utf-8')).hexdigest()
        key = key_hex[:32].encode('ascii')

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded) + unpadder.finalize()

        return data.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Falha na descriptografia: {str(e)}")

def encrypt_cpf(cpf: str, secret: str) -> str:
    try:
        iv = os.urandom(16)
        key_hex = sha256(secret.encode('utf-8')).hexdigest()
        key = key_hex[:32].encode('ascii')
        
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(cpf.encode('utf-8')) + padder.finalize()
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        ct_b64 = base64.b64encode(ciphertext).decode('ascii')
        combined = iv + ct_b64.encode('ascii')
        return base64.b64encode(combined).decode('ascii')
    except Exception as e:
        raise ValueError(f"Falha na criptografia: {str(e)}")

# Funções de câmera e QR Code
def camera_thread():
    global camera_active, latest_frame, cap, decoded_cpf
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a câmera")
        return
    
    start_time = time.time()
    while camera_active and (time.time() - start_time) < 10:
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            latest_frame = base64.b64encode(buffer).decode('utf-8')
            
            decoded_objects = pyzbar.decode(frame)
            for obj in decoded_objects:
                if obj.type == 'QRCODE':
                    try:
                        decoded_cpf = decrypt_cpf(obj.data.decode('utf-8'), SECRET_KEY)
                        print(f"CPF decodificado: {decoded_cpf}")
                        break
                    except Exception as e:
                        print(f"Erro ao decodificar: {str(e)}")
        
        time.sleep(0.05)
    
    camera_active = False
    if cap:
        cap.release()

# Página principal
@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return """
    <html>
        <head>
            <title>Sistema de Cadastro</title>
            <style>
                body {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                
                .main-container {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 800px;
                    padding: 30px;
                }
                
                .logo-container {
                    text-align: center;
                    margin-bottom: 20px;
                }
                
                .logo {
                    max-height: 100px;
                }
                
                h1 {
                    text-align: center;
                    color: #333;
                    margin-bottom: 30px;
                }
                
                .options-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                
                .options-table td {
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    text-align: center;
                    vertical-align: middle;
                }
                
                .option-btn {
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: bold;
                    transition: background-color 0.3s;
                    margin-top: 10px;
                }
                
                .option-btn:hover {
                    background-color: #45a049;
                }
                
                .option-icon {
                    font-size: 24px;
                    color: #4CAF50;
                    margin-bottom: 10px;
                }
                
                .option-title {
                    font-weight: bold;
                    color: #333;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        </head>
        <body>
            <div class="main-container">
                <div class="logo-container">
                    <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                </div>
                <h1>Sistema de Cadastro</h1>
                
                <table class="options-table">
                    <tr>
                        <td>
                            <div class="option-icon"><i class="fas fa-user-plus"></i></div>
                            <div class="option-title">Cadastrar Usuário</div>
                            <a href="/cadastro" class="option-btn">Acessar</a>
                        </td>
                        <td>
                            <div class="option-icon"><i class="fas fa-qrcode"></i></div>
                            <div class="option-title">Ler QR Code</div>
                            <a href="/camera" class="option-btn">Acessar</a>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2">
                            <div class="option-icon"><i class="fas fa-barcode"></i></div>
                            <div class="option-title">Gerar QR Code</div>
                            <a href="/gerar-qrcode" class="option-btn">Acessar</a>
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """

# Página de cadastro
@app.get("/cadastro", response_class=HTMLResponse)
def form_page():
    return """
    <html>
        <head>
            <title>Cadastro de Usuário</title>
            <style>
                body {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                
                .form-container {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 500px;
                    padding: 30px;
                }
                
                .logo-container {
                    text-align: center;
                    margin-bottom: 20px;
                }
                
                .logo {
                    max-height: 100px;
                }
                
                h2 {
                    text-align: center;
                    color: #333;
                    margin-bottom: 20px;
                }
                
                .form-group {
                    margin-bottom: 15px;
                }
                
                label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                    color: #555;
                }
                
                input[type="text"],
                input[type="email"] {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 16px;
                    box-sizing: border-box;
                }
                
                button {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                    font-size: 16px;
                    font-weight: bold;
                    transition: background-color 0.3s;
                    margin-top: 10px;
                }
                
                button:hover {
                    background-color: #45a049;
                }
                
                .back-btn {
                    display: block;
                    text-align: center;
                    margin-top: 20px;
                    color: #4CAF50;
                    text-decoration: none;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="form-container">
                <div class="logo-container">
                    <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                </div>
                <h2>Cadastro de Usuário</h2>
                
                <form action="/cadastrar" method="post">
                    <div class="form-group">
                        <label for="cpf">CPF:</label>
                        <input type="text" id="cpf" name="cpf" required pattern="\d{11}" title="11 dígitos numéricos">
                    </div>
                    
                    <div class="form-group">
                        <label for="nome">Nome Completo:</label>
                        <input type="text" id="nome" name="nome" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">E-mail:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="celular">Celular:</label>
                        <input type="text" id="celular" name="celular" required>
                    </div>
                    
                    <button type="submit">Cadastrar</button>
                </form>
                
                <a href="/" class="back-btn">Voltar ao menu</a>
            </div>
            
            <script>
                // Máscara para CPF
                document.getElementById('cpf').addEventListener('input', function(e) {
                    this.value = this.value.replace(/\D/g, '');
                    if(this.value.length > 11) {
                        this.value = this.value.slice(0, 11);
                    }
                });
                
                // Máscara para celular
                document.getElementById('celular').addEventListener('input', function(e) {
                    this.value = this.value.replace(/\D/g, '');
                });
            </script>
        </body>
    </html>
    """

@app.post("/cadastrar", response_class=HTMLResponse)
def cadastrar(
    cpf: str = Form(...),
    nome: str = Form(...),
    email: str = Form(...),
    celular: str = Form(...)
):
    # Validação do CPF
    if not re.match(r'^\d{11}$', cpf):
        return """
        <html>
            <head>
                <style>
                    body {
                        background-color: #f5f5f5;
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }
                    
                    .error-container {
                        background-color: #f8d7da;
                        color: #721c24;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        width: 100%;
                        max-width: 500px;
                        text-align: center;
                    }
                    
                    .logo {
                        max-height: 80px;
                        margin-bottom: 20px;
                    }
                    
                    .back-btn {
                        display: inline-block;
                        margin-top: 20px;
                        color: #4CAF50;
                        text-decoration: none;
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                    <h3>Erro no Cadastro</h3>
                    <p>CPF deve conter exatamente 11 dígitos numéricos</p>
                    <a href="/cadastro" class="back-btn">Voltar ao formulário</a>
                </div>
            </body>
        </html>
        """
    
    # Carrega dados existentes
    dados = carregar_dados()
    
    # Verifica se CPF já existe
    if any(usuario['cpf'] == cpf for usuario in dados):
        return """
        <html>
            <head>
                <style>
                    body {
                        background-color: #f5f5f5;
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }
                    
                    .warning-container {
                        background-color: #fff3cd;
                        color: #856404;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        width: 100%;
                        max-width: 500px;
                        text-align: center;
                    }
                    
                    .logo {
                        max-height: 80px;
                        margin-bottom: 20px;
                    }
                    
                    .back-btn {
                        display: inline-block;
                        margin-top: 20px;
                        color: #4CAF50;
                        text-decoration: none;
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <div class="warning-container">
                    <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                    <h3>CPF Já Cadastrado</h3>
                    <p>Este CPF já está registrado em nosso sistema</p>
                    <a href="/cadastro" class="back-btn">Voltar ao formulário</a>
                </div>
            </body>
        </html>
        """
    
    # Adiciona novo usuário
    novo_usuario = {
        "cpf": cpf,
        "nome": nome,
        "email": email,
        "celular": celular,
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    dados.append(novo_usuario)
    salvar_dados(dados)
    
    return """
    <html>
        <head>
            <style>
                body {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                
                .success-container {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 500px;
                    text-align: center;
                }
                
                .logo {
                    max-height: 80px;
                    margin-bottom: 20px;
                }
            </style>
            <script>
                setTimeout(function() {
                    window.location.href = "/";
                }, 3000);
            </script>
        </head>
        <body>
            <div class="success-container">
                <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                <h3>Cadastro Realizado com Sucesso!</h3>
                <p>Você será redirecionado para a página inicial em 3 segundos...</p>
            </div>
        </body>
    </html>
    """

# Página da câmera
@app.get("/camera", response_class=HTMLResponse)
def camera_page():
    global camera_active, decoded_cpf
    if not camera_active:
        camera_active = True
        decoded_cpf = None
        threading.Thread(target=camera_thread, daemon=True).start()
    
    return """
    <html>
        <head>
            <title>Leitor de QR Code</title>
            <style>
                body {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                
                .camera-container {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 800px;
                    padding: 30px;
                    text-align: center;
                }
                
                .logo {
                    max-height: 80px;
                    margin-bottom: 20px;
                }
                
                #video-container {
                    width: 640px;
                    height: 480px;
                    margin: 20px auto;
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    overflow: hidden;
                    background-color: #000;
                }
                
                #videoFeed {
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }
                
                #countdown {
                    font-size: 1.2em;
                    margin: 15px 0;
                    color: #4CAF50;
                    font-weight: bold;
                }
                
                #resultado {
                    margin-top: 20px;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                    display: none;
                }
                
                .back-btn {
                    display: inline-block;
                    margin-top: 20px;
                    color: #4CAF50;
                    text-decoration: none;
                    font-weight: bold;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
            <script>
                let secondsLeft = 10;
                
                function updateImage() {
                    fetch('/camera-feed?' + new Date().getTime())
                        .then(response => {
                            if (!response.ok) throw new Error('Erro no feed');
                            return response.text();
                        })
                        .then(data => {
                            if(data && data !== '') {
                                document.getElementById('videoFeed').src = 'data:image/jpeg;base64,' + data;
                            }
                            setTimeout(updateImage, 50);
                        })
                        .catch(error => {
                            console.error(error);
                            setTimeout(updateImage, 100);
                        });
                }
                
                function updateCountdown() {
                    document.getElementById('countdown').textContent = secondsLeft;
                    secondsLeft--;
                    
                    if (secondsLeft >= 0) {
                        setTimeout(updateCountdown, 1000);
                    } else {
                        window.location.href = "/";
                    }
                }
                
                function checkDecodedCPF() {
                    fetch('/get-decoded-cpf')
                        .then(response => response.json())
                        .then(data => {
                            if(data.cpf) {
                                const resultadoDiv = document.getElementById('resultado');
                                resultadoDiv.innerHTML = `
                                    <p><i class="fas fa-check-circle" style="color:#4CAF50;"></i> CPF decodificado com sucesso:</p>
                                    <h3>${data.cpf}</h3>
                                    <p>Redirecionando em 3 segundos...</p>
                                `;
                                resultadoDiv.style.display = 'block';
                                
                                setTimeout(() => {
                                    window.location.href = "/";
                                }, 3000);
                            } else {
                                setTimeout(checkDecodedCPF, 500);
                            }
                        });
                }
                
                window.onload = function() {
                    updateImage();
                    updateCountdown();
                    checkDecodedCPF();
                };
            </script>
        </head>
        <body>
            <div class="camera-container">
                <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                <h2>Leitor de QR Code</h2>
                <p>Aponte a câmera para o QR Code</p>
                
                <div id="video-container">
                    <img id="videoFeed" alt="Video feed">
                </div>
                
                <div id="countdown">10</div>
                <p>Tempo restante para leitura</p>
                
                <div id="resultado"></div>
                
                <a href="/" class="back-btn">
                    <i class="fas fa-arrow-left"></i> Voltar ao menu
                </a>
            </div>
        </body>
    </html>
    """

@app.get("/gerar-qrcode", response_class=HTMLResponse)
def gerar_qrcode_page():
    return """
    <html>
        <head>
            <title>Gerar QR Code</title>
            <style>
                body {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                
                .generator-container {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 500px;
                    padding: 30px;
                    text-align: center;
                }
                
                .logo {
                    max-height: 80px;
                    margin-bottom: 20px;
                }
                
                input[type="text"] {
                    width: 100%;
                    padding: 12px 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin-bottom: 15px;
                    font-size: 16px;
                    box-sizing: border-box;
                }
                
                button {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                    font-size: 16px;
                    font-weight: bold;
                    transition: background-color 0.3s;
                }
                
                button:hover {
                    background-color: #45a049;
                }
                
                #qrcode-container {
                    margin: 25px 0;
                    display: flex;
                    justify-content: center;
                }
                
                #qrcode-img {
                    max-width: 250px;
                    border: 10px solid white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    display: none;
                }
                
                #codigo-criptografado {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    word-break: break-all;
                    font-family: monospace;
                    font-size: 14px;
                    margin-top: 20px;
                    display: none;
                }
                
                .back-btn {
                    display: inline-block;
                    margin-top: 20px;
                    color: #4CAF50;
                    text-decoration: none;
                    font-weight: bold;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
            <script>
                function gerarQRCode() {
                    const cpf = document.getElementById('cpf').value;
                    if(!cpf || !/^\d{11}$/.test(cpf)) {
                        alert('Por favor, digite um CPF válido (11 dígitos numéricos)');
                        return;
                    }
                    
                    const btn = document.querySelector('button');
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';
                    btn.disabled = true;
                    
                    fetch('/gerar-qrcode', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `cpf=${encodeURIComponent(cpf)}`
                    })
                    .then(response => response.json())
                    .then(data => {
                        if(data.error) {
                            alert('Erro: ' + data.error);
                        } else {
                            const qrImg = document.getElementById('qrcode-img');
                            qrImg.src = data.qrcode;
                            qrImg.style.display = 'block';
                            
                            const codeDiv = document.getElementById('codigo-criptografado');
                            codeDiv.innerHTML = `
                                <p><strong>Código criptografado:</strong></p>
                                <p>${data.encrypted_cpf}</p>
                            `;
                            codeDiv.style.display = 'block';
                        }
                    })
                    .catch(error => {
                        alert('Erro ao gerar QR Code: ' + error.message);
                    })
                    .finally(() => {
                        btn.innerHTML = originalText;
                        btn.disabled = false;
                    });
                }
                
                // Máscara para CPF
                document.getElementById('cpf').addEventListener('input', function(e) {
                    this.value = this.value.replace(/\D/g, '');
                    if(this.value.length > 11) {
                        this.value = this.value.slice(0, 11);
                    }
                });
            </script>
        </head>
        <body>
            <div class="generator-container">
                <img src="/PIC.png" alt="Logo da Empresa" class="logo">
                <h2>Gerar QR Code</h2>
                
                <input type="text" id="cpf" placeholder="Digite o CPF (apenas números)" maxlength="11">
                <button onclick="gerarQRCode()">
                    <i class="fas fa-qrcode"></i> Gerar QR Code
                </button>
                
                <div id="qrcode-container">
                    <img id="qrcode-img">
                </div>
                
                <div id="codigo-criptografado"></div>
                
                <a href="/" class="back-btn">
                    <i class="fas fa-arrow-left"></i> Voltar ao menu
                </a>
            </div>
        </body>
    </html>
    """

@app.post("/gerar-qrcode")
async def gerar_qrcode(cpf: str = Form(...)):
    try:
        if not re.match(r'^\d{11}$', cpf):
            raise ValueError("CPF deve conter exatamente 11 dígitos numéricos")
        
        encrypted_cpf = encrypt_cpf(cpf, SECRET_KEY)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(encrypted_cpf)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "qrcode": img_str,
            "encrypted_cpf": encrypted_cpf
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/get-decoded-cpf")
def get_decoded_cpf():
    global decoded_cpf
    return {"cpf": decoded_cpf}

@app.get("/camera-feed")
def get_camera_feed():
    global latest_frame, camera_active
    if not camera_active or not latest_frame:
        return Response(content="", media_type="text/plain")
    return Response(content=latest_frame, media_type="text/plain")

@app.get("/PIC.png")
async def get_logo():
    return FileResponse("PIC.png")

@app.on_event("shutdown")
def shutdown_event():
    global camera_active, cap
    camera_active = False
    if cap:
        cap.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
