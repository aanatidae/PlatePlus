# Flat-rate toll scope

PlatePlus supports a simulated flat-rate toll at each location. One accepted crossing
is an independent toll event; the system does not track a journey or pair entry and
exit locations. There is no distance, route-length, or per-kilometre charge calculation.
Map coordinates and highway labels are presentation metadata, not pricing inputs.

The rule-based dynamic toll starts from:

`dynamic toll = location flat base toll × selected congestion multiplier`

The selected band may be held by the minimum change interval or threshold hysteresis.
The resulting amount is bounded by the configured minimum toll and the location base
toll times the maximum multiplier, then rounded to two decimal places. An explicit
pricing-policy update recalculates current prices without traffic-only interval or
hysteresis holds while retaining the price limits. Persisted prices are authoritative;
payment reads the latest non-future price for the crossing's location.

For example, a prototype base of RM2.40 at a 1.5× multiplier produces RM3.60 before
any applicable safeguard. These example and seeded base tolls are simulated prototype
configuration, not published or official highway tariffs.

Origin does not change the congestion band or multiplier. An eligible Singaporean
vehicle adds the separately configured simulated foreign-vehicle charge **after** the
dynamic toll decision. Malaysian vehicles add zero. The final attempted total is
stored as `amount`; successful wallet debit and reversal use that total. Unknown or
ambiguous origin cannot produce a successful deduction.

The V3 target normal network is LDP, AKLEH, NPE, and Grand Saga. Section I network
alignment is still pending; the current normal locations remain Penchala/LDP, DUKE,
KESAS, and NPE. Simulator Toll Plaza remains a separate local-ALPR location, with
10 active crossings and a rolling 60-second congestion window. This scope does not
rename locations or reinterpret historical records.

Verification is in `backend/tests/unit/test_pricing_decision.py` (location-relative
formula, price limits, interval and hysteresis) and the PostgreSQL payment/pricing
integration tests (stored price, charge components, wallet debit, replay, and refund).
