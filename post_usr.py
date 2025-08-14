import requests
import cv2
import time
from datetime import datetime

BASE_URL = "https://promosim-production.up.railway.app/api"

def ler_qrcode():
    print("Abrindo câmera por 5 segundos...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Não foi possível abrir a câmera.")
        return
    start_time = time.time()
    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Leitor de QR Code", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    print("Câmera fechada.")


def registrar_usuario():
    cpf = input("Digite o CPF: ")

    # Verifica se já existe
    url_check = f"{BASE_URL}/activities"
    payload = {
        "cpf": cpf,
        "activity": 0,
        "created_at": datetime.now().isoformat() 
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(url_check, json=payload, headers=headers)

    if response.status_code == 201:
        print("usuario já contem cadastro, atividade registrada com sucesso")
    elif response.status_code == 409:
        print("Novo usuario autenticado, completando cadastro:")


        nome = input("Digite o nome: ")
        email = input("Digite o email: ")
        celular = input("Digite o celular: ")

        payload = {
            "cpf": cpf,
            "name": nome,
            "email": email,
            "cellphone": celular,
            "created_at": datetime.now().isoformat() 
        }

        url = f"{BASE_URL}/pre-registration"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        print("Status Code:", response.status_code)
        print("Resposta:", response.text)

        if response.status_code == 201:
            print("usuario pré-cadastrado com sucesso")


def registrar_atividade():
    cpf = input("Digite o CPF: ")
    atividade = int(input("Digite o código da atividade: "))
    created_at = datetime.now().isoformat()

    payload = {
        "cpf": cpf,
        "activity": atividade,
        "created_at": created_at
    }

    url = f"{BASE_URL}/activities"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)

    print("Status Code:", response.status_code)
    print("Resposta:", response.text)

    if response.status_code == 201:
        print("Atividade registrada com sucesso")
    elif response.status_code == 400:
        print("Dados Invalidos")    

def main():
    while True:
        print("\n--- MENU ---")
        print("1. Ler QR Code")
        print("2. Verificar CPF")
        print("3. Registrar novo usuário")
        print("4. Registrar atividade")
        print("0. Sair")

        escolha = input("Escolha uma opção: ")

        if escolha == "1":
            ler_qrcode()
        elif escolha == "3":
            registrar_usuario()
        elif escolha == "4":
            registrar_atividade()
        elif escolha == "0":
            print("Saindo...")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
