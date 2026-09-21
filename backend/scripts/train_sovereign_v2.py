"""Train Quantive AI v1 — word tokenizer, 1000 QA pairs, 50 epochs.

No external downloads. Pure PyTorch. Domain-specific sovereign debt model.
"""

import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')

import json
import time
import re
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from pathlib import Path

# Load additional training data
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend\data\training\datasets')
from quantive_ai_v1_additional import ADDITIONAL_QA_PAIRS
from quantive_ai_v1_batch2 import ADDITIONAL_QA_PAIRS_BATCH2
from quantive_ai_v1_batch3 import ADDITIONAL_QA_PAIRS_BATCH3
from quantive_ai_v1_batch4 import ADDITIONAL_QA_PAIRS_BATCH4

# ── Word Tokenizer ────────────────────────────────────────────────────

class WordTokenizer:
    """Word-level tokenizer with special tokens."""

    SPECIAL = {'<PAD>': 0, '<UNK>': 1, '<BOS>': 2, '<EOS>': 3, '<SEP>': 4, '<Q>': 5, '<A>': 6}

    def __init__(self):
        self.word2idx = dict(self.SPECIAL)
        self.idx2word = {v: k for k, v in self.word2idx.items()}
        self.vocab_size = len(self.SPECIAL)

    @staticmethod
    def _tokenize(text):
        text = text.lower().strip()
        text = re.sub(r'([?.!,;:])', r' \1 ', text)
        return text.split()

    def fit(self, texts, min_freq=1):
        freq = {}
        for t in texts:
            for w in self._tokenize(t):
                freq[w] = freq.get(w, 0) + 1
        for w, c in sorted(freq.items()):
            if c >= min_freq and w not in self.word2idx:
                self.word2idx[w] = len(self.word2idx)
                self.idx2word[len(self.idx2word)] = w
        self.vocab_size = len(self.word2idx)
        return self

    def encode(self, text, max_length=256):
        tokens = self._tokenize(text)
        ids = [self.word2idx['<BOS>']]
        for w in tokens[:max_length - 2]:
            ids.append(self.word2idx.get(w, self.word2idx['<UNK>']))
        ids.append(self.word2idx['<EOS>'])
        return ids

    def decode(self, ids):
        words = []
        for i in ids:
            w = self.idx2word.get(i, '<UNK>')
            if w in ('<PAD>', '<BOS>', '<EOS>', '<SEP>'):
                continue
            if w == '<UNK>':
                continue
            words.append(w)
        return ' '.join(words)


# ── Model Architecture ────────────────────────────────────────────────

class QuantiveAI(nn.Module):
    def __init__(self, vocab_size=5000, d_model=256, n_heads=8, n_layers=6, d_ff=1024, max_seq=512):
        super().__init__()
        self.config = {
            'vocab_size': vocab_size, 'd_model': d_model,
            'n_heads': n_heads, 'n_layers': n_layers,
            'd_ff': d_ff, 'max_seq': max_seq,
        }
        self.embeddings = nn.Embedding(vocab_size, d_model)
        self.pos_embeddings = nn.Embedding(max_seq, d_model)
        self.dropout = nn.Dropout(0.1)
        decoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_ff,
            dropout=0.1, activation='gelu', batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(decoder_layer, num_layers=n_layers)
        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)
        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            nn.init.zeros_(module.bias)
            nn.init.ones_(module.weight)

    def forward(self, input_ids):
        B, T = input_ids.shape
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.dropout(self.embeddings(input_ids) + self.pos_embeddings(pos))
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=input_ids.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        return self.head(self.ln(x))


# ── Training Data ─────────────────────────────────────────────────────

