"""
Global Market Universe — Comprehensive stock/crypto/commodity tracking
Covers all major exchanges worldwide including pink sheets, OTC, and emerging markets.
"""

# ── US Markets ───────────────────────────────────────────────────────

US_LARGE_CAP = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "PG", "MA", "HD", "CVX",
    "MRK", "ABBV", "LLY", "AVGO", "COST", "KO", "PEP", "BAC", "CRM",
    "NFLX", "ADBE", "AMD", "INTC", "QCOM", "ORCL", "NOW", "TXN", "PM",
    "NEE", "UPS", "RTX", "HON", "LOW", "AMGN", "IBM", "BA", "GS",
]

US_MID_SMALL_CAP = [
    "SQ", "SNAP", "PINS", "ROKU", "ZM", "DASH", "ABNB", "PLTR",
    "SOFI", "HOOD", "RIVN", "LCID", "CHPT", "CHWY", "ETSY", "WISH",
    "CLOV", "WKHS", "NIO", "XPEV", "LI", "BYND", "NKLA", "FUBO",
    "BROS", "LULU", "WDAY", "DDOG", "NET", "CRWD", "ZS", "PANW",
]

US_CRYPTO_ADJACENT = [
    "COIN", "MSTR", "MARA", "RIOT", "HOOD", "SI", "CLSK", "HUT",
    "BITF", "IREN", "BTBT", "BTBT", "CORZ", "WULF", "CIFR",
]

US_ETFS = [
    "SPY", "QQQ", "VTI", "IWM", "EEM", "ARKK", "GLD", "TLT",
    "VXX", "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLU",
    "SOXX", "SMH", "BITX", "IBIT", "GBTC", "COIN", "BLOK",
]

US_PINK_SHEETS_OTC = [
    "PSTV", "TLSS", "HCMC", "DPLS", "ALPP", "ASTI", "CHNC",
    "GBLB", "MNPP", "SIRC", "DOWG", "PRPM", "EAST", "CUII",
    "FCCI", "TLSS", "WSRC", "GBLX", "GRNF", "CBDD", "ENZC",
    "HBRM", "ABHL", "AMDDF", "BMMJ", "BREB", "CBDS", "CIIX",
    "DCCXF", "EDXC", "ERBB", "ETST", "FGPHF", "FSPM", "GAHC",
    "HEMP", "HMPQ", "HOLLY", "IBGR", "INQD", "KALY", "LBSR",
    "LQWC", "MCIG", "MJNA", "MCOA", "MDCN", "MJTV", "MSRT",
    "NGBL", "NHMD", "NVSGF", "OZSC", "PBHG", "PCLO", "PRCX",
    "PUDO", "QEDN", "RCIT", "RMHB", "RSHC", "SAND", "SAPX",
    "SCIO", "SGMD", "SIHI", "SIRC", "SJLC", "SKAS", "SLGG",
    "SMKN", "SOCI", "SRMX", "SSOF", "SUPG", "TCBD", "TDEY",
    "TGGI", "THBD", "TIPS", "TRTC", "TRUU", "USMJ", "VAPI",
    "WARM", "WDLF", "WOCO", "YMZMF", "ZENO",
]

# ── Indonesia (IDX) ─────────────────────────────────────────────────

IDX_BLUE_CHIPS = [
    "BBCA",  # Bank Central Asia
    "BBRI",  # Bank Rakyat Indonesia
    "BMRI",  # Bank Mandiri
    "BBNI",  # Bank Negara Indonesia
    "TLKM",  # Telkom Indonesia
    "ASII",  # Astra International
    "UNVR",  # Unilever Indonesia
    "HMSP",  # HM Sampoerna
    "GGRM",  # Gudang Garam
    "KLBF",  # Kalbe Farma
    "ICBP",  # Indofood CBP
    "INDF",  # Indofood Sukses Makmur
    "SMGR",  # Semen Indonesia
    "TOWR",  # Tower Bersama
    "EXCL",  # XL Axiata
    "ISAT",  # Indosat
    "ADRO",  # Adaro Energy
    "PTBA",  # Bukit Asam
    "ITMG",  # Indo Tambangraya
    "ANTM",  # Aneka Tambang
    "MDKA",  # Merdeka Copper Gold
    "INCO",  # Vale Indonesia
    "MDRN",  # Merdeka Battery Materials
    "BBNI",  # Bank Negara Indonesia
    "BSDE",  # BSD City
    "CTRA",  # Ciputra Development
    "SMRA",  # Summarecon Agung
    "PWON",  # Pakuwon Jati
    "CPIN",  # Charoen Pokphand
    "GOOD",  # Good Food Indonesia
    "RALS",  # Ramayana Lestari
    "MAPI",  # Mitra Adiperkasa
]

