"""Train SovereignGPT v3 — word tokenizer, 200+ QA pairs, 200 epochs.

No external downloads. Pure PyTorch. ~5M params.
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

class SovereignGPT(nn.Module):
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
]

# ── Training Loop ─────────────────────────────────────────────────────

def train():
    print("=" * 60)
    print("SOVEREIGNGPT v3 — 200+ QA PAIRS, 200 EPOCHS")
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
    model = SovereignGPT(
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
    output_dir = Path(r'C:\Users\HP\OneDrive\Desktop\Quantive\backend\data\training\models\sovereign_gpt_v2')
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
    ]
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
