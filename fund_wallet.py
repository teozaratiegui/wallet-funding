import os
import subprocess
import sys
import requests

# --- CONFIGURACIÓN (por defecto; anula con FUNDING_AMOUNT) ---
AMOUNT = "10000000"  # 10 ALGOs en microAlgos; override con variable de entorno

def send_telegram_alert(message):
    """Notifica por Telegram. Siempre deja rastro en logs (GHA) para depurar."""
    token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    out = sys.stderr
    if not token or not chat_id:
        print(
            "Telegram: sin TELEGRAM_TOKEN o TELEGRAM_CHAT_ID. "
            "Añade ambos secrets en el repo (Settings - Secrets) con esos nombres exactos.",
            file=out,
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        ch = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
    except ValueError:
        ch = chat_id
    payload = {"chat_id": ch, "text": message[:4000]}

    try:
        r = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as e:
        print(f"Telegram: error de red: {e}", file=out)
        return False

    if r.status_code != 200:
        print(f"Telegram: HTTP {r.status_code} - {r.text[:500]}", file=out)
        return False

    try:
        data = r.json()
    except ValueError:
        print(f"Telegram: cuerpo no-JSON: {r.text[:300]}", file=out)
        return False

    if data.get("ok") is True:
        print("Telegram: entregado (ok: true en la API de Telegram).", file=sys.stdout)
        return True

    # HTTP 200 pero la API pone ok: false (token de bot inválido, chat_id malo, etc.)
    print(f"Telegram: la API devolvió ok: false - {data}", file=out)
    return False

def run_funding():
    token = os.environ.get("DISPENSER_TOKEN")
    wallet = os.environ.get("FUNDING_WALLET_ADDRESS")
    amount = os.environ.get("FUNDING_AMOUNT", AMOUNT)

    if not token:
        print("Error: No se encontró la variable de entorno DISPENSER_TOKEN.", file=sys.stderr)
        send_telegram_alert(
            "Fondeo: falta DISPENSER_TOKEN en el entorno (revisa el secret en GitHub)."
        )
        sys.exit(1)
    if not wallet:
        print(
            "Error: No se encontró la variable de entorno FUNDING_WALLET_ADDRESS.",
            file=sys.stderr,
        )
        send_telegram_alert(
            "Fondeo: falta FUNDING_WALLET_ADDRESS en el entorno (revisa el secret en GitHub)."
        )
        sys.exit(1)
    if not str(amount).isdigit() or int(amount) <= 0:
        print(
            "Error: FUNDING_AMOUNT debe ser un entero positivo de microAlgos.",
            file=sys.stderr,
        )
        send_telegram_alert("Fondeo: FUNDING_AMOUNT inválido (debe ser microAlgos, solo dígitos).")
        sys.exit(1)

    print(f"Iniciando fondeo para la wallet: {wallet}...")

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

    out = (result.stdout or "")
    err = (result.stderr or "")
    # AlgoKit a veces imprime trazas HTTP o errores en stdout; combinar para detectar fallo real
    combined = f"{out}\n{err}".lower()

    fund_failed = result.returncode != 0
    if not fund_failed and (
        "401" in combined
        or "403" in combined
        or "forbidden" in combined
        or "unauthorized" in combined
        or (
            '"error"' in combined
            and ("expired" in combined or "invalid" in combined)
        )
    ):
        fund_failed = True

    if not fund_failed:
        print("Fondeo exitoso.")
        if out:
            print(out)
        if err and err.strip():
            print(err, file=sys.stderr)
        return

    print(f"Falló el fondeo (stdout): {out}")
    print(f"Falló el fondeo (stderr): {err}", file=sys.stderr)

    error_msg = combined
    clip = (err or out)[:2000] or "(sin salida del CLI)"
    if "401" in error_msg or "403" in error_msg or "expired" in error_msg or "unauthorized" in error_msg:
        send_telegram_alert(
            "Token de AlgoKit inválido o vuelto a caducar. "
            "Renueva con: algokit dispenser login --ci y actualiza el secret DISPENSER_TOKEN."
        )
    elif "limit" in error_msg and "reached" in error_msg:
        print("Límite diario alcanzado. Intentando mañana...", file=sys.stderr)
        send_telegram_alert("Fondeo: límite diario del dispenser alcanzado. Probar otra vez mañana.")
    else:
        send_telegram_alert(f"Falleció algokit dispenser fund. Detalle:\n{clip}")

    sys.exit(1)

if __name__ == "__main__":
    run_funding()