IDX_TECH_GROWTH = [
    "GOTO",   # GoTo Group
    "BUKA",   # Bukalapak
    "EMTK",   # Emtek
    "DCII",   # DCI Indonesia
    "GARNET", # Telkomtelstra
    "RELI",   # Reliance
    "MTEL",   # Telkomsel
]

# ── Japan (TSE) ──────────────────────────────────────────────────────

TSE_BLUE_CHIPS = [
    "7203.T",  # Toyota
    "6758.T",  # Sony
    "6861.T",  # Keyence
    "8306.T",  # Mitsubishi UFJ
    "9984.T",  # SoftBank Group
    "6501.T",  # Hitachi
    "7751.T",  # Canon
    "6954.T",  # Fanuc
    "8035.T",  # Tokyo Electron
    "4063.T",  # Shin-Etsu Chemical
    "7267.T",  # Honda
    "6702.T",  # Fujitsu
    "5020.T",  # ENEOS
    "7974.T",  # Nintendo
    "9433.T",  # KDDI
    "4502.T",  # Takeda Pharma
    "6098.T",  # Recruit
    "8411.T",  # Mizuho
    "1605.T",  # INPEX
    "4519.T",  # Chugai Pharma
    "6178.T",  # Japan Post
    "7182.T",  # Japan Tobacco
    "5401.T",  # Nippon Steel
    "8766.T",  # Tokio Marine
    "7011.T",  # Mitsubishi Motors
]

# ── London (LSE) ──────────────────────────────────────────────────────

LSE_BLUE_CHIPS = [
    "SHEL.L",  # Shell
    "AZN.L",   # AstraZeneca
    "HSBA.L",  # HSBC
    "GSK.L",   # GSK
    "BP.L",    # BP
    "ULVR.L",  # Unilever
    "DGE.L",   # Diageo
    "AAL.L",   # Anglo American
    "BATS.L",  # British American Tobacco
    "RIO.L",   # Rio Tinto
    "BARC.L",  # Barclays
    "LLOY.L",  # Lloyds
    "VOD.L",   # Vodafone
    "NG.L",    # National Grid
    "BT-A.L",  # BT Group
    "BA.L",    # BAE Systems
    "NWG.L",   # NatWest
    "CRDA.L",  # Croda
    "SN.L",    # Smith & Nephew
    "SBRY.L",  # Sainsbury's
]

# ── Hong Kong (HKEX) ─────────────────────────────────────────────────

HKEX_BLUE_CHIPS = [
    "0700.HK",  # Tencent
    "9988.HK",  # Alibaba
    "9999.HK",  # NetEase
    "0941.HK",  # China Mobile
    "1211.HK",  # BYD
    "2318.HK",  # Ping An Insurance
    "3690.HK",  # Meituan
    "1398.HK",  # ICBC
    "3988.HK",  # Bank of China
    "0005.HK",  # HSBC Holdings
    "9618.HK",  # JD.com
    "1024.HK",  # Kuaishou
    "0175.HK",  # Geely
    "2020.HK",  # Anta Sports
    "9888.HK",  # Baidu
    "1810.HK",  # Xiaomi
    "0388.HK",  # HKEX
    "2382.HK",  # Sunny Optical
    "0939.HK",  # CCB
    "1928.HK",  # Sands China
]

# ── Europe (non-UK) ──────────────────────────────────────────────────

