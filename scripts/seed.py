"""Seed the database with a hand-crafted example contract (Meat Sale from Symboleo paper)."""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import engine, SessionLocal, Base
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def uid():
    return str(uuid.uuid4())

# ── Parties ──
seller_party = models.Party(id=uid(), name="AgriCorp Ltd.", type="Organization",
    identifiers=[{"key": "EIN", "value": "12-3456789"}])
buyer_party = models.Party(id=uid(), name="FreshMart Inc.", type="Organization",
    identifiers=[{"key": "EIN", "value": "98-7654321"}])
db.add_all([seller_party, buyer_party])

# ── Contract ──
contract = models.Contract(
    id=uid(), name="Meat Sale Agreement — AgriCorp / FreshMart",
    effective_date="2026-04-01", expiration_date="2027-03-31",
    governing_law="UCC Article 2", jurisdiction="New York, USA",
    source_text="""MEAT SALE AGREEMENT

This Meat Sale Agreement ("Agreement") is entered into as of April 1, 2026 ("Effective Date") by and between:

AgriCorp Ltd., a corporation organized under the laws of Delaware ("Seller"), and FreshMart Inc., a corporation organized under the laws of New York ("Buyer").

WHEREAS, Seller is in the business of producing and distributing premium beef products; and
WHEREAS, Buyer operates a chain of grocery stores and desires to purchase beef products from Seller;

NOW, THEREFORE, in consideration of the mutual covenants set forth herein, the parties agree as follows:

1. DEFINITIONS
1.1 "Goods" means one thousand (1,000) kilograms of Grade AAA beef, as further described in Exhibit A.
1.2 "Purchase Price" means $25,000 USD.
1.3 "Delivery Date" means within thirty (30) days of the Effective Date.

2. SALE AND PURCHASE
2.1 Seller agrees to sell and Buyer agrees to purchase the Goods at the Purchase Price.

3. DELIVERY
3.1 Seller shall deliver the Goods to Buyer's designated warehouse at 100 Market Street, New York, NY 10001, on or before the Delivery Date.
3.2 Risk of loss shall pass to Buyer upon delivery.

4. PAYMENT
4.1 Buyer shall pay the Purchase Price to Seller within fifteen (15) days of delivery of the Goods.
4.2 Late payments shall accrue interest at a rate of 1.5% per month.

5. QUALITY AND INSPECTION
5.1 All Goods shall conform to USDA Grade AAA standards.
5.2 Buyer shall have five (5) business days after delivery to inspect the Goods and notify Seller of any nonconformity.

6. REMEDIES
6.1 If Seller fails to deliver the Goods by the Delivery Date, Buyer may, at its option, (a) extend the delivery period by ten (10) days, or (b) terminate this Agreement.
6.2 If Buyer fails to pay by the due date, Seller may suspend delivery obligations until payment is received.

7. CONFIDENTIALITY
7.1 Each party shall maintain the confidentiality of the other party's proprietary information for a period of two (2) years following termination of this Agreement.

8. TERMINATION
8.1 Either party may terminate this Agreement upon thirty (30) days' written notice.
8.2 Termination shall not affect any rights or obligations accrued prior to the termination date.

9. GOVERNING LAW
9.1 This Agreement shall be governed by the laws of the State of New York and the Uniform Commercial Code.

10. ENTIRE AGREEMENT
10.1 This Agreement constitutes the entire agreement between the parties and supersedes all prior negotiations and agreements.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

AgriCorp Ltd.                    FreshMart Inc.
By: _______________              By: _______________
Name:                            Name:
Title:                           Title:
""",
    created_at="2026-03-26T00:00:00Z", updated_at="2026-03-26T00:00:00Z",
)
db.add(contract)
db.flush()

# ── Roles ──
seller = models.Role(id=uid(), label="Seller", party_id=seller_party.id, contract_id=contract.id)
buyer = models.Role(id=uid(), label="Buyer", party_id=buyer_party.id, contract_id=contract.id)
db.add_all([seller, buyer])
db.flush()

# ── Assets ──
goods = models.Asset(id=uid(), contract_id=contract.id, name="Grade AAA Beef",
    type="Tangible", description="1,000 kg of Grade AAA beef per USDA standards",
    owned_by_id=seller_party.id,
    properties=[{"key": "quantity", "value": "1000kg"}, {"key": "quality", "value": "AAA"}])
purchase_price = models.Asset(id=uid(), contract_id=contract.id, name="Purchase Price",
    type="Intangible", description="$25,000 USD")
db.add_all([goods, purchase_price])

