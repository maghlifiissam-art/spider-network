# MASA order workflow (zero spend, manual Taager entry)
1. Customer opens a product landing page (docs/masa/<product>/index.html, from template) and submits the Tally order form (name, phone, city, address, quantity).
2. Spider reads the new Tally submission (Tally email notification or API) and creates a row in the order log.
3. Spider sends script 1 on WhatsApp from the owner's number. No bulk sending, only order customers.
4. Reply "yes": status CONFIRMED. No reply: scripts 2 and 3. No/negative: CANCELLED, never contacted again.
5. For each CONFIRMED order: enter it in the Taager seller panel (Saudi): product, customer name, phone, city, address, quantity, selling price. Only after the Taager login lockout is lifted. Until then orders wait with status PENDING_TAAGER.
6. Taager ships and collects cash on delivery. Track status RETURNED / DELIVERED in the log; payout minus Taager price = profit.
7. Weekly: review return rate by product; drop products over 25% returns.
Order log columns: date, order id, product, qty, price, name, phone, city, address, status, taager id, delivered/returned, notes.
Constraints: Saudi customers' personal data stays in the Tally form, the order log and Taager only. Prices are in SAR and must match what the landing page says.