EUROPE_BLUE_CHIPS = [
    "SAP.DE",   # SAP (Germany)
    "SIE.DE",   # Siemens (Germany)
    "ALV.DE",   # Allianz (Germany)
    "BAS.DE",   # BASF (Germany)
    "BMW.DE",   # BMW (Germany)
    "MBG.DE",   # Mercedes-Benz (Germany)
    "ADS.DE",   # Adidas (Germany)
    "DTE.DE",   # Deutsche Telekom
    "EOAN.DE",  # E.ON (Germany)
    "VOW3.DE",  # Volkswagen (Germany)
    "MC.PA",    # LVMH (France)
    "SAN.PA",   # Sanofi (France)
    "TOT.PA",   # TotalEnergies (France)
    "BNP.PA",   # BNP Paribas (France)
    "AIR.PA",   # Airbus (France)
    "OR.PA",    # L'Oreal (France)
    "CS.PA",    # Credit Agricole (France)
    "PHIA.AS",  # Philips (Netherlands)
    "ASML.AS",  # ASML (Netherlands)
    "INGA.AS",  # ING (Netherlands)
    "CPR.MC",   # Iberdrola (Spain)
    "SAN.MC",   # Santander (Spain)
    "BBVA.MC",  # BBVA (Spain)
    "REP.MC",   # Repsol (Spain)
    "NESN.SW",  # Nestle (Switzerland)
    "ROG.SW",   # Roche (Switzerland)
    "NOVN.SW",  # Novartis (Switzerland)
    "UBSG.SW",  # UBS (Switzerland)
    "RACE.MI",  # Ferrari (Italy)
    "ENEL.MI",  # Enel (Italy)
    "INTC.MI",  # Intesa Sanpaolo (Italy)
]

# ── Canada (TSX) ──────────────────────────────────────────────────────

TSX_BLUE_CHIPS = [
    "RY.TO",   # Royal Bank
    "TD.TO",   # TD Bank
    "ENB.TO",  # Enbridge
    "BNS.TO",  # Bank of Nova Scotia
    "BMO.TO",  # Bank of Montreal
    "CM.TO",   # CIBC
    "MFC.TO",  # Manulife
    "CNQ.TO",  # Canadian Natural Resources
    "SU.TO",   # Suncor
    "TRP.TO",  # TC Energy
    "SHOP.TO", # Shopify
    "CSU.TO",  # Constellation Software
    "ABX.TO",  # Barrick Gold
    "NTR.TO",  # Nutrien
    "LNR.TO",  # Lanxess
    "AEM.TO",  # Agnico Eagle
    "WFG.TO",  # West Fraser Timber
    "WCN.TO",  # Waste Connections
    "TFI.TO",  # TF International
    "ATD.TO",  # Alimentation Couche-Tard
]

# ── Australia (ASX) ──────────────────────────────────────────────────

ASX_BLUE_CHIPS = [
    "CBA.AX",  # Commonwealth Bank
    "BHP.AX",  # BHP Group
    "CSL.AX",  # CSL Limited
    "NAB.AX",  # National Australia Bank
    "WBC.AX",  # Westpac
    "ANZ.AX",  # ANZ
    "WDS.AX",  # Woodside Energy
    "FMG.AX",  # Fortescue Metals
    "TLS.AX",  # Telstra
    "WOW.AX",  # Woolworths
    "MQG.AX",  # Macquarie Group
    "REA.AX",  # REA Group
    "ALL.AX",  # Aristocrat Leisure
    "MIN.AX",  # Mineral Resources
    "JHX.AX",  # James Hardie
]

# ── Crypto (Comprehensive) ──────────────────────────────────────────

CRYPTO_MAJOR = [
    "bitcoin", "ethereum", "tether", "binancecoin", "ripple",
    "solana", "usd-coin", "staked-ether", "cardano", "dogecoin",
    "avalanche-2", "tron", "polkadot", "chainlink", "matic-network",
    "litecoin", "uniswap", "bitcoin-cash", "cosmos", "stellar",
    "monero", "ethereum-classic", "filecoin", "near", "algorand",
    "internet-computer", "hedera-hashgraph", "vechain", "theta-token", "the-graph",
]

