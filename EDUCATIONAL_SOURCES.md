# Educational sources

Checked July 26, 2026. These primary sources support the stable educational
concepts used in Milestones 2 through 6. Runtime gameplay and tests use local
fictional configuration and do not require network access.

## CME Group

- [NYMEX Rulebook Chapter 220: Henry Hub Natural Gas Futures](https://www.cmegroup.com/rulebook/NYMEX/2/220.pdf)
  - Standard trading unit: 10,000 MMBtu.
  - Minimum price fluctuation: $0.001 per MMBtu.
  - Henry Hub is the delivery location for the physically settled standard contract.
- [Natural Gas Product Overview](https://www.cmegroup.com/education/courses/introduction-to-natural-gas/nat-gas-product-overview.html)
  - Identifies the standard NG contract as 10,000 MMBtu and the minimum price
    fluctuation as $0.001 per MMBtu.
- [Money Calculations for Futures and Options](https://www.cmegroup.com/education/articles-and-reports/money-calculations-for-futures-and-options)
  - Futures settlement variation is a daily cash mark-to-market process.
- [Mark-to-Market](https://www.cmegroup.com/education/courses/introduction-to-futures/mark-to-market)
  - Daily settlement prices determine daily gains, losses, and possible margin
    adjustments.
- [Futures Order Types](https://www.cmegroup.com/education/courses/futures-trading-mechanics-and-regulation/futures-order-types)
  - Distinguishes market, limit, and stop orders.
  - A sell limit defines the seller's minimum acceptable price and may remain
    unfilled; a stop requires a trigger before it becomes executable.
- [What happens when you submit an order?](https://www.cmegroup.com/education/courses/futures-trading-mechanics-and-regulation/what-happens-when-you-submit-an-order)
  - Describes broker checks, exchange acceptance, matching, fills, clearing, and
    controls on contract type and quantity.
- [Closing Your Position](https://www.cmegroup.com/education/courses/things-to-know-before-trading-cme-futures/closing-your-position)
  - An open futures position is closed with an opposite position in the same
    contract; released margin then becomes available.

## CFTC

- [The Economic Purpose of Futures Markets](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/economicpurpose.html)
  - A seller exposed to falling cash prices can use a short futures position.
  - Initial margin is a performance bond rather than a purchase down payment.
  - Futures positions are marked to market daily.
  - A maintenance breach can require funding back to initial margin.
- [CFTC Futures Glossary](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CFTCGlossary/index.htm)
  - Definitions for basis risk, hedge ratio, margin, margin calls, variation
    margin, and mark-to-market.
- [Futures Market Basics](https://www.cftc.gov/LearnAndProtect/EducationCenter/FuturesMarketBasics/index2.htm)
  - Distinguishes commercial hedgers from speculators and describes market
    oversight, supervision, and internal-control responsibilities.
- [Futures Commission Merchants (FCMs)](https://www.cftc.gov/IndustryOversight/Intermediaries/FCMs/fcmibdisclosures.html)
  - Summarizes exact-quantity trading authorization, next-business-day
    confirmations, order receipt/transmission timestamps, transaction records,
    daily journals, and supervisory responsibility.
- [17 CFR 1.35](https://www.ecfr.gov/current/title-17/chapter-I/part-1/section-1.35)
  - Current federal text for records of commodity-interest transactions. The
    game uses it as a high-level reason to preserve separate order, execution,
    confirmation, and correction records—not as a compliance implementation.

## FASB

- [FASB Accounting Standards Updates](https://www.fasb.org/standards/accounting-standard-updates)
  - The FASB Codification is the authoritative source of nongovernmental U.S.
    GAAP; Topic 470 covers debt and Topic 835 covers interest.
- [ASU 2015-15, Interest—Imputation of Interest](https://storage.fasb.org/ASU%202015-15.pdf)
  - Addresses debt issuance costs associated with line-of-credit arrangements
    within Subtopic 835-30.
- [ASU 2016-13 master-glossary excerpt](https://storage.fasb.org/ASU_2016-13.pdf)
  - Describes a line-of-credit or revolving-debt arrangement as allowing repeated
    borrowings up to a maximum, repayments, and reborrowing; drawn amounts are
    debt instruments and undrawn capacity is a loan commitment.

The game's debit-cash/credit-debt draw and debit-interest-expense/credit-accrued-
interest entries are deliberately simplified teaching patterns, not a complete
GAAP conclusion for any real facility.

## GAO internal-control framework

- [GAO 2025 Green Book](https://www.gao.gov/greenbook)
  - Provides a primary-source framework for control activities, reliable
    information, communication, and documentation. The game uses these concepts
    for contemporaneous approvals and durable decision evidence.
  - Its 2025 revision includes examples of preventive and detective activities
    and distinguishes the design, implementation, and operation of controls.

The Green Book applies directly to U.S. federal internal control. Here it is a
general educational control-design reference, not a claim that Northstar is a
federal entity.

## The Institute of Internal Auditors

- [2024 Global Internal Audit Standards](https://www.theiia.org/en/standards/2024-standards/global-internal-audit-standards/)
  - The current Standards are effective for quality assessments beginning
    January 9, 2025.
  - They support the chapter's evidence-based engagement work, professional
    skepticism, communication of results, and monitoring of action plans.
  - Noah's fictional walkthrough borrows these professional concepts. It does
    not claim that a four-day single-transaction game chapter is a complete
    standards-conforming internal-audit engagement.

## NFA

- [NFA Study Outline for Futures Industry Exams](https://www.nfa.futures.org/registration-membership/study-outlines/index.html)
  - Identifies short and long hedging, basis, hedge calculations, initial and
    maintenance margin, variation, settlement, and substantial price movements
    as exam-study concepts.
- [NFA Rulebook](https://www.nfa.futures.org/rulebook/rules.aspx)
  - Includes NFA Compliance Rule 2-9 supervision requirements and related
    interpretive materials for NFA members.
  - The game distinguishes those member and associated-person obligations from
    Northstar's fictional internal policies and from general professional best
    practices. It does not imply every NFA rule directly governs the junior
    analyst or every Northstar employee.

## Fictional assumptions

The following are game parameters, not statements of current exchange or FCM
requirements:

- Initial margin: $15,000 per contract.
- Maintenance margin: $11,000 per contract.
- All Henry Hub and Chicago prices.
- The five-day weather, pipeline, and liquidity sequence.
- Northstar's $3.9 million minimum operating-cash reserve.
- The second five-day winter-rally path and $70,000 day-two call.
- The $500,000 revolver, 8.5% rate, $50,000 draw increment, $3.6 million
  covenant, approvals, and lender.
- The $750,000 obligation schedule and $3.5 million treasury operating reserve.
- The fictional FCM's 2:00 p.m. deadline and deterministic liquidation after an
  intentionally missed call.
- The First Rotation dates, people, questions, authorization packet, forecast
  quantities, and margin examples.
- The Eleventh Contract dates, intraday observations, fills, trigger behavior,
  physical-volume outcome, order and authorization IDs, FCM confirmation,
  control workflow, Chicago basis, and fish-fry events.
- The No Surprises engagement, request list, control objectives and activities,
  Northstar severity labels, test results, findings, target dates, management
  responses, outcomes, and board/lender/buyer interest.
- Full fills at the next configured eligible observation, with no order-book
  depth, queue priority, fees, slippage, exchange price protection, or partial
  fills in the authored path. The typed order model can still represent partial,
  cancelled, rejected, and unfilled statuses.
