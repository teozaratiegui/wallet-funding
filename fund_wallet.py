import os
import subprocess
import sys
import requests

# --- CONFIGURACIÓN (por defecto; anula con FUNDING_AMOUNT) ---
AMOUNT = "10000000"  # 10 ALGOs en microAlgos; override con variable de entorno

def send_telegram_alert(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Error enviando Telegram: {e}")

def run_funding():
    token = os.environ.get("DISPENSER_TOKEN")
    wallet = os.environ.get("FUNDING_WALLET_ADDRESS")
    amount = os.environ.get("FUNDING_AMOUNT", AMOUNT)

    if not token:
        print("❌ Error: No se encontró la variable de entorno DISPENSER_TOKEN.")
        return
    if not wallet:
        print("❌ Error: No se encontró la variable de entorno FUNDING_WALLET_ADDRESS.")
        return
    if not str(amount).isdigit() or int(amount) <= 0:
        print("❌ Error: FUNDING_AMOUNT debe ser un entero positivo de microAlgos.")
        return

    print(f"🚀 Iniciando fondeo para la wallet: {wallet}...")

    # Ejecutamos el comando de AlgoKit
    # Configuramos la variable de entorno necesaria para el CLI
    env = os.environ.copy()
    env["ALGOKIT_DISPENSER_ACCESS_TOKEN"] = token

    result = subprocess.run(
        ["algokit", "dispenser", "fund", "--receiver", wallet, "--amount", str(amount)],
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode == 0:
        print("✅ ¡Fondeo exitoso!")
        print(result.stdout)
    else:
        # Lógica de detección de errores de Shaco
        error_msg = result.stderr.lower()
        print(f"❌ Falló el fondeo: {result.stderr}")

        if "401" in error_msg or "403" in error_msg or "expired" in error_msg:
            alert = "⚠️ ¡Teo! El token de AlgoKit ha expirado. Necesitas renovarlo con 'algokit dispenser login --ci' 🔪🤡"
            send_telegram_alert(alert)
        elif "limit reached" in error_msg:
            print("⏳ Límite diario alcanzado. Intentando mañana...")
        else:
            send_telegram_alert(f"🚨 Error técnico inesperado en el script de fondeo: {result.stderr[:100]}")
        
        sys.exit(1)

if __name__ == "__main__":
    run_funding()