TRAINING_DATA = [
    ("What is sovereign debt?", "Sovereign debt is money owed by a national government to creditors, including bonds, loans, and other financial obligations."),
    ("How is sovereign debt measured?", "It is primarily measured as the debt to GDP ratio, which compares total government debt to the country's gross domestic product."),
    ("What affects sovereign bond yields?", "Credit rating, inflation expectations, economic growth, fiscal deficit, political stability, monetary policy, and global risk sentiment all affect yields."),
    ("What is debt optimization?", "Debt optimization is the strategic management of a government's debt portfolio to minimize borrowing costs while controlling risk across maturity, currency, and interest rate exposure."),
    ("What is AI in debt management?", "AI helps optimize bond issuance timing, predict yield curves, automate regulatory compliance, detect market anomalies, and run complex scenario analysis for debt strategies."),
    ("What is a yield curve?", "A yield curve plots bond yields against their maturities. It reflects market expectations about future interest rates, inflation, and economic conditions."),
    ("What is duration risk?", "Duration risk is the sensitivity of a bond's price to changes in interest rates. A bond with higher duration will experience larger price swings when rates change."),
    ("What is the IMF Debt Sustainability Framework?", "The IMF DSF assesses whether public debt is sustainable using scenario analysis and threshold indicators like debt to GDP and gross financing needs to GDP ratios."),
    ("What are Treasury securities?", "US government debt instruments including Treasury bills for short term, notes for medium term, bonds for long term, TIPS for inflation protection, and floating rate notes."),
    ("What is credit risk in sovereign debt?", "Credit risk is the possibility that a sovereign borrower will fail to make timely interest or principal payments, resulting in default on its obligations."),
    ("What is debt restructuring?", "Debt restructuring modifies existing debt terms by extending maturities, reducing interest rates, converting currencies, or writing down principal amounts to restore sustainability."),
    ("What is fiscal consolidation?", "Fiscal consolidation reduces government deficits through spending cuts, tax increases, or structural reforms to improve the fiscal position over time."),
    ("What is a sovereign wealth fund?", "A sovereign wealth fund is a state-owned investment fund that manages excess revenues from commodities or trade surpluses for stabilization and future generations."),
    ("What is FX risk in sovereign debt?", "Foreign exchange risk arises when government debt is denominated in foreign currency. If the domestic currency depreciates, the cost of servicing that debt increases."),
    ("What do credit rating agencies do?", "S&P, Moody's, and Fitch evaluate sovereign creditworthiness based on economic fundamentals, institutional quality, and fiscal metrics, assigning ratings that affect borrowing costs."),
    ("What is the primary fiscal balance?", "The primary fiscal balance excludes interest payments from the overall balance, showing whether government revenue covers non interest spending."),
    ("What are green bonds?", "Green bonds are fixed income instruments whose proceeds fund environmentally beneficial projects, following the Green Bond Principles established by ICMA."),
    ("What is emerging market sovereign debt?", "Emerging market government debt typically carries higher yields due to perceived credit risk, currency volatility, weaker institutions, and commodity dependence."),
    ("How does quantitative finance help debt management?", "Methods like Value at Risk, Monte Carlo simulation, mean variance optimization, and machine learning models are used for risk measurement, scenario analysis, and portfolio construction."),
    ("What is EU fiscal governance?", "EU fiscal governance includes the Stability and Growth Pact requiring deficit below 3 percent of GDP and debt below 60 percent of GDP for member states."),
    ("What is interest rate modeling?", "Interest rate models like Vasicek and Cox Ingersoll Ross are used for pricing bonds, managing interest rate risk, and constructing yield curves for debt analysis."),
    ("What is debt sustainability analysis?", "Debt sustainability analysis evaluates whether a country's current debt levels and trajectory are compatible with maintaining long term fiscal stability and market confidence."),
    ("What is the role of central banks in debt?", "Central banks manage government bond issuance, conduct open market operations, set monetary policy rates, and may act as lender of last resort during debt crises."),
    ("What is political risk for sovereign debt?", "Political risk is the danger that political instability, elections, regime change, or policy shifts will affect a government's willingness or ability to repay its debts."),
    ("What is the original sin problem?", "Original sin refers to the inability of emerging markets to borrow abroad in their own currency, creating currency mismatch risk when exchange rates move adversely."),
    ("What is contagion in sovereign debt markets?", "Contagion is the spread of financial distress from one sovereign to others through market linkages, investor panic, and correlated exposure to common risk factors."),
    ("What is the European Semester?", "The European Semester is the EU framework for coordinating economic and fiscal policies across member states through annual cycles of reform recommendations."),
    ("What is a credit default swap on sovereign debt?", "A sovereign credit default swap is a financial derivative that provides protection against losses from a government defaulting on its debt obligations."),
    ("What is the Brady Bond program?", "The Brady Bond program restructured developing country debt in the 1980s and 1990s by converting bank loans into tradeable bond instruments with US government backing."),
    ("What is dollarization?", "Dollarization occurs when a country adopts the US dollar as its official currency, giving up monetary policy independence but reducing foreign exchange risk and inflation."),
    ("How do governments issue new debt?", "Governments issue debt through auctions, syndications, or book building. Treasury auctions follow a competitive bidding process where primary dealers submit bids for bonds."),
    ("What is the difference between stocks and bonds?", "Stocks represent ownership in a company and pay variable dividends, while bonds represent debt obligations that pay fixed interest payments and return principal at maturity."),
    ("What is bond convexity?", "Convexity measures the rate of change of a bond's duration. It captures the curvature in the price yield relationship, providing a more accurate estimate of price changes."),
    ("What is a basis point?", "A basis point is one hundredth of a percentage point. A change from 5 percent to 5.25 percent is a 25 basis point increase in interest rates."),
    ("What is the risk free rate?", "The risk free rate is the theoretical return on an investment with zero risk. Government bond yields, especially US Treasuries, are commonly used as proxies."),
    ("What is yield to maturity?", "Yield to maturity is the total return expected on a bond if held until it matures. It accounts for all coupon payments and any capital gain or loss."),
    ("What is current yield?", "Current yield is the annual coupon payment divided by the bond's current market price. It shows the income return relative to the price paid."),
    ("What is a coupon bond?", "A coupon bond pays periodic interest payments called coupons during its life and returns the face value at maturity. The coupon rate is fixed at issuance."),
    ("What is a zero coupon bond?", "A zero coupon bond pays no periodic interest. It is issued at a discount to face value and the return comes from the price appreciation to par at maturity."),
    ("What is inflation risk for bonds?", "Inflation risk is the danger that rising inflation will erode the real value of a bond's fixed future payments, reducing the purchasing power of coupon and principal payments."),
    ("What is liquidity risk in bond markets?", "Liquidity risk is the risk that a bond cannot be bought or sold quickly enough at a fair price due to low trading volume or market stress."),
    ("What is credit spread?", "The credit spread is the difference in yield between a corporate or sovereign bond and a risk free government bond of similar maturity, reflecting default risk."),
    ("What is the term structure of interest rates?", "The term structure shows the relationship between bond yields and their maturities. It is typically visualized as the yield curve and reflects rate expectations."),
    ("What is an inverted yield curve?", "An inverted yield curve occurs when short term bond yields exceed long term yields. It is often seen as a predictor of economic recession."),
    ("What is a flat yield curve?", "A flat yield curve occurs when there is little difference between short term and long term bond yields. It may signal uncertainty about future economic conditions."),
    ("What is a steep yield curve?", "A steep yield curve occurs when long term yields are significantly higher than short term yields. It typically indicates expectations of economic growth and rising rates."),
    ("What is bond duration?", "Duration measures a bond's price sensitivity to interest rate changes. Modified duration quantifies the percentage price change for a one percent change in yield."),
    ("What is Macaulay duration?", "Macaulay duration is the weighted average time to receive a bond's cash flows, where weights are the present value of each cash flow divided by the bond price."),
    ("What is DV01?", "DV01, or Dollar Value of an 01, measures the dollar change in a bond's price for a one basis point change in yield. It is a key risk metric for bond traders."),
    ("What is the Sharpe ratio?", "The Sharpe ratio measures risk adjusted return by dividing excess return over the risk free rate by the standard deviation of returns. Higher is better."),
    ("What is Value at Risk?", "Value at Risk estimates the maximum potential loss over a given time period at a specific confidence level. It is widely used for portfolio risk management."),
    ("What is conditional VaR?", "Conditional VaR, also known as expected shortfall, measures the average loss in the worst cases beyond the VaR threshold, providing a more conservative risk estimate."),
    ("What is Monte Carlo simulation?", "Monte Carlo simulation uses random sampling to model the probability of different outcomes. It is used in finance for pricing derivatives and assessing portfolio risk."),
    ("What is mean variance optimization?", "Mean variance optimization, developed by Markowitz, finds the portfolio allocation that maximizes expected return for a given level of risk or minimizes risk for a given return."),
    ("What is stress testing in debt management?", "Stress testing evaluates how a debt portfolio performs under extreme but plausible scenarios like interest rate shocks, currency crises, or economic recessions."),
    ("What is scenario analysis?", "Scenario analysis examines how different future events or conditions might affect a debt portfolio or fiscal outcome, using best case, base case, and worst case projections."),
    ("What is the efficient frontier?", "The efficient frontier is the set of optimal portfolios that offer the highest expected return for a given level of risk. Portfolios below the frontier are suboptimal."),
    ("What is portfolio rebalancing?", "Portfolio rebalancing is the process of periodically adjusting a debt portfolio's composition to maintain desired risk and return characteristics as market conditions change."),
    ("What is active debt management?", "Active debt management involves strategic decisions about debt issuance, maturity profiles, currency composition, and derivative usage to optimize the cost and risk of government debt."),
    ("What is passive debt management?", "Passive debt management, or buy and hold, involves issuing debt and holding it to maturity without active trading or timing strategies."),
    ("What is a debt management office?", "A debt management office is the government entity responsible for planning, executing, and managing the country's borrowing strategy and debt portfolio."),
    ("What is the Paris Club?", "The Paris Club is an informal group of creditor nations that negotiates bilateral debt relief and restructuring agreements for debtor countries."),
    ("What is the Heavily Indebted Poor Countries initiative?", "The HIPC initiative provides debt relief to the world's poorest countries through the IMF and World Bank to ensure they are not burdened by unsustainable debt."),
    ("What is sovereign debt crisis?", "A sovereign debt crisis occurs when a country cannot meet its debt obligations, leading to defaults, restructurings, and potential contagion to other economies."),
    ("What happened in the Greek debt crisis?", "The Greek debt crisis from 2010 to 2018 involved multiple bailouts, severe austerity measures, and a 2012 restructuring that was the largest sovereign default in history."),
    ("What was the Latin American debt crisis?", "The Latin American debt crisis of the 1980s saw several countries including Mexico, Brazil, and Argentina unable to service their foreign debt, leading to the Brady Bond restructuring."),
    ("What is the Asian financial crisis?", "The 1997 Asian financial crisis began with the Thai baht collapse and spread across East Asia, leading to IMF bailouts and severe economic contractions in affected countries."),
    ("What is quantitative easing?", "Quantitative easing is an unconventional monetary policy where a central bank purchases government bonds or other financial assets to inject liquidity and lower long term interest rates."),
    ("What is tapering?", "Tapering is the gradual reduction of central bank asset purchases, signaling a move toward normalizing monetary policy. It can cause bond yields to rise."),
    ("What is the Federal Reserve's role in bond markets?", "The Federal Reserve conducts monetary policy through open market operations, buying and selling Treasury securities to influence short term interest rates."),
    ("What is the ECB's role in European debt?", "The European Central Bank manages monetary policy for the eurozone, conducts bond purchase programs like APP and PEPP, and provides liquidity facilities to banks."),
    ("What is sovereign bond market liquidity?", "Liquidity refers to how easily bonds can be bought or sold without significantly affecting their price. Treasury markets are among the most liquid in the world."),
    ("What is the role of primary dealers?", "Primary dealers are financial institutions authorized to trade directly with the central bank in government securities markets. They play a key role in debt issuance."),
    ("What is a bond auction?", "A bond auction is a method of selling government securities where investors submit competitive or non competitive bids. The issuer accepts bids to meet its financing needs."),
    ("What is the difference between fixed and floating rate debt?", "Fixed rate debt has a constant coupon rate throughout its life, while floating rate debt has coupons that reset periodically based on a reference rate like LIBOR or SOFR."),
    ("What is interest rate swap?", "An interest rate swap is a derivative contract where two parties exchange interest rate payments, typically fixed for floating, to manage interest rate exposure."),
    ("What is a currency swap?", "A currency swap is a derivative contract where two parties exchange principal and interest payments in different currencies, used to manage foreign exchange risk."),
    ("What is cross currency basis swap?", "A cross currency basis swap exchanges floating rate payments in one currency for floating rate payments in another currency, reflecting funding cost differentials."),
    ("What is the role of IMF in sovereign debt?", "The IMF provides financial assistance, policy advice, and technical support to countries facing debt difficulties, often as part of adjustment programs."),
    ("What is an IMF program?", "An IMF program is a set of economic policies and reforms that a country agrees to implement in exchange for financial assistance from the International Monetary Fund."),
    ("What is conditionality in IMF lending?", "Conditionality refers to the policy requirements that IMF member countries must agree to when receiving financial assistance, aimed at resolving balance of payments problems."),
    ("What is the World Bank's role in sovereign debt?", "The World Bank provides development financing, technical assistance, and policy advice to developing countries, often supporting debt management capacity building."),
    ("What is the Sustainable Development Goals funding?", "SDG funding involves financing through bonds, loans, and grants to support the 17 UN Sustainable Development Goals addressing poverty, inequality, and climate change."),
    ("What is a catastrophe bond?", "A catastrophe bond is a risk linked security that transfers natural disaster risk from an issuer to investors. If a specified event occurs, principal is reduced or forgiven."),
    ("What is social impact bonding?", "Social impact bonding, or pay for success contracts, involves private investors funding social programs with returns tied to achieving specific measurable outcomes."),
    ("What is sustainable finance?", "Sustainable finance integrates environmental, social, and governance factors into investment decisions and financial services to support long term economic development."),
    ("What is ESG investing?", "ESG investing considers environmental, social, and governance criteria alongside financial factors to evaluate companies and countries for investment sustainability."),
    ("What is the carbon credit market?", "The carbon credit market trades permits to emit greenhouse gases. Companies and countries buy and sell credits to manage their carbon footprint and meet emission targets."),
    ("What is climate risk for sovereign debt?", "Climate risk affects sovereign debt through physical risks like natural disasters and transition risks from policy changes toward low carbon economies."),
    ("What is nature based solutions financing?", "Financing nature based solutions involves investing in ecosystem restoration, conservation, and sustainable land use to address climate change and biodiversity loss."),
    ("What is the role of rating agencies in EM debt?", "Rating agencies like S&P, Moody's, and Fitch assess emerging market sovereign creditworthiness, influencing capital flows, borrowing costs, and investor demand."),
    ("What is the difference between EM and DM debt?", "Emerging market debt has higher yields, greater volatility, and more currency risk compared to developed market debt, reflecting weaker institutions and higher growth potential."),
    ("What is capital flow volatility?", "Capital flow volatility refers to sudden and large movements of money in and out of countries, which can destabilize exchange rates and debt markets."),
    ("What is the carry trade?", "The carry trade borrows in a low interest rate currency and invests in a higher yielding currency, profiting from the interest rate differential."),
    ("What is the impossible trinity?", "The impossible trinity, or trilemma, states that a country cannot simultaneously maintain a fixed exchange rate, free capital movement, and independent monetary policy."),
    ("What is reserve accumulation?", "Reserve accumulation is the building up of foreign currency reserves by central banks to manage exchange rates, provide liquidity, and build confidence."),
    ("What is a currency peg?", "A currency peg fixes a country's exchange rate to another currency or basket of currencies, providing stability but limiting monetary policy flexibility."),
    ("What is sovereign default?", "Sovereign default occurs when a government fails to meet its debt obligations on time, either by missing payments or formally repudiating the debt."),
    ("What is hair cut in debt restructuring?", "A haircut in debt restructuring is the reduction in the face value of debt. Creditors accept less than the full amount owed to help the debtor recover."),
    ("What is holdout risk?", "Holdout risk is the danger that some creditors refuse to participate in debt restructuring, potentially suing for full repayment and undermining the process."),
    ("What is collective action clause?", "A collective action clause in bond contracts allows a supermajority of bondholders to agree to debt restructuring terms that bind all holders."),
    ("What is pari passu?", "Pari passu means equal treatment. In sovereign debt, it ensures that all creditors in the same class receive equal payment without preference."),
    ("What is the sovereign debt restructuring mechanism?", "The SDRM is a proposed international framework for orderly sovereign debt restructuring, advocated by the IMF to fill gaps in the current system."),
    ("What is vulture fund litigation?", "Vulture funds buy distressed sovereign debt at deep discounts and then sue for full repayment in foreign courts, potentially undermining debt restructuring efforts."),
    ("What is bilateral vs multilateral debt?", "Bilateral debt is owed to individual creditor countries, while multilateral debt is owed to international organizations like the IMF, World Bank, and regional development banks."),
    ("What is external vs domestic debt?", "External debt is owed to foreign creditors and often in foreign currency, while domestic debt is owed to local investors and denominated in the local currency."),
    ("What is short term vs long term debt?", "Short term debt matures in one year or less and carries rollover risk, while long term debt has maturities beyond one year and typically carries higher interest rates."),
    ("What is the debt ceiling?", "The debt ceiling is a legal limit on the total amount of money the US government can borrow, set by Congress and periodically raised or suspended."),
    ("What is the debt to GDP ratio threshold?", "The Maastricht Treaty sets 60 percent of GDP as a reference threshold for EU member states, though many countries operate above or below this benchmark."),
    ("What is gross financing needs?", "Gross financing needs represent the total amount a government must borrow in a given year, including to fund deficits and roll over maturing debt."),
    ("What is the debt service to revenue ratio?", "The debt service to revenue ratio measures what share of government revenue goes toward paying interest and principal on existing debt, indicating fiscal sustainability."),
    ("What is the rule of law in sovereign debt?", "The rule of law ensures that debt contracts are enforceable, creditor rights are protected, and restructuring processes follow established legal principles."),
    ("What is investor confidence in sovereign debt?", "Investor confidence reflects the trust that creditors have in a government's ability and willingness to repay its debt obligations on time and in full."),
    ("What is market access for sovereign borrowers?", "Market access is a government's ability to raise funds by issuing debt in international capital markets on reasonable terms and conditions."),
    ("What is the cost of borrowing?", "The cost of borrowing is the total expense of debt issuance, including coupon payments, issuance costs, and any premiums or discounts from par value."),
    ("What is debt maturity profile?", "The maturity profile shows the distribution of debt repayment obligations over time, helping manage rollover risk and interest rate exposure."),
    ("What is a bullet maturity?", "A bullet maturity is a bond where the entire principal is repaid at once on the maturity date, as opposed to amortizing bonds with periodic principal repayments."),
    ("What is a sinking fund?", "A sinking fund requires the issuer to retire a portion of the bond issue periodically before maturity, reducing redemption risk and providing regular market supply."),
    ("What is callability?", "A callable bond gives the issuer the right to redeem the bond before maturity, typically when interest rates fall, allowing refinancing at lower rates."),
    ("What is putability?", "A putable bond gives the holder the right to sell the bond back to the issuer before maturity, typically when interest rates rise, providing downside protection."),
    ("What is credit enhancement?", "Credit enhancement improves the creditworthiness of a debt issuance through guarantees, insurance, collateral, or structural features like seniority."),
    ("What is a sovereign guarantee?", "A sovereign guarantee is a commitment by the government to repay debt issued by another entity, such as a state owned enterprise or subnational government."),
    ("What is subnational debt?", "Subnational debt is borrowing by regional, state, or local governments, often with different legal frameworks and risk profiles than central government debt."),
    ("What is public private partnership financing?", "PPPs involve collaboration between government and private sector to finance, build, and operate infrastructure, often using structured debt instruments."),
    ("What is infrastructure bond financing?", "Infrastructure bonds are debt instruments issued to fund specific infrastructure projects like transportation, energy, water, and telecommunications."),
    ("What is a development finance institution?", "DFIs are government backed institutions that provide financing for development projects in developing countries, often with concessional terms."),
    ("What is concessional lending?", "Concessional lending provides loans with below market interest rates, longer grace periods, and extended maturities, typically from multilateral institutions."),
    ("What is blended finance?", "Blended finance combines development capital with private investment to fund sustainable development, using tools like guarantees and first loss tranches."),
    ("What is debt for nature swap?", "A debt for nature swap is an agreement where a portion of a developing country's debt is forgiven in exchange for commitments to fund environmental conservation."),
    ("What is the role of transparency in debt management?", "Transparency in debt management involves publishing comprehensive data on debt levels, composition, and risks to build investor confidence and enable market discipline."),
    # ── Extended QA pairs (v3) ────────────────────────────────────────
    ("What is a sovereign bond?", "A sovereign bond is a debt instrument issued by a national government to finance spending. It promises regular coupon payments and return of principal at maturity."),
    ("What is the bid ask spread on bonds?", "The bid ask spread is the difference between the price a buyer will pay and the price a seller will accept. Tighter spreads indicate more liquid markets."),
    ("What is bond pricing?", "Bond pricing calculates the present value of a bond's future cash flows, including coupon payments and principal repayment, discounted at the prevailing market yield."),
    ("What is par value?", "Par value, or face value, is the amount a bond will be worth at maturity. Bonds trade at par, at a premium above par, or at a discount below par."),
    ("What is a premium bond?", "A premium bond trades above its par value because its coupon rate is higher than the prevailing market interest rate for similar bonds."),
    ("What is a discount bond?", "A discount bond trades below its par value because its coupon rate is lower than the prevailing market interest rate for similar bonds."),
    ("What is current yield calculation?", "Current yield equals the annual coupon payment divided by the bond's current market price. It measures the income return relative to the price paid for the bond."),
    ("What is the relationship between bond prices and yields?", "Bond prices and yields move inversely. When market interest rates rise, existing bond prices fall, and when rates fall, bond prices rise."),
    ("What is interest rate risk?", "Interest rate risk is the risk that changes in market interest rates will affect a bond's price. Longer duration bonds have greater interest rate risk."),
    ("What is reinvestment risk?", "Reinvestment risk is the risk that coupon payments received from a bond will have to be reinvested at a lower interest rate than the original bond yield."),
    ("What is call risk?", "Call risk is the risk that a callable bond will be redeemed early by the issuer when interest rates fall, forcing the investor to reinvest at lower yields."),
    ("What is credit analysis?", "Credit analysis evaluates the creditworthiness of a bond issuer by examining financial statements, economic conditions, fiscal policy, and institutional strength."),
    ("What is a credit score for countries?", "A sovereign credit score assigned by rating agencies reflects the likelihood of debt repayment. It ranges from AAA for the highest quality to D for default."),
    ("What is the sovereign credit cycle?", "The sovereign credit cycle describes how countries move through phases of credit improvement, peak quality, deterioration, and potential default or restructuring."),
    ("What is fiscal space?", "Fiscal space is the room a government has to increase spending or cut taxes without endangering its debt sustainability or losing market access."),
    ("What is the debt dynamics equation?", "The debt dynamics equation shows how the debt to GDP ratio changes based on the interest rate, growth rate, primary balance, and stock flow adjustments."),
    ("What is the interest rate growth differential?", "The interest rate growth differential, or r minus g, determines whether debt dynamics are favorable. When g exceeds r, debt ratios can decline even with deficits."),
    ("What is primary surplus?", "A primary surplus occurs when government revenue exceeds spending excluding interest payments. It indicates the government can service debt from current operations."),
    ("What is the fiscal rule?", "A fiscal rule is a permanent constraint on fiscal policy through numerical targets for budget deficits, debt, or spending, designed to ensure long term sustainability."),
    ("What is cyclically adjusted balance?", "The cyclically adjusted balance removes the effects of the business cycle from the budget balance, showing the underlying fiscal position at potential output."),
    ("What is the output gap?", "The output gap is the difference between actual GDP and potential GDP. A negative gap indicates slack in the economy, while a positive gap suggests overheating."),
    ("What is sovereign debt accounting?", "Sovereign debt accounting tracks the issuance, servicing, and repayment of government obligations using accrual or cash based accounting standards."),
    ("What is the Government Finance Statistics framework?", "GFS is the IMF standard for fiscal data, classifying transactions by function and economic type, enabling cross country comparisons of fiscal positions."),
    ("What is the medium term debt management strategy?", "A medium term debt management strategy sets targets for debt composition including maturity structure, currency mix, and investor base over a three to five year horizon."),
    ("What is the cost risk framework?", "The cost risk framework balances minimizing expected borrowing costs against controlling risk from interest rate, rollover, and currency exposures."),
    ("What is the tactical management of debt?", "Tactical debt management involves short term decisions about issuance timing, instrument selection, and market positioning to exploit market conditions."),
    ("What is the benchmark bond approach?", "The benchmark bond approach creates a representative bond with standard features to serve as a reference point for pricing and trading other bonds."),
    ("What is on the run vs off the run bonds?", "On the run bonds are the most recently issued securities of a given maturity, while off the run bonds are older issues. On the run bonds are more liquid."),
    ("What is the liquidity premium?", "The liquidity premium compensates investors for holding less liquid securities. Less liquid bonds must offer higher yields to attract buyers."),
    ("What is the term premium?", "The term premium is the extra yield investors demand for holding longer term bonds instead of rolling over short term bonds. It compensates for duration risk."),
    ("What is the expectations hypothesis?", "The expectations hypothesis states that long term bond yields equal the average of expected future short term rates, plus a potential term premium."),
    ("What is the preferred habitat theory?", "The preferred habitat theory suggests investors have maturity preferences but will shift to other maturities if adequately compensated by higher yields."),
    ("What is market segmentation theory?", "Market segmentation theory holds that bonds of different maturities are distinct markets with separate supply and demand, with limited substitution between them."),
    ("What is a bootstrapping yield curve?", "Bootstrapping constructs a zero coupon yield curve from coupon bearing bond prices by sequentially solving for each maturity's spot rate."),
    ("What is the Nelson Siegel model?", "The Nelson Siegel model fits the yield curve using three parameters representing the level, slope, and curvature of the term structure."),
    ("What is the Svensson extension?", "The Svensson extension adds a fourth parameter to the Nelson Siegel model, allowing for an additional hump to better fit complex yield curve shapes."),
    ("What is a par yield curve?", "The par yield curve shows the yields at which bonds of each maturity would trade at par value. It is derived from the zero coupon yield curve."),
    ("What is a forward rate?", "A forward rate is the implied interest rate for a future period, derived from current spot rates. It reflects market expectations of future interest rate levels."),
    ("What is a forward yield curve?", "The forward yield curve plots implied future short term interest rates across different maturities, derived from the current spot yield curve."),
    ("What is yield curve flattening?", "Yield curve flattening occurs when the spread between long term and short term yields narrows, often signaling expectations of slower economic growth."),
    ("What is yield curve steepening?", "Yield curve steepening occurs when the spread between long term and short term yields widens, often indicating expectations of economic recovery or rising inflation."),
    ("What is the butterfly spread?", "The butterfly spread is a trade that profits from changes in the curvature of the yield curve, typically using a combination of short, medium, and long term bonds."),
    ("What is key rate duration?", "Key rate duration measures a bond's sensitivity to a change in yield at a specific maturity point along the yield curve, rather than a parallel shift."),
    ("What is convexity adjustment?", "The convexity adjustment accounts for the curvature in the price yield relationship, providing a more accurate estimate of price changes than duration alone."),
    ("What is the carry of a bond?", "The carry of a bond is the return earned from holding the bond, including coupon income and any roll down the yield curve as the bond approaches maturity."),
    ("What is a barbell bond strategy?", "A barbell strategy concentrates bond holdings in short and long maturities, avoiding intermediate maturities, to capture term premium while maintaining flexibility."),
    ("What is a bullet bond strategy?", "A bullet strategy concentrates bond holdings in a single maturity or narrow range, targeting a specific investment horizon and reducing complexity."),
    ("What is a ladder bond strategy?", "A ladder strategy distributes bond holdings evenly across maturities, providing regular cash flow and reducing reinvestment risk through diversification."),
    ("What is asset liability matching?", "Asset liability matching, or immunization, structures a bond portfolio so that its duration matches the liability duration, protecting against interest rate changes."),
    ("What is cash flow matching?", "Cash flow matching pairs specific bonds with specific future liabilities, ensuring that coupon and principal payments align with payment obligations."),
    ("What is the liability driven investing approach?", "LDI focuses on matching a portfolio's assets with specific future liabilities, prioritizing risk reduction over return maximization."),
    ("What is the asset allocation for debt portfolios?", "Debt portfolio asset allocation determines the mix across government bonds, corporate bonds, inflation linked securities, and other fixed income instruments."),
    ("What is inflation linked bonds?", "Inflation linked bonds adjust their principal and coupon payments based on an inflation index, protecting investors against erosion of purchasing power."),
    ("What are TIPS?", "Treasury Inflation Protected Securities are US government bonds that adjust their principal value based on the Consumer Price Index, providing inflation protection."),
    ("What is breakeven inflation?", "Breakeven inflation is the difference between nominal and inflation linked bond yields of the same maturity, representing the market's expected inflation rate."),
    ("What is real vs nominal yield?", "The real yield is the return on a bond after adjusting for inflation. The nominal yield is the stated yield before inflation adjustment."),
    ("What is the Fisher equation?", "The Fisher equation states that the nominal interest rate approximately equals the real interest rate plus expected inflation. It links nominal and real rates."),
    ("What is floating rate note pricing?", "Floating rate notes reset their coupon periodically based on a reference rate like SOFR. They trade near par between reset dates."),
    ("What is a put option on bonds?", "A put option on a bond gives the holder the right to sell the bond back to the issuer at a specified price before maturity."),
    ("What is an interest rate cap?", "An interest rate cap is a derivative that provides payments when a reference rate exceeds a specified strike rate, limiting floating rate borrowing costs."),
    ("What is an interest rate floor?", "An interest rate floor is a derivative that provides payments when a reference rate falls below a specified strike rate, protecting floating rate investors."),
    ("What is an interest rate collar?", "An interest rate collar combines a cap and a floor, limiting both upside and downside interest rate exposure within a specified range."),
    ("What is a swaption?", "A swaption is an option on an interest rate swap, giving the holder the right but not the obligation to enter into a swap at specified terms."),
    ("What is the Black model for bond options?", "The Black model prices European options on bond futures using the forward bond price, volatility, and the risk free rate to calculate option values."),
    ("What is the Heath Jarrow Morton framework?", "HJM is a mathematical framework for modeling the entire yield curve evolution, ensuring no arbitrage by specifying dynamics of forward rates."),
    ("What is the Hull White model?", "The Hull White model is a short rate model that fits the initial yield curve and allows mean reversion, used for pricing interest rate derivatives."),
    ("What is the Heston model?", "The Heston model is a stochastic volatility model used to price options, accounting for the volatility smile and correlations between asset price and volatility."),
    ("What is volatility smile?", "The volatility smile is the pattern where out of the money options have higher implied volatility than at the money options, suggesting the Black Scholes model is incomplete."),
    ("What is model risk in debt management?", "Model risk is the risk that financial models used for pricing, risk management, or decision making produce incorrect results due to flawed assumptions or implementation."),
    ("What is backtesting?", "Backtesting evaluates a trading or risk management strategy by applying it to historical data to see how it would have performed under past market conditions."),
    ("What is machine learning in bond markets?", "Machine learning techniques like neural networks, random forests, and gradient boosting are used for yield prediction, credit scoring, and trade execution optimization."),
    ("What is natural language processing in finance?", "NLP analyzes financial text like news, reports, and filings to extract sentiment, identify risks, and generate insights for investment decisions."),
    ("What is reinforcement learning for trading?", "Reinforcement learning trains agents to make sequential trading decisions by maximizing cumulative rewards through trial and error in simulated market environments."),
    ("What is the efficient market hypothesis?", "EMH states that asset prices fully reflect all available information, making it impossible to consistently earn above market returns through analysis or timing."),
    ("What is behavioral finance?", "Behavioral finance studies how psychological biases like overconfidence, loss aversion, and herding affect investor decisions and market outcomes."),
    ("What is the disposition effect?", "The disposition effect is the tendency of investors to sell winning investments too early and hold losing investments too long, driven by loss aversion."),
    ("What is the equity premium puzzle?", "The equity premium puzzle refers to the historically high excess return of stocks over bonds, which is difficult to explain using standard economic models."),
    ("What is the Tobin tax?", "The Tobin tax is a proposed tax on foreign exchange transactions to reduce currency speculation and generate revenue for international development."),
    ("What is capital controls?", "Capital controls are government restrictions on the flow of money in and out of a country, used to manage exchange rates and prevent financial instability."),
    ("What is the impossible trinity in practice?", "In practice, countries choose two of the three impossible trinity goals: most developed economies choose free capital flows and independent monetary policy with floating rates."),
    ("What is sterilized intervention?", "Sterilized intervention occurs when a central bank buys or sells foreign currency but offsets the effect on the domestic money supply through open market operations."),
    ("What is the balance of payments?", "The balance of payments records all economic transactions between residents of a country and the rest of the world, including trade, investment, and transfers."),
    ("What is the current account deficit?", "A current account deficit means a country imports more goods, services, and capital than it exports, requiring foreign financing through capital inflows."),
    ("What is external debt sustainability?", "External debt sustainability assesses whether a country can service its foreign currency debt without requiring future default, restructuring, or excessive adjustment."),
    # ── Restructuring Case Studies ─────────────────────────────────────
    ("What happened in the Argentine debt crisis?", "Argentina defaulted on $93 billion in 2001, the largest sovereign default at the time. It resolved through a 2005 and 2010 exchange offering 30 to 35 cents on the dollar, with holdout creditors winning $1.3 billion in US courts in 2014."),
    ("What was the Ecuador 2020 debt restructuring?", "Ecuador restructured $17.4 billion in bonds in 2020 during COVID, exchanging for new bonds at 55 cents on the dollar with 5 year maturity extension and reduced coupons, saving $11 billion in debt service."),
    ("What happened in the Zambia debt default?", "Zambia defaulted in November 2020 on $17 billion in external debt, becoming the first COVID era African default. Restructuring under the G20 Common Framework was delayed by disputes over Chinese creditor treatment."),
    ("What was the Sri Lanka 2022 crisis?", "Sri Lanka defaulted in May 2022 amid foreign reserve exhaustion, with $51 billion in external debt. An IMF program was approved in March 2023 with restructuring of Chinese, Paris Club, and commercial creditor claims."),
    ("What is the Puerto Rico debt crisis?", "Puerto Rico defaulted on $74 billion in bonds and $49 billion in pensions beginning in 2016. PROMESA established a fiscal oversight board, and a 2022 restructuring plan reduced debt by $30 billion."),
    ("What happened in the Russian debt moratorium?", "Russia imposed a 2022 moratorium on Eurobond payments in foreign currency following sanctions, effectively engineering a selective default. Coupon payments were made in rubles to domestic holders."),
    ("What was the Uruguay 2003 restructuring?", "Uruguay restructured $5.4 billion in bonds in 2003 through a preemptive exchange before default, offering 87 to 92 cents on the dollar. It was considered a successful market friendly approach."),
    ("What is the Lebanese debt crisis?", "Lebanon defaulted on $1.2 billion in Eurobonds in March 2020, its first ever default. The crisis involved the central bank's financial engineering schemes, capital controls, and negotiations with the IMF for a $3 billion program."),
    ("What happened in the Belize 2021 restructuring?", "Belize restructured $553 million in super bonds in 2021 at a 55 percent haircut, one of the deepest sovereign restructurings. The deal was linked to a marine conservation initiative for debt-for-nature swap."),
    ("What is the Chad debt restructuring?", "Chad completed restructuring in 2024 under the G20 Common Framework, with debt relief from China and commercial creditors, linked to IMF program conditions and private creditor comparability of treatment."),
    # ── Bond Market Mechanics ─────────────────────────────────────────
    ("How are bonds traded?", "Bonds trade over the counter through dealer networks and electronic platforms. Major exchanges list some bonds, but most sovereign debt trades directly between dealers and institutional investors."),
    ("What is the settlement cycle for bonds?", "Government bonds typically settle on T+1 or T+2 business days after the trade date. US Treasuries settled T+1 as of May 2024. Eurobonds typically settle T+2."),
    ("What is a ISIN code?", "An International Securities Identification Number is a 12 character alphanumeric code that uniquely identifies a specific financial security, used for clearing and settlement of bond trades."),
    ("What is a CUSIP?", "A CUSIP is a 9 character alphanumeric identifier assigned to North American financial securities, used for trade settlement and clearing in US and Canadian markets."),
    ("What is book building?", "Book building is a price discovery process where the issuer collects non binding bids from investors before setting the final price and allocation for a new bond issuance."),
    ("What is a green shoe option?", "A green shoe option allows the issuer to increase the size of a bond offering by up to 15 percent after initial pricing, providing flexibility to meet excess demand."),
    ("What is a tap issuance?", "A tap issuance adds new supply to an existing bond issue, creating a larger benchmark. It allows issuers to meet demand without creating entirely new securities."),
    ("What is a buyback program?", "A buyback program involves the issuer repurchasing outstanding bonds before maturity, typically to reduce debt, manage maturity profile, or create savings from below par purchases."),
    ("What is bond indexing?", "Bond indexing involves creating portfolio replicas that track specific bond indices like the Bloomberg Aggregate or JP Morgan EMBI, used for passive investment strategies."),
    ("What is a benchmark bond?", "A benchmark bond is a highly liquid, recently issued security that serves as a reference point for pricing other bonds. It typically has a standard maturity like 2, 5, 10, or 30 years."),
    ("What is the repo market for bonds?", "The repo market allows bond holders to borrow cash by selling bonds with an agreement to repurchase them at a specified price and date, serving as short term secured financing."),
    ("What is securities lending?", "Securities lending involves temporarily transferring bonds to borrowers who pay collateral, enabling short selling and liquidity provision in bond markets."),
    # ── Risk Management Advanced ──────────────────────────────────────
    ("What is basis risk?", "Basis risk is the risk that the hedge instrument and the asset being hedged do not move perfectly in sync, leaving residual exposure after hedging."),
    ("What is convexity risk?", "Convexity risk is the additional price risk from large interest rate movements that duration alone cannot capture, particularly significant for long duration bonds."),
    ("What is curve risk?", "Curve risk is the risk that different parts of the yield curve move by different amounts, affecting portfolios with bonds at multiple maturities differently."),
    ("What is gap risk?", "Gap risk is the risk that interest rates change between the repricing dates of assets and liabilities, creating maturity mismatches in fixed income portfolios."),
    ("What is prepayment risk?", "Prepayment risk is the risk that a bond issuer will repay principal earlier than expected, typically when interest rates fall, forcing reinvestment at lower yields."),
    ("What is call risk for bond investors?", "Call risk is the risk that an issuer will redeem callable bonds when interest rates decline, capping upside returns and forcing reinvestment at lower prevailing yields."),
    ("What is extension risk?", "Extension risk is the opposite of prepayment risk, occurring when bonds are called less frequently than expected in rising rate environments, extending effective duration."),
    ("What is credit migration risk?", "Credit migration risk is the risk that an issuer's credit rating will change over time, affecting bond prices and portfolio valuations."),
    ("What is concentration risk?", "Concentration risk arises from having too much exposure to a single issuer, sector, country, or maturity, increasing vulnerability to specific adverse events."),
    ("What is counterparty risk?", "Counterparty risk is the risk that the other party in a financial transaction will default before the transaction is settled, relevant for derivatives and repo trades."),
    ("What is wrong way risk?", "Wrong way risk occurs when counterparty credit quality deteriorates at the same time the exposure to that counterparty increases, amplifying potential losses."),
    ("What is liquidity coverage ratio?", "The LCR requires banks to hold enough high quality liquid assets to cover 30 days of net cash outflows, affecting their demand for sovereign bonds as HQLA."),
    # ── Fiscal Policy Advanced ────────────────────────────────────────
    ("What is the fiscal multiplier?", "The fiscal multiplier measures the change in GDP resulting from a change in government spending or taxation. Multipliers above 1 indicate that fiscal stimulus more than offsets its cost."),
    ("What is Ricardian equivalence?", "Ricardian equivalence suggests that government borrowing and taxation are equivalent methods of financing, because rational taxpayers anticipate future taxes to repay debt."),
    ("What is the golden rule of public finance?", "The golden rule of public finance states that government should only borrow to invest, not to fund current spending, ensuring debt finances productive assets."),
    ("What is the debt brake?", "A debt brake is a fiscal rule that limits the growth of public debt, often expressed as a constitutional requirement to keep the debt to GDP ratio below a specified threshold."),
    ("What is structural deficit?", "The structural deficit is the budget deficit that would exist if the economy were operating at potential output, removing cyclical effects from the headline deficit."),
    ("What is the automatic stabilizer?", "Automatic stabilizers are fiscal mechanisms like progressive taxation and unemployment insurance that automatically adjust to economic conditions without explicit policy action."),
    ("What is fiscal cliff?", "The fiscal cliff refers to the simultaneous expiration of tax cuts and implementation of spending cuts that could sharply reduce the deficit but also contract the economy."),
    ("What is sequestration?", "Sequestration refers to automatic across the board spending cuts triggered when Congress fails to meet deficit reduction targets, as in the 2013 US Budget Control Act."),
    ("What is the debt ceiling standoff?", "A debt ceiling standoff occurs when political disagreements prevent raising the legal borrowing limit, threatening default on government obligations and creating market uncertainty."),
    ("What is quantitative fiscal policy?", "Quantitative fiscal policy uses precise numerical targets and rules to guide fiscal decisions, including expenditure ceilings, revenue floors, and deficit limits."),
    # ── Monetary Policy and Rates ─────────────────────────────────────
    ("What is the Taylor rule?", "The Taylor rule suggests how central banks should adjust interest rates in response to inflation and output gaps, providing a guideline for monetary policy stance."),
    ("What is forward guidance?", "Forward guidance is communication by central banks about the likely future path of monetary policy, influencing market expectations and longer term interest rates."),
    ("What is the zero lower bound?", "The zero lower bound is the constraint that nominal interest rates cannot fall much below zero, limiting the central bank's ability to stimulate the economy through rate cuts."),
    ("What is negative interest rate policy?", "Negative interest rate policy charges banks for holding excess reserves, pushing short term rates below zero to encourage lending and investment during severe downturns."),
    ("What is yield curve control?", "Yield curve control is a monetary policy tool where the central bank targets specific long term interest rates by committing to buy unlimited bonds at those levels."),
    ("What is the carry cost of holding bonds?", "The carry cost is the net cost of financing a bond position, calculated as the difference between the financing rate and the bond yield. Positive carry means earning more than paying."),
    ("What is the role of the BIS in sovereign debt?", "The Bank for International Settlements serves as a bank for central banks, facilitates international monetary cooperation, and publishes research on sovereign debt and financial stability."),
    ("What is LIBOR transition?", "The transition from LIBOR to alternative reference rates like SOFR in the US and EURIBOR reform in Europe affects trillions in financial contracts, including sovereign derivatives."),
    ("What is the Secured Overnight Financing Rate?", "SOFR is the US dollar interest rate benchmark based on overnight Treasury repo transactions, replacing LIBOR as the reference rate for floating rate instruments and derivatives."),
    # ── Country-Specific Practices ────────────────────────────────────
    ("How does Japan manage its debt?", "Japan manages the world's largest debt to GDP ratio at over 260 percent through domestic financing, Bank of Japan yield curve control, and strong domestic investor base holding 90 percent of JGBs."),
    ("How does China issue sovereign debt?", "China issues sovereign bonds through the Ministry of Finance, with both domestic CGBs and offshore USD dim sum bonds. The PBOC manages monetary policy while the MOF handles debt issuance."),
    ("How does India manage its debt?", "India's debt management involves a mix of dated securities, Treasury bills, and small savings schemes. The RBI conducts auctions on behalf of the government with a developing yield curve strategy."),
    ("How does Brazil manage its debt?", "Brazil issues inflation linked NTN-B bonds, fixed rate Letras Tesouro Direto, and USD denominated Global bonds. The National Treasury manages a large domestic market with foreign investor participation."),
    ("How does South Africa manage its debt?", "South Africa issues bonds through the JSE exchange, with both domestic rand and offshore USD Eurobonds. The Treasury follows a medium term debt strategy with regular issuance calendars."),
    ("How does Turkey manage its debt?", "Turkey issues domestic lira bonds through transparent auctions and has reduced external debt reliance. The domestic market has grown significantly with diversified investor participation."),
    ("How does Mexico manage its debt?", "Mexico issues both domestic CETES and Bondes instruments and external sovereign bonds. The Treasury follows a regular issuance calendar with growing foreign investor participation in domestic bonds."),
    ("How does Saudi Arabia issue debt?", "Saudi Arabia issues sovereign debt through both domestic SAR bonds and international USD sukuk and conventional bonds, leveraging its high credit rating and oil revenue backing."),
    ("How does the UAE manage sovereign debt?", "The UAE issues federal government bonds and Abu Dhabi and Dubai have their own debt programs. The market has grown with regular issuances and increasing foreign investor access."),
    # ── Quantitative Methods ──────────────────────────────────────────
    ("What is dynamic programming for debt?", "Dynamic programming optimizes sequential debt management decisions by breaking complex problems into simpler subproblems, finding optimal issuance and maturity strategies over time."),
    ("What is stochastic optimization?", "Stochastic optimization finds solutions that perform well across multiple uncertain scenarios, used in debt management to create robust strategies under interest rate and growth uncertainty."),
    ("What is robust optimization?", "Robust optimization finds solutions that remain feasible and near optimal even under worst case parameter realizations, providing protection against model uncertainty in debt planning."),
    ("What is scenario optimization?", "Scenario optimization evaluates strategies across a discrete set of plausible future scenarios, selecting the strategy that performs best on average or minimizes worst case outcomes."),
    ("What is the Markowitz model applied to debt?", "The Markowitz mean variance framework applied to sovereign debt portfolios finds the optimal mix of bond instruments that minimizes risk for a target expected cost of borrowing."),
    ("What is factor modeling for bond returns?", "Factor models decompose bond returns into exposures to systematic factors like level, slope, curvature, credit spreads, and liquidity, enabling risk attribution and portfolio construction."),
    ("What is principal component analysis for yields?", "PCA identifies the dominant patterns of yield curve movement, typically explaining 95 plus percent of variance with three factors representing level, slope, and curvature movements."),
    ("What is bootstrap resampling for VaR?", "Bootstrap resampling estimates the distribution of VaR by randomly sampling historical returns with replacement, providing non parametric confidence intervals for risk estimates."),
    ("What is Monte Carlo tree search for debt?", "MCTS combines tree search with random sampling to explore debt management decision trees, useful for evaluating complex issuance strategies with multiple sequential choices."),
    ("What is reinforcement learning for debt?", "Reinforcement learning trains agents to make optimal debt management decisions by learning from simulated market environments, maximizing long term borrowing cost reduction."),
    # ── Legal and Institutional ───────────────────────────────────────
    ("What is sovereign immunity?", "Sovereign immunity protects governments from being sued in foreign courts without consent, affecting creditor ability to enforce debt contracts against defaulting sovereigns."),
    ("What is the Foreign Sovereign Immunities Act?", "The FSIA is the US law governing when foreign governments can be sued in US courts, including exceptions for commercial activity and arbitration agreements."),
    ("What is an arbitration clause in sovereign bonds?", "Arbitration clauses specify that disputes between the sovereign issuer and bondholders will be resolved through international arbitration rather than national courts."),
    ("What is an嵌入 option in sovereign bonds?", "Embedded options in sovereign bonds include call features allowing early redemption, put features allowing early sale, and conversion features changing the bond's terms."),
    ("What is an acceleration clause?", "An acceleration clause allows bondholders to demand immediate repayment of all outstanding principal if the issuer defaults on payments or breaches other conditions."),
    ("What is cross default?", "Cross default means that a default on one debt obligation triggers default on all other debt obligations, allowing creditors to declare all debt immediately due."),
    ("What is negative pledge?", "A negative pledge prevents the sovereign issuer from granting security to other creditors that would rank ahead of existing unsecured bonds, protecting bondholder interests."),
    ("What is pari passu enforcement?", "Pari passu enforcement ensures that all bonds in the same series rank equally in payment priority, preventing the issuer from preferring some creditors over others."),
    ("What is the rule against cherry picking?", "The rule against cherry picking prevents sovereign issuers from selectively paying some creditors while defaulting on others, promoting equitable treatment in restructuring."),
    ("What is the legal premise for sovereign lending?", "The legal premise is that sovereign debt contracts are governed by the laws specified in the bond indenture, typically English or New York law for international bonds."),
    # ── Modern Finance Topics ─────────────────────────────────────────
    ("What is fintech in sovereign debt management?", "Fintech applies technology to debt management including AI driven issuance optimization, blockchain settlement, digital bond platforms, and real time risk monitoring dashboards."),
    ("What is tokenized government debt?", "Tokenized government debt represents bond ownership on a blockchain, potentially improving transparency, reducing settlement times, and expanding investor access to sovereign securities."),
    ("What is central bank digital currency impact on bonds?", "CBDCs could affect sovereign bond markets by changing payment systems, potentially reducing transaction costs, and altering the monetary policy transmission mechanism."),
    ("What is climate aligned sovereign debt?", "Climate aligned sovereign debt links borrowing costs to climate targets, including green bonds, sustainability linked bonds, and debt-for-climate swaps."),
    ("What is the Just Energy Transition Partnership?", "JETPs are multi stakeholder financing arrangements helping coal dependent developing countries transition to clean energy, involving sovereign debt restructuring and concessional finance."),
    ("What is nature performance bonds?", "Nature performance bonds link sovereign debt service to measurable outcomes in biodiversity conservation and ecosystem restoration, creating financial incentives for environmental protection."),
    ("What is pandemicemic risk insurance?", "Pandemic risk insurance for sovereigns includes catastrophe bonds triggered by disease outbreaks, contingent credit facilities, and regional risk pooling mechanisms."),
    ("What is digital public infrastructure finance?", "DPI finance involves sovereign borrowing to fund digital identity, payment systems, and data exchange platforms, increasingly important for development finance."),
    ("What is the Bridgetown Initiative?", "The Bridgetown Initiative proposes reforming the international financial architecture to provide faster, larger scale financing for climate and development in vulnerable countries."),
    ("What is debt for climate swaps at scale?", "Debt for climate swaps at scale involve converting large portions of sovereign debt into climate commitments, with examples like Belize and Ecuador linking restructuring to marine conservation."),
    # ── Advanced Debt Strategies ──────────────────────────────────────
    ("What is liability management exercises?", "LMEs involve bondholders exchanging existing securities for new ones with modified terms, used by sovereigns to extend maturities, reduce coupons, or consolidate bond series."),
    ("What is a tender offer for bonds?", "A tender offer is a public offer to purchase outstanding bonds at a specified price, allowing the sovereign to retire debt voluntarily before maturity."),
    ("What is a consent solicitation?", "A consent solicitation asks bondholders to agree to changes in bond terms, typically in exchange for a fee, to enable liability management or restructuring."),
    ("What is an exchange offer?", "An exchange offer gives bondholders new securities in return for existing ones, often used as part of debt restructuring to modify terms across a bond series."),
    ("What is the cost of debt analysis?", "Cost of debt analysis calculates the all in cost of borrowing including coupon payments, issuance costs, buyback gains or losses, and foreign exchange effects."),
    ("What is debt service forecasting?", "Debt service forecasting projects future interest and principal payments based on current debt composition, expected issuance, and interest rate scenarios."),
    ("What is maturity wall risk?", "Maturity wall risk is the danger that large amounts of debt mature simultaneously, creating refinancing pressure and potential market access challenges."),
    ("What is the debt maturity ladder?", "The debt maturity ladder distributes repayment obligations across different time periods to avoid concentration of maturities and manage rollover risk systematically."),
    ("What is the marginal cost of borrowing?", "The marginal cost of borrowing measures the incremental cost of issuing additional debt, considering market impact, investor demand, and portfolio effects."),
    ("What is the average cost of debt?", "The average cost of debt is the total annual debt service divided by total outstanding debt, providing a measure of the overall borrowing cost across the portfolio."),
    # ── International Institutions ────────────────────────────────────
    ("What is the IMF Article IV consultation?", "Article IV consultations are annual assessments of member countries' economic and financial policies, providing recommendations on fiscal, monetary, and structural policies."),
    ("What is the IMF Special Drawing Rights?", "SDRs are international reserve assets allocated to IMF member countries, usable for settling international payments and supplementing official reserves."),
    ("What is the World Bank IDA?", "The International Development Association provides concessional loans and grants to the world's poorest countries, with terms more favorable than the IBRD lending window."),
    ("What is the Paris Club agreement?", "Paris Club agreements follow principles including case by case treatment, consensus among creditors, conditionality, and comparability of treatment for debtor countries."),
    ("What is the G20 Common Framework?", "The G20 Common Framework for Debt Treatments provides a platform for restructuring official bilateral debt of the poorest countries, building on the Debt Service Suspension Initiative."),
    ("What is the Heavily Indebted Poor Countries initiative?", "HIPC provides debt relief to qualifying countries through the IMF and World Bank, requiring policy reforms and providing relief to restore debt sustainability."),
    ("What is the Multilateral Debt Relief Initiative?", "MDRI goes beyond HIPC by providing 100 percent debt relief on eligible debts from the IMF, IDA, and African Development Fund to qualifying countries."),
    ("What is the regional development bank role?", "Regional development banks like the ADB, AfDB, and IDB provide financing, technical assistance, and policy advice for development in their respective regions."),
    ("What is the role of the IFC in sovereign debt?", "The IFC mobilizes private investment in developing countries, complementing sovereign financing by funding private sector projects that support economic development."),
    ("What is blended finance from MDBs?", "MDB blended finance combines concessional and commercial capital to fund development projects, using guarantees, first loss tranches, and risk sharing to attract private investors."),
    # ── Data and Statistics ───────────────────────────────────────────
    ("What is the IMF World Economic Outlook?", "The WEO is a twice yearly report by the IMF providing analysis and projections of global economic developments, including debt, growth, and inflation forecasts for member countries."),
    ("What is the IMF Global Debt Database?", "The GDD compiles public and private debt data for 190 countries, providing the most comprehensive source of comparable sovereign and private debt statistics."),
    ("What is the World Bank International Debt Statistics?", "IDS provides comprehensive debt statistics for developing countries, covering external debt stocks, flows, and debt service payments from official and private creditors."),
    ("What is the BIS debt securities statistics?", "BIS publishes quarterly data on international and domestic debt securities markets, covering issuance, outstanding amounts, and yields across countries and sectors."),
    ("What is the OECD Sovereign Borrowing Outlook?", "The SO provides analysis of public debt management practices, borrowing needs, and debt strategies for OECD member countries and key non members."),
    ("What is the IMF Debt Sustainability Framework?", "The IMF DSF is a systematic approach to assess whether public debt is sustainable, combining quantitative projections with policy analysis and risk assessment."),
    ("What is the joint World Bank IMF debt sustainability framework?", "The joint framework assesses debt sustainability for low income countries, providing debt distress ratings and policy recommendations to maintain sustainable debt levels."),
    ("What is the IMF Fiscal Monitor?", "The Fiscal Monitor is a semi annual IMF report analyzing public finance developments, including deficits, debt, and fiscal policy across advanced and emerging economies."),
    ("What is the Global Financial Stability Report?", "The GFSR is a semi annual IMF assessment of global financial market conditions, risks, and policy implications for financial stability and sovereign debt markets."),
    ("What is the Bank for International Settlements?", "The BIS is an international financial institution owned by central banks, serving as a bank for central banks, conducting research, and facilitating monetary and financial stability cooperation."),
    # ── Quantive Platform Specific ────────────────────────────────────
    ("How does Quantive optimize debt portfolios?", "Quantive uses mixed integer linear programming, Monte Carlo simulation, and reinforcement learning to find optimal debt portfolios that minimize cost while controlling risk across maturity, currency, and interest rate dimensions."),
    ("What is Quantive DSA analysis?", "Quantive's DSA module implements the IMF Debt Sustainability Framework with automated threshold analysis, scenario projections, and early warning indicators for debt distress."),
    ("How does Quantive stress test debt portfolios?", "Quantive runs Monte Carlo stress tests simulating thousands of interest rate, growth, and exchange rate scenarios to evaluate portfolio resilience under extreme but plausible conditions."),
    ("What is Quantive maturity profiling?", "Quantive's maturity profiler analyzes debt composition across time buckets, calculating weighted average maturity, amortization schedules, and rollover risk concentrations."),
    ("How does Quantive handle fiscal rules?", "Quantive's fiscal rule engine tracks compliance with configurable rules including deficit limits, debt ceilings, and expenditure floors, with automated alerts when thresholds are approached."),
    ("What is Quantive transparency index?", "Quantive's transparency index scores countries on debt management disclosure practices, covering data publication, audit mechanisms, and institutional governance quality."),
    ("How does Quantive manage audit trails?", "Quantive maintains cryptographically signed immutable audit trails for all portfolio changes, optimization runs, and policy decisions, ensuring full accountability and regulatory compliance."),
    ("What is Quantive sovereign mode?", "Sovereign Mode runs Quantive entirely within a government's own infrastructure, ensuring data sovereignty, no external data flows, and compliance with national security requirements."),
    ("How does Quantive procurement work?", "Quantive's procurement module evaluates vendor proposals, tracks pilot programs, and manages the sovereign debt management platform procurement lifecycle for government clients."),
    ("What is Quantive AI advisor?", "Quantive AI advisor is a custom trained language model specialized in sovereign debt management, providing natural language analysis, recommendations, and portfolio insights to treasury officials."),
    ("How does Quantive handle currency risk?", "Quantive models currency risk using historical volatility, correlation analysis, and scenario stress testing across foreign currency debt portfolios, recommending hedging strategies."),
    ("What is Quantive outcome based pricing?", "Quantive charges based on measurable debt cost reduction achieved, aligning incentives so Quantive only profits when governments save money through better debt management."),
    ("How does Quantive model interest rate risk?", "Quantive calculates DV01, duration, convexity, and key rate durations for all instruments, running parallel shift and twist scenario analysis for interest rate risk management."),
    ("What is Quantive pilot program?", "Quantive pilot programs let governments test the platform on a subset of their debt portfolio, measuring real world performance before full deployment."),
    ("How does Quantive compare to Bloomberg Terminal?", "Quantive is purpose built for sovereign debt management while Bloomberg covers broader financial markets. Quantive offers specialized DSA, fiscal rules, and government-specific optimization."),
    ("What is Quantive case study generator?", "Quantive automatically generates detailed case studies from completed pilot programs, documenting methodology, results, and lessons learned for stakeholder communication."),
    ("How does Quantive handle data security?", "Quantive uses end-to-end encryption, role-based access control, immutable audit trails, and optional sovereign deployment to meet government security requirements."),
    ("What is Quantive interoperability module?", "Quantive's interoperability module converts between FpML, XBRL, SWIFT, and other financial data formats, enabling integration with existing government financial systems."),
    ("How does Quantive disaster recovery work?", "Quantive implements automated backups, geo-redundant storage, and documented recovery procedures to ensure business continuity for critical debt management operations."),
    ("What is Quantive SLA monitoring?", "Quantive monitors service level agreements with automated compliance tracking, breach detection, and service credit calculations to ensure platform reliability."),
    ("How does Quantive approval workflows work?", "Quantive implements multi-level approval workflows with configurable authorization chains, ensuring that critical debt management decisions receive appropriate review and sign-off."),
    ("What is Quantive model validation?", "Quantive validates optimization models through feasibility checks, optimality gap analysis, stability testing across multiple runs, and historical backtesting against past decisions."),
    ("How does Quantive agent system work?", "Quantive's agent system autonomously monitors markets, runs analyses, and executes approved actions within predefined parameters, with human approval required for high impact decisions."),
    ("What is Quantive interoperability?", "Quantive integrates with existing government financial systems through standard data formats, APIs, and automated data pipelines for seamless debt management workflow integration."),
    # ── Bond Mathematics ──────────────────────────────────────────────
    ("How do you calculate bond price?", "Bond price equals the present value of all future cash flows, calculated as the sum of each coupon payment discounted at the yield to maturity plus the present value of the face value."),
    ("How do you calculate yield to maturity?", "YTM is the discount rate that equates the bond's current price to the present value of its future cash flows. It is found through iterative numerical methods or financial calculators."),
    ("How do you calculate modified duration?", "Modified duration equals Macaulay duration divided by one plus the yield per period. It measures the percentage price change for a one unit change in yield."),
    ("How do you calculate DV01?", "DV01 equals modified duration multiplied by the bond price multiplied by 0.0001. It represents the dollar change in bond price for a one basis point change in yield."),
    ("How do you calculate convexity?", "Convexity is calculated as the second derivative of bond price with respect to yield, divided by the bond price. It measures the curvature of the price yield relationship."),
    ("How do you calculate Macaulay duration?", "Macaulay duration is the weighted average time to maturity of cash flows, where each time period is weighted by the present value of the cash flow at that time divided by the bond price."),
    ("How do you calculate current yield?", "Current yield equals the annual coupon payment divided by the current market price of the bond, showing the income return relative to the price paid."),
    ("How do you price a zero coupon bond?", "A zero coupon bond price equals the face value discounted at the yield to maturity for the remaining time to maturity, with no intermediate coupon payments."),
    ("How do you calculate par yield?", "Par yield is the coupon rate at which a bond would trade at par value, calculated as the weighted average of spot rates for each maturity up to the bond's term."),
    ("How do you calculate forward rates?", "Forward rates are derived from spot rates using the formula: forward rate equals the ratio of compounded long term rate to short term rate, annualized to the forward period."),
    # ── Credit Risk Modeling ──────────────────────────────────────────
    ("What is the Merton model for sovereign debt?", "The Merton model treats sovereign debt as a put option on the country's assets, where default occurs if asset value falls below the debt face value at maturity."),
    ("What is the KMV model?", "The KMV model extends Merton by estimating the probability of default from the distance to default, measuring how many standard deviations the asset value is from the default point."),
    ("What is CreditMetrics for sovereigns?", "CreditMetrics estimates the credit value at risk of a sovereign bond portfolio by modeling rating transitions and their impact on bond valuations across rating categories."),
    ("What is the Reduced Form model?", "Reduced form models estimate default probability from observable market prices and macroeconomic variables without modeling the underlying asset process explicitly."),
    ("What is the Structural model of default?", "Structural models link default to the sovereign's asset value relative to its debt obligations, providing economic intuition for credit risk based on balance sheet fundamentals."),
    ("What is CreditPortfolioView?", "CreditPortfolioView is a multi factor model that estimates portfolio credit risk by modeling rating transitions as a function of macroeconomic variables and country specific factors."),
    ("What is the expected loss formula?", "Expected loss equals probability of default multiplied by loss given default multiplied by exposure at default, providing the baseline credit risk measure for sovereign exposure."),
    ("What is the conditional probability of default?", "The conditional probability of default is the likelihood of default in a given period conditional on having survived to the beginning of that period, derived from hazard rate models."),
    ("What is a hazard rate model?", "Hazard rate models specify the instantaneous probability of default as a function of time and covariates, allowing for time varying default risk in sovereign debt analysis."),
    ("What is credit spread modeling?", "Credit spread modeling decomposes sovereign bond spreads into default risk premium, liquidity premium, and risk premium components using regression and structural models."),
    # ── Yield Curve Construction ──────────────────────────────────────
    ("How do you construct a yield curve?", "A yield curve is constructed by fitting a parametric function like Nelson Siegel to observed bond yields, ensuring no arbitrage and smooth interpolation between maturities."),
    ("What is the bootstrap method for yield curves?", "Bootstrapping sequentially solves for zero coupon rates at each maturity by using the prices of coupon bearing bonds, starting from the shortest maturity and working outward."),
    ("What is spline interpolation for yield curves?", "Spline interpolation fits piecewise polynomial functions to bond yields, providing smooth yield curves that pass exactly through observed market data points."),
    ("What is the Nelson Siegel model parameters?", "The Nelson Siegel model uses three parameters: beta1 for the level, beta2 for the slope, and beta3 for the curvature of the yield curve, with a decay parameter controlling the hump location."),
    ("What is the Svensson model?", "The Svensson model extends Nelson Siegel with a fourth parameter adding a second hump, providing better fit for complex yield curve shapes with multiple inflection points."),
    ("What is a theoretical yield curve?", "A theoretical yield curve is derived from arbitrage free pricing models that ensure consistent pricing of bonds across all maturities, eliminating relative value opportunities."),
    ("What is the spot rate curve?", "The spot rate curve shows yields on zero coupon bonds of different maturities, representing the pure time value of money without coupon reinvestment effects."),
    ("What is the par curve?", "The par curve shows yields on coupon bearing bonds that trade at par value for each maturity, commonly used as a reference for pricing new bond issuances."),
    ("What is the forward curve?", "The forward curve plots implied future short term interest rates derived from the current spot curve, reflecting market expectations for the path of interest rates."),
    ("What is the swap curve?", "The swap curve shows interest rate swap rates across maturities, often used as a benchmark for pricing floating rate debt and derivatives in lieu of government yields."),
    # ── Derivatives Pricing ───────────────────────────────────────────
    ("How do you price an interest rate swap?", "An interest rate swap is priced by calculating the present value of expected fixed rate payments minus floating rate payments, where the fixed rate is set to make the swap value zero at inception."),
    ("How do you price a swaption?", "A swaption is priced using the Black model adapted for swaps, with the swap rate as the underlying asset, volatility of swap rates, and the discount factor to the option expiry."),
    ("How do you price a cap or floor?", "Interest rate caps and floors are priced as portfolios of individual caplets or floorlets, each modeled as a call or put option on a forward rate using the Black model."),
    ("How do you price a currency swap?", "A currency swap is priced as the difference in present values of the two coupon streams in different currencies, plus the present value of the principal exchange at maturity."),
    ("How do you price a CDS on sovereign debt?", "A sovereign CDS is priced by equating the present value of premium leg payments to the present value of expected protection payouts, calibrated to market spread and recovery assumptions."),
    ("How do you calculate CDS spread?", "CDS spread is the annual premium rate paid by the protection buyer, calibrated so that the present value of premium payments equals the present value of expected default losses."),
    ("How do you calculate recovery rate?", "Recovery rate for sovereign CDS is typically modeled using historical restructuring data, ranging from 20 to 40 cents on the dollar depending on the legal framework and creditor treatment."),
    ("How do you calculate CVA for sovereign exposure?", "Credit valuation adjustment estimates the loss from counterparty default risk by calculating the expected exposure multiplied by the probability of default and loss given default."),
    ("How do you calculate wrong way CVA?", "Wrong way CVA accounts for the positive correlation between counterparty credit quality and exposure, typically occurring when the counterparty's credit deteriorates during market stress."),
    ("How do you calculate DVA for sovereign bonds?", "Debit valuation adjustment accounts for the issuer's own credit risk, reducing the liability by the expected loss from default from the issuer's perspective."),
    # ── Portfolio Construction ────────────────────────────────────────
    ("What is the liability driven investing for sovereigns?", "LDI matches sovereign asset portfolios with specific future payment obligations, using derivatives and cash bonds to hedge the present value of debt service liabilities."),
    ("What is the benchmark tracking error?", "Tracking error measures the standard deviation of portfolio returns relative to a benchmark index, indicating how closely the portfolio replicates the benchmark's performance."),
    ("What is the information ratio?", "The information ratio measures active return per unit of tracking error, indicating the skill of the portfolio manager in generating excess returns relative to benchmark risk."),
    ("What is the Treynor ratio?", "The Treynor ratio measures excess return per unit of systematic risk (beta), useful for evaluating sovereign debt portfolios in the context of market risk exposure."),
    ("What is the Sortino ratio?", "The Sortino ratio measures excess return per unit of downside deviation, focusing only on negative return volatility and providing a more targeted risk adjusted performance measure."),
    ("What is the Calmar ratio?", "The Calmar ratio measures return relative to maximum drawdown, indicating how much return is earned per unit of worst case peak to trough decline in portfolio value."),
    ("What is the Omega ratio?", "The Omega ratio calculates the probability weighted ratio of gains to losses above and below a threshold, providing a more complete risk measure than Sharpe or Sortino ratios."),
    ("What is portfolio immunization?", "Immunization matches the duration of assets and liabilities so that interest rate changes affect both sides equally, protecting the portfolio's funded status from rate movements."),
    ("What is cash flow matching for debt?", "Cash flow matching pairs specific bonds with specific future debt service payments, ensuring that coupon and principal receipts align exactly with obligation due dates."),
    ("What is horizon matching?", "Horizon matching combines cash flow matching for near term liabilities with duration matching for distant liabilities, balancing precision and cost efficiency in liability hedging."),
    # ── Market Microstructure ─────────────────────────────────────────
    ("What is bid ask spread for sovereign bonds?", "The bid ask spread represents the cost of immediately trading a bond, calculated as the difference between the dealer's ask price and bid price, reflecting liquidity and inventory risk."),
    ("What is market depth?", "Market depth measures the volume of bonds available at various price levels, indicating how much can be traded before significantly affecting the market price."),
    ("What is price impact?", "Price impact measures how much a bond's price moves in response to a trade, inversely related to market depth and directly related to trade size relative to outstanding supply."),
    ("What is order flow toxicity?", "Order flow toxicity measures the probability that informed traders are on the opposite side of a trade, potentially adverse selecting uninformed participants."),
    ("What is market making in sovereign bonds?", "Market making involves dealers continuously quoting bid and ask prices for sovereign bonds, earning the spread while managing inventory risk and competing with other dealers."),
    ("What is the role of primary dealers?", "Primary dealers are financial institutions authorized to participate directly in government bond auctions, providing liquidity, distributing new issues, and supporting market functioning."),
    ("What is interdealer market?", "The interdealer market is where primary dealers trade sovereign bonds among themselves, facilitating price discovery, inventory management, and efficient redistribution of risk."),
    ("What is electronic trading in sovereign bonds?", "Electronic trading platforms automate bond trading, improving price transparency, reducing transaction costs, and expanding access for smaller institutional investors."),
    ("What is all to all trading?", "All to all trading allows any market participant to trade with any other, bypassing traditional dealer intermediation and potentially reducing costs through direct matching."),
    ("What is trade repository reporting?", "Trade repository reporting requires market participants to report trade details to a central repository, improving market transparency and regulatory oversight of sovereign bond markets."),
    # ── Country Risk Analysis ─────────────────────────────────────────
    ("What is political risk assessment?", "Political risk assessment evaluates the likelihood and impact of political events on a sovereign's ability and willingness to service its debt obligations."),
    ("What is institutional quality scoring?", "Institutional quality scoring rates governance effectiveness, rule of law, regulatory quality, and control of corruption, correlating strongly with sovereign creditworthiness."),
    ("What is the World Bank governance indicators?", "The WGI measures six dimensions of governance including voice and accountability, political stability, government effectiveness, regulatory quality, rule of law, and control of corruption."),
    ("What is the Institutional Investor country credit rating?", "The Institutional Investor rating aggregates credit opinions from international bankers, providing a consensus assessment of sovereign credit quality for investment decisions."),
    ("What is the Euler Hermes country risk rating?", "Euler Hermes rates country risk for trade credit insurance, assessing political, commercial, and transfer risks that affect cross border transactions and investment."),
    ("What is the CDS implied default probability?", "CDS spreads imply a default probability calibrated to the spread level and assumed recovery rate, providing a market based forward looking measure of sovereign default risk."),
    ("What is sovereign bond spread decomposition?", "Spread decomposition breaks sovereign bond yields into the risk free rate, credit risk premium, liquidity premium, and risk premium to identify the drivers of borrowing costs."),
    ("What is the Grabbe model for EM spreads?", "The Grabbe model decomposes emerging market spreads into country specific factors including default risk, liquidity, and global risk appetite measured by VIX and US Treasury spreads."),
    ("What is the Caixin PMI for sovereign analysis?", "The Caixin PMI measures Chinese manufacturing activity, relevant for commodity exporters and countries with significant China trade exposure in sovereign debt analysis."),
    ("What is commodity price risk for sovereigns?", "Commodity price risk affects resource dependent economies through revenue volatility, terms of trade shocks, and fiscal balance pressure that impacts debt sustainability."),
    # ── Optimization Methods ──────────────────────────────────────────
    ("What is linear programming for debt?", "Linear programming finds optimal debt portfolios by minimizing a linear objective function subject to linear constraints, suitable for cost minimization with simple risk limits."),
    ("What is integer programming for debt?", "Integer programming handles discrete decisions like choosing specific bond instruments or lot sizes, where variables must be whole numbers representing individual securities."),
    ("What is mixed integer programming?", "MIP combines continuous and integer variables, allowing simultaneous optimization of portfolio weights and discrete issuance decisions in sovereign debt management."),
    ("What is quadratic programming for bonds?", "QP minimizes a quadratic objective function subject to linear constraints, commonly used for mean variance optimization of bond portfolios."),
    ("What is stochastic programming for debt?", "Stochastic programming optimizes decisions across multiple scenarios with associated probabilities, creating robust debt strategies that perform well under uncertainty."),
    ("What is dynamic programming for issuance?", "Dynamic programming optimizes sequential issuance decisions by solving backward from maturity, finding optimal timing and instrument choice at each step."),
    ("What is genetic algorithm optimization?", "Genetic algorithms use evolutionary principles of selection, crossover, and mutation to search for near optimal debt portfolios in complex, non convex solution spaces."),
    ("What is simulated annealing for bonds?", "Simulated annealing uses probabilistic acceptance of worse solutions to escape local optima, finding good solutions for complex debt portfolio optimization problems."),
    ("What is column generation for debt?", "Column generation efficiently solves large scale debt optimization problems by generating promising portfolio compositions iteratively rather than enumerating all possibilities."),
    ("What is the/Branch and bound method?", "Branch and bound systematically explores integer programming solutions by solving continuous relaxations and branching on integer variables, guaranteeing optimal integer solutions."),
    # ── Economic Indicators ───────────────────────────────────────────
    ("What is GDP growth and sovereign debt?", "GDP growth reduces the debt to GDP ratio by expanding the denominator, while recessions increase it through lower revenue and higher automatic stabilizer spending."),
    ("What is inflation's effect on sovereign debt?", "Inflation erodes the real value of nominal debt, benefiting issuers at the expense of creditors, but can also raise nominal yields and increase new borrowing costs."),
    ("What is the unemployment rate impact on debt?", "High unemployment reduces tax revenue and increases social spending, widening fiscal deficits and increasing borrowing needs that affect sovereign debt dynamics."),
    ("What is the trade balance impact on debt?", "Trade deficits require foreign financing through capital inflows, potentially increasing external debt exposure and currency risk in sovereign debt portfolios."),
    ("What is the current account and debt sustainability?", "Persistent current account deficits accumulate external debt, requiring either adjustment through currency depreciation or continued capital inflows that may prove volatile."),
    ("What is the fiscal impulse?", "Fiscal impulse measures the change in the structural fiscal balance, indicating whether fiscal policy is adding to or withdrawing from aggregate demand and affecting debt."),
    ("What is the debt tax?", "The debt tax is the implicit cost of servicing public debt, measured as interest payments as a share of GDP, representing resources diverted from productive spending."),
    ("What is the real interest rate on debt?", "The real interest rate adjusts the nominal rate for inflation, measuring the true economic cost of carrying debt and determining whether debt dynamics are favorable."),
    ("What is the primary deficit and debt dynamics?", "The primary deficit adds to the debt stock when positive, while a primary surplus reduces it. The debt dynamics equation shows how growth, interest rates, and the primary balance interact."),
    ("What is the stock flow adjustment?", "Stock flow adjustments capture the difference between predicted and actual debt changes, including privatization revenues, bank recapitalizations, and exchange rate effects on foreign currency debt."),
    # ── Institutional Frameworks ──────────────────────────────────────
    ("What is a debt management office structure?", "A DMO typically includes treasury operations, risk management, investor relations, research, and IT departments, with clear reporting lines to the finance ministry."),
    ("What is the Three Lines Model for DMOs?", "The Three Lines Model assigns risk management to business units (first line), independent risk oversight (second line), and internal audit (third line) for effective governance."),
    ("What is a debt management strategy?", "A debt management strategy is a medium term plan setting targets for debt composition including maturity profile, currency mix, investor base, and instrument types."),
    ("What is issuance calendar?", "An issuance calendar pre announces the timing, size, and types of upcoming bond auctions, providing transparency and predictability for market participants."),
    ("What is investor relations for sovereigns?", "Sovereign investor relations involves regular communication with bondholders through roadshows, investor meetings, and publications to maintain market confidence and access."),
    ("What is debt statistics publication?", "Regular publication of comprehensive debt statistics including composition, maturity profile, currency breakdown, and investor base builds transparency and market confidence."),
    ("What is the IMF ROSC for debt?", "IMF Reports on the Observance of Standards and Codes assess countries' adherence to data dissemination and fiscal transparency standards, including debt statistics."),
    ("What is the Lima Principles?", "The Lima Principles are guidelines for debt transparency endorsed by the IMF, promoting comprehensive, timely, and standardized public debt data disclosure."),
    ("What is the SDDS Plus?", "SDDS Plus is the IMF's enhanced data dissemination standard requiring countries to publish comprehensive economic and financial data including detailed debt statistics."),
    ("What is the XBRL reporting standard?", "XBRL is a standardized format for financial reporting that enables automated processing and comparison of fiscal and debt data across countries and reporting periods."),
    # ── Debt Instruments Advanced ─────────────────────────────────────
    ("What is a floating rate note?", "A floating rate note pays coupons that reset periodically based on a reference rate like SOFR or EURIBOR, trading near par between reset dates."),
    ("What is an inflation linked bond?", "Inflation linked bonds adjust principal and coupon payments based on an inflation index, protecting investors against erosion of purchasing power."),
    ("What are TIPS?", "Treasury Inflation Protected Securities are US government bonds that adjust their principal value based on the CPI, providing real return guarantees."),
    ("What is a green bond?", "A green bond is a fixed income instrument whose proceeds fund environmentally beneficial projects, following ICMA Green Bond Principles for transparency and impact reporting."),
    ("What is a sustainability bond?", "A sustainability bond funds projects with both environmental and social benefits, aligned with the Sustainability Bond Guidelines published by ICMA."),
    ("What is a social bond?", "A social bond raises proceeds for projects with positive social outcomes, such as affordable housing, healthcare, or education, following ICMA Social Bond Principles."),
    ("What is a catastrophe bond?", "A catastrophe bond transfers natural disaster risk to capital markets investors, with principal reduction triggered by specified catastrophic events."),
    ("What is a revenue bond?", "A revenue bond is backed by specific government revenue streams like tolls or taxes, rather than the full faith and credit of the sovereign issuer."),
    ("What is a covered bond?", "A covered bond is a debt obligation secured by a dedicated pool of assets, providing dual recourse to both the issuer and the asset pool."),
    ("What is a sukuk?", "A sukuk is an Islamic finance instrument structured to comply with Sharia law, providing returns through asset ownership rather than interest payments."),
    # ── Risk Budgeting ────────────────────────────────────────────────
    ("What is risk budgeting for sovereign debt?", "Risk budgeting allocates a total risk budget across different risk factors including interest rate, currency, and credit risk to control portfolio volatility."),
    ("What is risk parity for bond portfolios?", "Risk parity allocates risk equally across different asset classes or risk factors, rather than equal capital allocation, to achieve better diversification."),
    ("What is factor risk budgeting?", "Factor risk budgeting assigns risk limits to individual systematic factors like duration, curve, and credit spread, ensuring controlled exposure to each risk source."),
    ("What is stress scenario budgeting?", "Stress scenario budgeting allocates maximum acceptable losses across predefined stress scenarios, ensuring the portfolio survives extreme but plausible market conditions."),
    ("What is tail risk hedging?", "Tail risk hedging protects against extreme market events by purchasing options or implementing strategies that profit during severe downturns, at the cost of regular premium."),
    ("What is the maximum drawdown constraint?", "The maximum drawdown constraint limits the worst peak to trough decline in portfolio value, providing a concrete risk limit for debt portfolio management."),
    ("What is conditional tail expectation?", "CTE measures the expected loss in the worst X percent of scenarios, providing a more intuitive risk measure than VaR for understanding extreme downside outcomes."),
    ("What is the risk contribution of each instrument?", "Risk contribution measures how much each bond instrument contributes to total portfolio risk, enabling informed decisions about which positions to increase or decrease."),
    ("What is the tracking error budget?", "Tracking error budget sets the maximum acceptable deviation from a benchmark, guiding how actively the portfolio can deviate from passive index replication."),
    ("What is the value added at risk?", "VaR measures the maximum expected loss at a given confidence level over a specified time horizon, providing a single number summary of portfolio downside risk."),
    # ── Issuance Strategy ─────────────────────────────────────────────
    ("What is the regular issuance strategy?", "Regular issuance establishes a predictable supply of bonds through consistent auctions, building liquidity and investor base while reducing market timing risk."),
    ("What is opportunistic issuance?", "Opportunistic issuance takes advantage of favorable market conditions like low rates or high demand to issue bonds at attractive terms outside the regular calendar."),
    ("What is the syndicated issuance method?", "Syndicated issuance involves a group of banks jointly underwriting and distributing a large bond issue, useful for complex or novel transactions."),
    ("What is the auction method for bonds?", "Competitive auctions allow dealers to submit bids at various yields, with the issuer accepting bids from lowest yield upward until the target amount is reached."),
    ("What is the non competitive auction bid?", "Non competitive bids accept the weighted average yield determined by the auction, guaranteed allocation but without price choice, available to retail investors."),
    ("What is the when issued market?", "The when issued market allows trading of bonds before they are officially issued, providing price discovery and hedging opportunities for new supply."),
    ("What is thegreenshoe allocation?", "The greenshoe allocation distributes oversubscribed issuance to meet excess demand, with the issuer having the option to increase the final size."),
    ("What is the minimum bid yield?", "The minimum bid yield is the lowest acceptable yield in an auction, preventing below market pricing and ensuring the issuer does not overpay for funding."),
    ("What is the award amount?", "The award amount is the total quantity of bonds allocated to successful bidders in an auction, typically meeting the announced target issuance amount."),
    ("What is the tail of a bond auction?", "The auction tail measures the difference between the highest yield accepted and the average accepted yield, indicating the demand distribution and clearing level."),
] + ADDITIONAL_QA_PAIRS + ADDITIONAL_QA_PAIRS_BATCH2 + ADDITIONAL_QA_PAIRS_BATCH3 + ADDITIONAL_QA_PAIRS_BATCH4

