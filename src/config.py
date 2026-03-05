import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class IBConfig:
    host: str
    port: int
    client_id: int
    base_currency: str
    accounts: list          # All accounts to subscribe to; first is used at connect time
    greeks_use_ib: bool     # True = try reqMktData (requires market data subscription)
    max_options_greeks: int # How many option rows to compute Greeks for


def get_ib_config() -> IBConfig:
    """Load IBKR connection settings from environment variables."""
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    client_id = int(os.getenv("IB_CLIENT_ID", "1"))
    base_currency = os.getenv("BASE_CURRENCY", "USD")

    raw_accounts = os.getenv("IB_ACCOUNTS", os.getenv("IB_ACCOUNT", ""))
    accounts = [a.strip() for a in raw_accounts.split(",") if a.strip()]

    greeks_use_ib = os.getenv("GREEKS_USE_IB", "false").strip().lower() == "true"
    max_options_greeks = int(os.getenv("MAX_OPTIONS_GREEKS", "4"))

    return IBConfig(
        host=host,
        port=port,
        client_id=client_id,
        base_currency=base_currency,
        accounts=accounts,
        greeks_use_ib=greeks_use_ib,
        max_options_greeks=max_options_greeks,
    )


