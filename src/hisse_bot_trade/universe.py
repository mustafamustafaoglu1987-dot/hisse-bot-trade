"""BIST ticker universe.

Reads data/bist100_tickers.txt (one BIST code per line, no ".IS" suffix,
"#" comments allowed) and returns the list.

IMPORTANT: this starter list is NOT guaranteed to match the current
official BIST 100 index composition -- BIST 100 constituents are reviewed
quarterly (Jan/Apr/Jul/Oct) by Borsa Istanbul. The code never hardcodes
tickers; update the txt file with the current official list (from Borsa
Istanbul, KAP, or TradingView) whenever you want an accurate snapshot.
"""

from pathlib import Path

# .../hisse-bot-trade/src/hisse_bot_trade/universe.py -> parents[2] is the project root.
TICKERS_FILE = Path(__file__).resolve().parents[2] / "data" / "bist100_tickers.txt"


def load_tickers(path: Path = TICKERS_FILE) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} bulunamadı. Satır başına bir BIST kodu içeren bir liste oluşturun."
        )
    tickers = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tickers.append(line.upper())
    return tickers
