# Fondeo Wallet

Automated **TestNet** funding for an Algorand wallet using the [AlgoKit dispenser](https://developer.algorand.org/docs/get-details/algokit/) CLI.

## Purpose

- **Daily run:** This project is designed to be executed on a **schedule (e.g. every day) via [GitHub Actions](https://docs.github.com/en/actions)**, so the target wallet receives funds regularly without manual runs.
- **Token expiry:** The AlgoKit CI dispenser token lasts about **30 days**. When the run fails with authentication errors (`401` / `403` / “expired”), the script can **send a [Telegram](https://core.telegram.org/bots/api) message** so you know to renew the token (see [Renew the dispenser token](#renew-the-dispenser-token)).

## How it works

1. A scheduled workflow (or a manual dispatch) sets environment variables and runs `wallet-funding/fund_wallet.py`.
2. The script sets `ALGOKIT_DISPENSER_ACCESS_TOKEN` from your dispenser token and `FUNDING_WALLET_ADDRESS` from a secret, then calls:
   - `algokit dispenser fund --receiver <address> --amount <microAlgos>`.
3. On certain failures (unauthorized, forbidden, or expired token), it notifies Telegram if `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are configured.

## Local setup (PowerShell)

1. **Python 3.10+** and **`requests`** (e.g. `py -m pip install requests`).

2. **AlgoKit** installed and on `PATH` (`algokit` command works).

3. **Obtain a CI token** (valid ~30 days; open the device URL in a browser when prompted):
   ```powershell
   algokit dispenser login --ci
   ```
   You can also write the token to a file with `-o file` and copy its contents.

4. **Set environment variables** in the current session (do not commit secrets):
   ```powershell
   $env:DISPENSER_TOKEN = "<your-ci-token>"
   $env:FUNDING_WALLET_ADDRESS = "<testnet-algorand-address>"
   $env:FUNDING_AMOUNT = "10000000"   # optional; default 10 ALGO in microAlgos
   $env:TELEGRAM_TOKEN = "<bot-token>"   # optional, for alerts
   $env:TELEGRAM_CHAT_ID = "<chat-id>"  # optional
   py .\wallet-funding\fund_wallet.py
   ```

## GitHub Actions

- Use a **scheduled workflow** (`on.schedule` with a daily `cron` in UTC) to run the script.
- Store **repository or environment [secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)** and map them in the workflow `env` block so names match the script, for example:
  - `DISPENSER_TOKEN` — AlgoKit CI dispenser token
  - `FUNDING_WALLET_ADDRESS` — receiver account (set this secret when you want to **change the funded wallet** without editing code)
  - `FUNDING_AMOUNT` (optional) — microAlgos; omit to use the default in the script (10 ALGO if unchanged)
  - `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (optional) — Telegram alerts

> **CI note:** The runner must have **AlgoKit** installed in the job (e.g. install the documented method for your OS in the workflow) in addition to Python and dependencies, because the script shells out to `algokit dispenser fund`.

## Configuration

- **Wallet (required):** set `FUNDING_WALLET_ADDRESS` (local env or GitHub secret) to the Algorand address that receives the funds.
- **Amount (optional):** set `FUNDING_AMOUNT` to a positive integer in **microAlgos** (1 ALGO = 1,000,000). If unset, the default in `fund_wallet.py` applies (see `AMOUNT` constant).

## Renew the dispenser token

When the Telegram alert indicates expiry (or the workflow logs show 401/403 on the dispenser):

1. On a trusted machine, run:
   ```powershell
   algokit dispenser login --ci
   ```
2. Complete browser login and update the `DISPENSER_TOKEN` (or `ALGOKIT_DISPENSER_ACCESS_TOKEN`, depending on where you store it) in GitHub secrets and anywhere else you use it.

## License / disclaimer

- Uses **TestNet** dispenser rules and limits; respect [AlgoKit / Algorand documentation](https://developer.algorand.org/) for current limits and terms.
- This README describes intended deployment (daily GHA + Telegram on token issues); keep secrets out of the repository and rotate tokens before they expire when possible.