CRYPTO_DEFI = [
    "uniswap", "aave", "maker", "compound-governance-token", "curve-dao-token",
    "sushiswap", "1inch", "pancakeswap-token", "synthetix-network-token",
    "yearn-finance", "convex-finance", "lido-dao", "rocket-pool",
    "ether-fi", "pendle", "jupiter-exchange-solana",
]

CRYPTO_MEME = [
    "dogecoin", "shiba-inu", "pepe", "bonk", "floki",
    "dogwifcoin", "brett", "meme-coin", "wojak", "turbo",
    "cat-in-a-dogs-world", "popcat", "mog-coin", "brett",
]

CRYPTO_AI = [
    "render-token", "fetch-ai", "singularitynet", "ocean-protocol",
    "akash-network", "worldcoin", "bittensor", "akash",
    "numeraire", "ocean", "fet", "agix",
]

# ── Commodities ──────────────────────────────────────────────────────

COMMODITIES = {
    "gold": "GC=F",
    "silver": "SI=F",
    "crude_oil_wti": "CL=F",
    "crude_oil_brent": "BZ=F",
    "natural_gas": "NG=F",
    "copper": "HG=F",
    "platinum": "PL=F",
    "palladium": "PA=F",
    "corn": "ZC=F",
    "wheat": "ZW=F",
    "soybeans": "ZS=F",
    "sugar": "SB=F",
    "cotton": "CT=F",
    "coffee": "KC=F",
    "cocoa": "CC=F",
    "live_cattle": "LE=F",
    "lean_hogs": "HE=F",
    "lumber": "LBS=F",
}

# ── Build Global Universe ────────────────────────────────────────────

def get_global_stock_universe() -> dict:
    """Return the complete global stock universe grouped by exchange."""
    return {
        "US Large Cap": US_LARGE_CAP,
        "US Mid/Small Cap": US_MID_SMALL_CAP,
        "US Crypto Adjacent": US_CRYPTO_ADJACENT,
        "US ETFs": US_ETFS,
        "US Pink Sheets/OTC": US_PINK_SHEETS_OTC,
        "Indonesia (IDX)": IDX_BLUE_CHIPS + IDX_TECH_GROWTH,
        "Japan (TSE)": TSE_BLUE_CHIPS,
        "London (LSE)": LSE_BLUE_CHIPS,
        "Hong Kong (HKEX)": HKEX_BLUE_CHIPS,
        "Europe (XETRA/Euronext)": EUROPE_BLUE_CHIPS,
        "Canada (TSX)": TSX_BLUE_CHIPS,
        "Australia (ASX)": ASX_BLUE_CHIPS,
    }


def get_crypto_universe() -> dict:
    """Return the complete crypto universe grouped by category."""
    return {
        "Major": CRYPTO_MAJOR,
        "DeFi": CRYPTO_DEFI,
        "Meme": CRYPTO_MEME,
        "AI/Data": CRYPTO_AI,
    }


def get_all_symbols_flat() -> list:
    """Return all stock symbols as a flat list (for ingestion)."""
    all_stocks = []
    for exchange_stocks in get_global_stock_universe().values():
        all_stocks.extend(exchange_stocks)
    return list(set(all_stocks))


def get_all_crypto_flat() -> list:
    """Return all crypto IDs as a flat list (for ingestion)."""
    all_crypto = []
    for category_coins in get_crypto_universe().values():
        all_crypto.extend(category_coins)
    return list(set(all_crypto))


def get_universe_stats() -> dict:
    """Get statistics about the global universe."""
    stock_universe = get_global_stock_universe()
    crypto_universe = get_crypto_universe()

    total_stocks = sum(len(v) for v in stock_universe.values())
    total_crypto = sum(len(v) for v in crypto_universe.values())

    return {
        "total_stocks": total_stocks,
        "total_crypto": total_crypto,
        "total_commodities": len(COMMODITIES),
        "total_assets": total_stocks + total_crypto + len(COMMODITIES),
        "exchanges": list(stock_universe.keys()),
        "crypto_categories": list(crypto_universe.keys()),
        "commodity_classes": list(COMMODITIES.keys()),
    }