# ── Clauses ──
clauses_data = [
    ("preamble", "Preamble", "Preamble", "This Meat Sale Agreement is entered into as of April 1, 2026 by and between AgriCorp Ltd. and FreshMart Inc."),
    ("party_identification", "Parties", "Parties", "AgriCorp Ltd., a corporation organized under the laws of Delaware (\"Seller\"), and FreshMart Inc., a corporation organized under the laws of New York (\"Buyer\")."),
    ("definition", "1.1", "Definitions — Goods", "\"Goods\" means one thousand (1,000) kilograms of Grade AAA beef, as further described in Exhibit A."),
    ("definition", "1.2", "Definitions — Price", "\"Purchase Price\" means $25,000 USD."),
    ("definition", "1.3", "Definitions — Delivery Date", "\"Delivery Date\" means within thirty (30) days of the Effective Date."),
    ("obligation", "2.1", "Sale and Purchase", "Seller agrees to sell and Buyer agrees to purchase the Goods at the Purchase Price."),
    ("obligation", "3.1", "Delivery", "Seller shall deliver the Goods to Buyer's designated warehouse at 100 Market Street, New York, NY 10001, on or before the Delivery Date."),
    ("condition", "3.2", "Risk of Loss", "Risk of loss shall pass to Buyer upon delivery."),
    ("obligation", "4.1", "Payment", "Buyer shall pay the Purchase Price to Seller within fifteen (15) days of delivery of the Goods."),
    ("temporal_provision", "4.2", "Late Payment Interest", "Late payments shall accrue interest at a rate of 1.5% per month."),
    ("obligation", "5.1", "Quality Standard", "All Goods shall conform to USDA Grade AAA standards."),
    ("right", "5.2", "Inspection Right", "Buyer shall have five (5) business days after delivery to inspect the Goods and notify Seller of any nonconformity."),
    ("power", "6.1", "Buyer's Remedies for Late Delivery", "If Seller fails to deliver the Goods by the Delivery Date, Buyer may, at its option, (a) extend the delivery period by ten (10) days, or (b) terminate this Agreement."),
    ("power", "6.2", "Seller's Remedy for Non-Payment", "If Buyer fails to pay by the due date, Seller may suspend delivery obligations until payment is received."),
    ("confidentiality", "7.1", "Confidentiality", "Each party shall maintain the confidentiality of the other party's proprietary information for a period of two (2) years following termination of this Agreement."),
    ("termination", "8.1", "Termination by Notice", "Either party may terminate this Agreement upon thirty (30) days' written notice."),
    ("termination", "8.2", "Surviving Rights", "Termination shall not affect any rights or obligations accrued prior to the termination date."),
    ("governing_law", "9.1", "Governing Law", "This Agreement shall be governed by the laws of the State of New York and the Uniform Commercial Code."),
    ("entire_agreement", "10.1", "Entire Agreement", "This Agreement constitutes the entire agreement between the parties and supersedes all prior negotiations and agreements."),
    ("signature", "Signatures", "Signature Block", "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above."),
]

clause_objs = {}
for tag, sec, heading, text in clauses_data:
    cl = models.Clause(id=uid(), contract_id=contract.id, section_number=sec,
        heading=heading, text=text, ontology_tag=tag)
    db.add(cl)
    clause_objs[sec] = cl
db.flush()

# ── Obligations ──
obligations = [
    (seller, buyer, "Seller shall sell and deliver 1,000 kg of Grade AAA beef to Buyer",
     "Delivery of goods to buyer's warehouse", {"type": "Deadline", "description": "Within 30 days of effective date", "reference_date": "2026-04-01", "offset_days": 30}, False, "2.1"),
    (buyer, seller, "Buyer shall pay $25,000 USD to Seller",
     "Payment of purchase price", {"type": "Relative", "description": "Within 15 days of delivery"}, False, "4.1"),
    (seller, buyer, "All Goods shall conform to USDA Grade AAA standards",
     "Quality conformance", None, False, "5.1"),
    (seller, buyer, "Seller shall maintain confidentiality of Buyer's proprietary information",
     "Non-disclosure of proprietary information", {"type": "Period", "description": "2 years following termination"}, True, "7.1"),
    (buyer, seller, "Buyer shall maintain confidentiality of Seller's proprietary information",
     "Non-disclosure of proprietary information", {"type": "Period", "description": "2 years following termination"}, True, "7.1"),
]

for debtor, creditor, desc, conseq, temporal, surviving, sec in obligations:
    obl = models.Obligation(
        id=uid(), contract_id=contract.id,
        debtor_role_id=debtor.id, creditor_role_id=creditor.id,
        description=desc, consequent=conseq,
        temporal_constraint=temporal, surviving=surviving,
        clause_id=clause_objs[sec].id,
    )
    db.add(obl)

# ── Powers ──
powers_data = [
    (buyer, seller, "Buyer may extend delivery period by 10 days if Seller fails to deliver on time",
     "Extension of delivery deadline", {"description": "Seller fails to deliver by Delivery Date"}, "6.1"),
    (buyer, seller, "Buyer may terminate Agreement if Seller fails to deliver on time",
     "Termination of contract", {"description": "Seller fails to deliver by Delivery Date"}, "6.1"),
    (seller, buyer, "Seller may suspend delivery obligations if Buyer fails to pay",
     "Suspension of delivery obligations", {"description": "Buyer fails to pay by due date"}, "6.2"),
    (seller, buyer, "Seller may terminate Agreement with 30 days notice",
     "Termination of contract", {"description": "At will, with 30 days written notice"}, "8.1"),
    (buyer, seller, "Buyer may terminate Agreement with 30 days notice",
     "Termination of contract", {"description": "At will, with 30 days written notice"}, "8.1"),
]

for creditor, debtor, desc, conseq, trigger, sec in powers_data:
    pwr = models.Power(
        id=uid(), contract_id=contract.id,
        creditor_role_id=creditor.id, debtor_role_id=debtor.id,
        description=desc, consequent=conseq,
        trigger_condition=trigger,
        clause_id=clause_objs[sec].id,
    )
    db.add(pwr)

# ── Constraints ──
db.add(models.Constraint(id=uid(), contract_id=contract.id,
    description="Seller and Buyer must be different parties",
    expression="seller ≠ buyer",
    clause_id=clause_objs["Preamble"].id))

db.commit()
print(f"Seeded contract: {contract.name} (id: {contract.id})")
print(f"  Parties: {seller_party.name}, {buyer_party.name}")
print(f"  Roles: Seller, Buyer")
print(f"  Clauses: {len(clauses_data)}")
print(f"  Obligations: {len(obligations)}")
print(f"  Powers: {len(powers_data)}")
print("Done.")
db.close()
