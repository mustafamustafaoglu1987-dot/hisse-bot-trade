# hisse-bot-trade

BIST hisseleri için backtest + tarama (screener) botu. [kripto-bot-trade](../kripto-bot-trade)
ile aynı öğrenme felsefesi ve mimarisi (şeffaf strateji/backtest kodu), farklı veri katmanı.

**Neden yfinance?** Binance'in aksine Borsa İstanbul'un herkese açık/authsuz bir REST
API'si yok — resmi veri ücretli lisans gerektiriyor. yfinance (Yahoo Finance, `.IS`
uzantılı BIST kodları, örn. `THYAO.IS`) API key gerektirmeyen en pratik ücretsiz seçenek.

**⚠️ `data/bist100_tickers.txt` hakkında önemli not:** Bu dosyadaki liste, bilinen
büyük/likit BIST hisselerinden oluşan bir **başlangıç seti** — şu anki resmi BIST 100
endeksiyle birebir aynı olduğu garanti edilemez (endeks bileşenleri Borsa İstanbul
tarafından Ocak/Nisan/Temmuz/Ekim aylarında güncellenir). Güncel resmi listeyi Borsa
İstanbul, KAP veya TradingView'dan alıp bu dosyayı güncelleyin (satır başına bir kod,
`.IS` eki yazmadan).

Gerçek parayla canlı işlem YOK, paper trading da YOK (bu milestone'da) — sadece backtest
ve güncel gösterge durumu taraması. BIST'in sınırlı işlem saatleri (10:00-18:00 TSİ) ve
günlük veri granülaritesi, kripto botundaki gibi 7/24 canlı simülasyonu anlamsız kılıyor;
bu ileride ayrı bir faz olabilir.

## Kurulum

```
uv sync
```

## Kullanım

### Tek hisse backtest

```
uv run hisse-bot backtest --ticker THYAO --strategy sma_crossover --start 2024-01-01 --end 2026-09-01 --plot
```

- `--strategy`: `sma_crossover` (varsayılan) veya `rsi_reversion`
- İlk çalıştırmada veri yfinance'ten çekilir, `data/ohlcv/{TICKER}.csv` olarak cache'lenir
- `--plot` equity eğrisini `equity_curve.png` olarak kaydeder

### BIST taraması (scan)

```
uv run hisse-bot scan --strategy rsi_reversion --sort oversold --limit 20
```

- `data/bist100_tickers.txt`'deki tüm hisseleri tek bir toplu yfinance çağrısıyla çeker
  (rate-limit riskini azaltmak için), güncel RSI/SMA durumunu hesaplar
- Aynı gün içinde tekrar taramada cache kullanılır (API'ye tekrar gidilmez)
- `--sort oversold|overbought|ticker`, `--limit N` ile sonuç listesini daralt
- Sadece rapor üretir, hiçbir işlem yapmaz

## Testler

```
uv run pytest
```

## Yol haritası (bu milestone'un kapsamı dışında)

- Gerçek/güncel BIST100 listesinin otomatik güncellenmesi
- Paper trading (BIST işlem saatlerine uyumlu)
- Gerçek parayla canlı işlem
