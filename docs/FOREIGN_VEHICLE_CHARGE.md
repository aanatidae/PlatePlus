# Simulated foreign-vehicle charge

Optional upload fallback extends this path to validated `foreign_other` results
with matching declared synthetic country; initially modern UK plates are supported.
MY adds zero; SG and accepted other-foreign origins add the configured separate fee.
Local ambiguity still fails safely unless optional high-confidence Gemini evidence
passes PlatePlus validation and registration matching. See [scope and security](GEMINI_FALLBACK.md).

PlatePlus stores a vehicle's declared demo `registration_origin` separately from the OCR pattern decision. A successful simulated charge requires an unambiguous Malaysian or Singaporean pattern and a matching active synthetic vehicle. Unknown, overlapping, and registration-mismatch results cannot debit a wallet. Pattern matching does not verify legal registration or nationality.

For a Malaysian vehicle, `final simulated total = dynamic toll`. For a Singaporean vehicle, `final simulated total = dynamic toll + configured simulated foreign-vehicle charge`. The foreign charge is added after congestion pricing; it does not affect the congestion band or multiplier. `toll_transactions.dynamic_toll_amount` and `foreign_vehicle_charge` store the components; `amount` stores their final attempted total. A failed transaction may show an attempted amount, but it never creates a wallet debit. The successful wallet ledger, payment notification, and any reversal use the final debited total.

Migration `20261002_0013` adds the component fields and a separate `foreign_vehicle_charge_settings` singleton. Existing transaction amounts are backfilled as dynamic toll with zero foreign charge, without inferring historical origins. The seeded charge is **RM20.00 as a configurable simulated demo value inspired by the proposal**. It is not a real toll-plaza fee. After migration, an authenticated administrator can read or change the amount through `GET` or `PUT /api/data/foreign-vehicle-charge` with a JSON body such as `{"amount":"20.00"}`. Updates are audit logged. A missing setting makes a Singaporean payment fail safely.

The idempotent local seed adds three fictional Singaporean-pattern vehicles with `@example.test` accounts. Two have enough opening balance for the seeded charge plus a typical dynamic toll, and one intentionally has an insufficient balance. The existing 96-vehicle Malaysian presentation fleet remains the source of normal generated demo crossings. Singaporean examples can be exercised through the normal payment service and local Simulator Toll Plaza webcam or still-image flow. No issued registration, real owner, government lookup, bank, or eWallet is involved.