# ── Training Loop ─────────────────────────────────────────────────────

def train():
    print("=" * 60)
    print("QUANTIVE AI v1 — 1000 QA PAIRS, 50 EPOCHS")
    print("=" * 60)
    print()

    # Prepare data as Q/A pairs
    texts = []
    for q, a in TRAINING_DATA:
        texts.append(f"<Q> {q} <A> {a}")

    print(f"Training data: {len(TRAINING_DATA)} QA pairs")

    # Build tokenizer
    tokenizer = WordTokenizer()
    tokenizer.fit(texts, min_freq=1)
    print(f"Vocabulary: {tokenizer.vocab_size} words")

    # Tokenize
    max_len = 128
    encoded = [tokenizer.encode(t, max_length=max_len) for t in texts]
    max_seq = max(len(e) for e in encoded)
    max_seq = min(max_seq, 256)
    print(f"Max sequence length: {max_seq}")

    # Pad
    padded = []
    for e in encoded:
        e = e[:max_seq]
        padded.append(e + [0] * (max_seq - len(e)))
    input_ids = torch.tensor(padded, dtype=torch.long)

    # Labels = shifted input
    labels = input_ids.clone()
    labels[:, :-1] = input_ids[:, 1:]
    labels[:, -1] = 0
    labels = labels.masked_fill(input_ids == 0, -100)

    print(f"Batch size: {len(input_ids)}")
    print()

    # Build model
    print("Building model...")
    model = QuantiveAI(
        vocab_size=tokenizer.vocab_size,
        d_model=192,
        n_heads=6,
        n_layers=4,
        d_ff=512,
        max_seq=max_seq,
    )
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model: {total_params / 1e6:.1f}M parameters")
    print()

    # Training
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)

    epochs = 50
    print(f"Training for {epochs} epochs...")
    print()

    start_time = time.time()
    best_loss = float('inf')
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()

        logits = model(input_ids)
        loss = F.cross_entropy(logits.reshape(-1, tokenizer.vocab_size), labels.reshape(-1), ignore_index=-100)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        if loss.item() < best_loss:
            best_loss = loss.item()
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if (epoch + 1) % 10 == 0 or epoch == 0:
            elapsed = time.time() - start_time
            perplexity = math.exp(min(loss.item(), 20))
            print(f"  Epoch {epoch+1:3d}/{epochs} | Loss: {loss.item():.4f} | PPL: {perplexity:.2f} | Best: {best_loss:.4f} | Time: {elapsed:.1f}s")

    total_time = time.time() - start_time
    print()
    print(f"Training complete in {total_time:.1f}s")
    print(f"Best loss: {best_loss:.4f}")

    # Restore best model
    model.load_state_dict(best_state)

    # Save
    output_dir = Path(r'C:\Users\HP\OneDrive\Desktop\Quantive\backend\data\training\models\quantive_ai_v1')
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.save({
        'model_state_dict': model.state_dict(),
        'config': model.config,
        'tokenizer': {'word2idx': tokenizer.word2idx, 'idx2word': tokenizer.idx2word},
    }, output_dir / 'model.pt')

    with open(output_dir / 'config.json', 'w') as f:
        json.dump(model.config, f, indent=2)

    print(f"Model saved to {output_dir}")

    # Test generation
    print()
    print("=" * 60)
    print("GENERATION TESTS")
    print("=" * 60)

    model.eval()
    test_prompts = [
        "What is sovereign debt?",
        "What is debt optimization?",
        "What is the IMF?",
        "What are credit rating agencies?",
        "What is a yield curve?",
    # ── Additional Training Data ────────────────────────────────────────
] + ADDITIONAL_QA_PAIRS
    for prompt in test_prompts:
        ids = tokenizer.encode(f"<Q> {prompt} <A>", max_length=max_len)
        input_t = torch.tensor([ids], dtype=torch.long)
        with torch.no_grad():
            for _ in range(80):
                logits = model(input_t)
                next_logits = logits[:, -1, :] / 0.8
                probs = F.softmax(next_logits, dim=-1)
                next_token = torch.multinomial(probs, 1)
                input_t = torch.cat([input_t, next_token], dim=1)
                if input_t.shape[1] >= max_seq:
                    break
                if next_token.item() == tokenizer.word2idx.get('<EOS>', 3):
                    break
        response = tokenizer.decode(input_t[0].tolist())
        print(f"\nQ: {prompt}")
        print(f"A: {response}")

    return model, tokenizer


if __name__ == "__main__":
    model, tokenizer = train()
