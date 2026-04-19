# Planning Addendum: Decisions, Explanations, and Data Sources

**Date:** April 2, 2026
**Relation to:** Normative_Ontology_Planning_Document

This document answers the outstanding conceptual questions and records the decisions made on April 2, 2026. It also catalogs all available legal data sources and contains the revised implementation plan.

---

## A1. How Alexy Extends Hohfeld in UFO-L

Hohfeld's original system (1913) identifies eight fundamental legal positions arranged in four correlative pairs:

    Right ↔ Duty
    Privilege (Permission) ↔ No-Right
    Power ↔ Liability (Subjection)
    Disability ↔ Immunity

These are *dyadic* — they describe a relationship between exactly two people. "John has a Right against Mary" means "Mary has a Duty toward John." That's all Hohfeld gives you.

The problem is that Hohfeld doesn't distinguish between *what kind of action* the right or duty concerns. "John has a right that Mary pay him $100" and "John has a right that Mary *not* disclose his data" look structurally identical in Hohfeld's system — both are Right-Duty pairs. But legally they're quite different: one requires Mary to *do* something, the other requires Mary to *refrain from* something.

**Alexy's addition (from "A Theory of Constitutional Rights," 2002):** Robert Alexy makes Hohfeld's positions *triadic* — three-part rather than two-part. Every legal position now has three components:

1. **The holder** (who has the position)
2. **The addressee** (who the position is directed toward)
3. **The object** (what action or omission the position concerns)

And critically, Alexy distinguishes the object into **positive actions** (doing something) and **negative actions** (omitting/refraining from something). This doubles the number of position subtypes:

    Right to a Positive Action → "A has a right against B that B does φ"
    Right to a Negative Action → "A has a right against B that B omits φ"
    Duty to Act → "B has a duty toward A to do φ"
    Duty to Omit → "B has a duty toward A to omit φ"
    Permission to Act → "A has permission toward B to do φ"
    Permission to Omit → "A has permission toward B to omit φ"
    No-Right to an Action → "B has no-right to demand A does φ"
    No-Right to an Omission → "B has no-right to demand A omits φ"

**How UFO-L implements this:**

In the UFO-L ontology diagram (Fig. 2 of the Griffo paper), you can see that the bottom row of the taxonomy splits each legal moment into action/omission variants. For example, under the Right-Duty Relator, you get:

- Right to an Action / Right to an Omission
- Duty to Act / Duty to Omit

And under the NoRight-Permission Relator:

- NoRight to an Action / NoRight to an Omission
- Permission to Act / Permission to Omit

Each of these is a distinct ontological class in UFO-L. They're all subtypes of their parent (e.g., "Right to an Action" is a subtype of "Right"), but they carry different semantic content.

**Why this matters for our project:**

When we extract normative content from a statute, the Alexy extension forces us to be precise about what exactly the norm requires. Consider:

    "The employer shall provide safety equipment" → Right to Positive Action (employee has right that employer *does* something)
    "The employer shall not retaliate against whistleblowers" → Right to Negative Action (employee has right that employer *omits* something)

Without Alexy's distinction, both would just be "Right-Duty pairs." With it, we capture the crucial difference between obligations to act and obligations to refrain — which matters enormously for compliance, enforcement, and reasoning.

**The Liberty Relator — Alexy's most interesting contribution:**

Alexy also enables UFO-L to model *Liberty* as a Complex Legal Relator. A Liberty is when a person has *both* the permission to do something *and* the permission to not do it — they are genuinely free to choose. In UFO-L, this is modeled as a composition of two NoRight-Permission Relators:

    Liberty of A to φ = Permission of A to Act (φ) + Permission of A to Omit (φ)
                       = No-Right of B to demand A does φ + No-Right of B to demand A omits φ

This is the formal representation of freedom: nobody can demand you do it, and nobody can demand you don't.

---

## A2. Defeasibility Explained, with a LegalRuleML Example

**What defeasibility means:**

In everyday logic, rules are absolute: "if it rains, the ground gets wet" — no exceptions. But legal rules are almost never absolute. They come with exceptions, qualifications, overrides, and conflicts. "Defeasibility" is the formal name for this property: a rule is *defeasible* if its conclusion can be "defeated" — overridden or blocked — by additional information.

Think of it this way: a non-defeasible (strict) rule is like a law of physics. A defeasible rule is like a legal presumption — it holds *unless* something else overrides it.

**A concrete example:**

Consider two rules in a legal system:

    Rule 1: "Vehicles are prohibited in the park."
    Rule 2: "Emergency vehicles are permitted in the park."

Rule 1 says vehicles are prohibited. Rule 2 creates an exception — emergency vehicles are permitted despite Rule 1. Rule 2 *defeats* Rule 1 for the specific case of emergency vehicles.

In classical logic, having both "vehicles are prohibited" and "emergency vehicles are permitted" would be a contradiction. The system would break. In defeasible logic, it works fine: Rule 1 is a *defeasible* rule (it holds unless something overrides it), and Rule 2 is a *defeater* (it blocks Rule 1 for a specific case).

**The three types of rules in defeasible logic:**

LegalRuleML distinguishes three strengths of rules:

1. **Strict rules** (written: body → head) — If the body holds, the head *always* holds. No exceptions. These are rare in law but exist for things like mathematical definitions or constitutional absolutes. "A person is a minor if they are under 18."

2. **Defeasible rules** (written: body ⇒ head) — If the body holds, the head *usually* holds, unless something defeats it. This is the normal case for legal norms. "Vehicles are prohibited in the park" is defeasible because exceptions exist.

3. **Defeaters** (written: body ~> head) — These can *block* a defeasible rule but cannot establish anything on their own. They're pure exceptions. "If the vehicle is an emergency vehicle, it is *not* the case that it is prohibited." The defeater doesn't say emergency vehicles are *permitted* — it only says the prohibition doesn't apply.

**How LegalRuleML handles conflicts between rules:**

When two defeasible rules conflict (one says X, the other says not-X), LegalRuleML provides a *superiority relation* to resolve the conflict. This maps directly to the classical legal principles:

- *Lex specialis* — the more specific rule prevails over the more general
- *Lex posterior* — the later-enacted rule prevails over the earlier
- *Lex superior* — the higher-authority rule prevails (constitutional > statutory > regulatory)

In LegalRuleML, this is expressed with the `<lrml:Override>` element:

```xml
<!-- Rule 1: Vehicles are prohibited in the park -->
<lrml:PrescriptiveStatement key="ps1">
    <ruleml:Rule key="rule1">
        <ruleml:if>
            <ruleml:Atom>isVehicle($x) AND inPark($x)</ruleml:Atom>
        </ruleml:if>
        <ruleml:then>
            <lrml:Obligation>
                <ruleml:Atom>prohibited($x)</ruleml:Atom>
            </lrml:Obligation>
        </ruleml:then>
    </ruleml:Rule>
</lrml:PrescriptiveStatement>

<!-- Rule 2: Emergency vehicles are permitted in the park -->
<lrml:PrescriptiveStatement key="ps2">
    <ruleml:Rule key="rule2">
        <ruleml:if>
            <ruleml:Atom>isEmergencyVehicle($x) AND inPark($x)</ruleml:Atom>
        </ruleml:if>
        <ruleml:then>
            <lrml:Permission>
                <ruleml:Atom>permitted($x)</ruleml:Atom>
            </lrml:Permission>
        </ruleml:then>
    </ruleml:Rule>
</lrml:PrescriptiveStatement>

<!-- Rule 2 overrides Rule 1 (lex specialis — more specific wins) -->
<lrml:OverrideStatement>
    <lrml:Override over="#rule2" under="#rule1"/>
</lrml:OverrideStatement>
```

The Override element says: when Rule 1 and Rule 2 conflict (and they will, because every emergency vehicle is also a vehicle), Rule 2 wins. The system doesn't have a contradiction — it has a resolved conflict.

**Why this is essential for statutory law:**

The US Code is full of this pattern. A typical structure looks like:

    § 1234(a): "No person shall discharge pollutants into navigable waters."
    § 1234(b): "Subsection (a) does not apply to discharges authorized under a permit issued under section 1342."
    § 1234(c): "Notwithstanding subsection (b), no permit may authorize the discharge of..." [specific toxic substances]

This is three layers of defeasibility: a general prohibition, an exception (permits), and an exception to the exception (certain substances can't be permitted). Each layer defeats the one above it. LegalRuleML's defeasible logic handles this directly.

---

## A3. The Multi-Layer Architecture (Decision Confirmed)

You've identified the correct architecture. No single ontology does everything. We need layers:

**Layer 1 — UFO-L** for the *relational* structure of normative positions (who owes what to whom, who has power over whom). This is the Hohfeld + Alexy layer. It captures the *meaning* of legal norms in terms of the positions they create between agents.

**Layer 2 — LegalRuleML** for the *rule* structure (if X then Y, with exceptions and overrides). This captures the *logic* of norms — conditions, consequences, defeasibility, conflict resolution. It also handles constitutive norms (definitions: "For the purposes of this section, X means Y").

**Layer 3 — A domain/world ontology** for the *things in the real world* that norms are about. Laws regulate real-world events, objects, activities, and situations. "Natural disaster" is not a legal concept — it's a real-world concept that legal norms reference. We need a way to represent these.

For this layer, the options are:

- **DOLCE** — A foundational ontology that covers physical objects, events, processes, qualities. Very general, ISO standard. Could serve as the base for domain extensions.
- **Schema.org** — A simpler, more pragmatic vocabulary used across the web. Has types for Event, Place, Organization, Product, Action, etc. Less philosophically rigorous but far more widely used and understood.
- **Custom domain modules** — Build domain-specific modules as needed (e.g., an "Environmental" module with concepts like Pollutant, WaterBody, EmissionSource; a "Labor" module with concepts like Employee, Workplace, Wage).

The pragmatic recommendation is to start with custom domain modules for the specific title we're extracting, using DOLCE or schema.org as a reference vocabulary rather than a formal dependency. We can always formalize the connection later.

**Layer 4 — Akoma Ntoso / USLM** for the *document* structure. See next section.

---

## A4. Document Representation and Multiple Interpretations

**The document layer:**

You're right that Akoma Ntoso (or specifically USLM, the US variant) should be used for the document layer. Every normative statement in the graph needs to trace back to its source: "this obligation comes from 42 USC § 7412(a)(1), as enacted by Public Law 101-549, § 301."

The good news: the US Code is already published in USLM XML, which is based on LegalDocML/Akoma Ntoso. So we don't need to convert anything — we consume the official structured source directly.

**Multiple interpretations — how this works in the graph:**

Your intuition is exactly right. Here's how this would look:

Imagine 42 USC § 1983, the civil rights statute. The text says: "Every person who, under color of any statute, ordinance, regulation, custom, or usage, of any State or Territory or the District of Columbia, subjects, or causes to be subjected, any citizen of the United States... to the deprivation of any rights, privileges, or immunities secured by the Constitution and laws, shall be liable to the party injured..."

This statute has been interpreted many different ways by different courts and scholars. In the graph, this would look like:

```
[Source Node: 42 USC § 1983]
    ├── stored as: USLM XML (the literal text with structural markup)
    │
    ├── [Normative Extraction 1: "Base reading"]
    │   ├── type: PrescriptiveStatement
    │   ├── deontic: Obligation (liability)
    │   ├── addressee: "every person acting under color of state law"
    │   ├── condition: "causes deprivation of constitutional rights"
    │   ├── consequence: "liable to injured party"
    │   ├── source: LLM extraction (confidence: 0.95)
    │   └── strength: Defeasible
    │
    ├── [Interpretation A: Qualified Immunity Defense]
    │   ├── source: Harlow v. Fitzgerald, 457 U.S. 800 (1982)
    │   ├── type: Defeater of Extraction 1
    │   ├── content: "Officials are shielded unless conduct violates
    │   │            clearly established statutory or constitutional rights"
    │   ├── authority: Supreme Court
    │   └── override: Defeats the base obligation when official acted
    │                  in objectively reasonable manner
    │
    ├── [Interpretation B: Municipal Liability]
    │   ├── source: Monell v. Dept. of Social Services, 436 U.S. 658 (1978)
    │   ├── type: Extension of Extraction 1
    │   ├── content: "municipalities can be sued under § 1983 when
    │   │            the alleged unconstitutional action implements
    │   │            an official policy"
    │   └── authority: Supreme Court
    │
    └── [Interpretation C: Academic critique]
        ├── source: Schwartz, "The Case Against Qualified Immunity,"
        │           Notre Dame Law Review (2018)
        ├── type: Alternative reading
        ├── content: argues the text does not support qualified immunity
        └── authority: Academic (persuasive only, not binding)
```

This is exactly what LegalRuleML's "Alternatives" mechanism was designed for — multiple, potentially incompatible formal readings of the same provision, each tagged with its source, authority, and jurisdiction.

The key insight: **the graph doesn't pick one interpretation.** It stores all of them, with metadata about their authority and provenance. A query can then ask: "What does § 1983 require *under the Supreme Court's interpretation*?" or "What does § 1983 require *if we ignore qualified immunity*?"

---

## A5. Scope (Decision: All Federal + One State Pilot)

**Decided:** Everything federal. Plus one state as pilot.

The federal corpus consists of:

1. **US Constitution** — The supreme law. All other federal law derives authority from it.
2. **US Code** (54 titles) — Federal statutes as codified. This is the primary target.
3. **Code of Federal Regulations** (50 titles) — Regulations issued by executive agencies implementing the statutes. This is where the detailed normative content lives (e.g., the Clean Air Act creates general powers; EPA regulations specify exact emission limits).
4. **Executive Orders** — Presidential directives with force of law.
5. **Federal court opinions** — Judicial interpretations that define what the statutes and Constitution mean in practice.
6. **Federal court rules** — Rules of Civil Procedure, Criminal Procedure, Evidence, etc.

**Selected state pilot: New York.**

New York was selected because: it is a large, complex legal corpus that meaningfully tests the system's scalability, it has an excellent Open Legislation API at legislation.nysenate.gov (JSON, free API key), NYC Administrative Code is available in XML, and CourtListener has extensive NY appellate court coverage.

Data availability for NY:
- **NY Consolidated Laws (statutes):** NY Senate Open Legislation API — JSON, free API key, excellent coverage
- **NYC Administrative Code:** XML via NYC Council website
- **NY Regulations (NYCRR):** Not available in structured bulk format. Individual sections available through the Department of State website. Will require scraping or phased inclusion after statutes.
- **NY Court Opinions:** CourtListener bulk data (Court of Appeals, Appellate Division). Also nycourts.gov.

Original alternative that was considered: Vermont (smaller, cleaner data, but less meaningful as a test). Virginia (The State Decoded project, XML format) also remains an option for future pilots.

---

## A6. Temporal Model (Decision: Current Law Only)

**Decided:** Current point in time only. Historical versioning deferred.

This means: we model the US Code, CFR, and state code *as they currently stand*. We do not track what the law said last year or ten years ago. This enormously simplifies the data model and the extraction pipeline.

We will, however, record metadata about *when* each provision was last amended and which Public Law made the change. This lays the groundwork for future temporal expansion without requiring us to build the full temporal model now.

---

## A7. Serialization and Storage — Explained from Scratch

This section explains the options in non-technical terms.

**What's the problem we're solving?**

We're building a knowledge graph — a web of facts about what the law requires. Each fact looks something like: "Under 42 USC § 7412, the EPA Administrator has a duty to establish emission standards for hazardous air pollutants." This fact has parts: a source (the statute), an actor (the EPA Administrator), a relationship (has a duty), and an object (establish emission standards).

We need to: (a) store millions of such facts, (b) connect them to each other (the duty in one statute references a power in another), and (c) ask questions about them ("What are all the duties of the EPA Administrator?" or "What happens if this duty is violated?").

The question is: what format do we store these facts in, and what software do we use to query them?

**Option A: RDF Triple Store**

*What it is:* RDF (Resource Description Framework) is a standard way of expressing facts as "triples" — three-part statements. Every fact is: Subject → Predicate → Object.

Example:
```
<42USC7412>  <creates>  <DutyToEstablishStandards>
<DutyToEstablishStandards>  <addressee>  <EPAAdministrator>
<DutyToEstablishStandards>  <type>  <Obligation>
<EPAAdministrator>  <isA>  <FederalOfficial>
```

A triple store is a database designed to hold billions of these triples and answer questions about them using a query language called SPARQL.

*Analogy:* Think of it like a massive web of index cards. Each card has three fields: "this thing → has this relationship → with that thing." The triple store lets you follow the threads between cards. "Start with EPA Administrator. Follow all 'addressee' threads backward. Show me everything that points to them." That query returns every duty, power, and prohibition directed at the EPA Administrator across the entire US Code.

*Benefits:*
- This is the international standard for knowledge graphs. All the legal ontology projects we've been studying (LKIF, ELI, ALLOT, FOLIO) use RDF.
- It's designed for exactly this kind of data: entities connected by typed relationships.
- SPARQL (the query language) is powerful for traversing networks of relationships.
- It's inherently web-compatible — every entity gets a unique URL-like identifier, so different knowledge graphs can link to each other.

*Drawbacks:*
- The tools (Protege, Jena, GraphDB, Stardog) have a steep learning curve.
- SPARQL can be unintuitive at first.
- Performance can be an issue with very complex queries over very large datasets.
- The RDF data model is quite strict — everything must be expressed as triples, which sometimes feels awkward for complex structures.

*Available software:* GraphDB (free community edition), Apache Jena Fuseki (free, open-source), Stardog (commercial), Blazegraph (free, powers Wikidata).

**Option B: Labeled Property Graph (e.g., Neo4j)**

*What it is:* A different kind of graph database where nodes (entities) can have multiple properties (fields) and edges (relationships) can also have properties. It's more flexible than RDF — nodes aren't restricted to triples.

Example:
```
(Node: Statute {title: "42 USC § 7412", enacted: "1990-11-15"})
    --[CREATES {section: "a(1)"}]-->
(Node: Obligation {type: "Duty", content: "establish emission standards"})
    --[ADDRESSED_TO]-->
(Node: Agent {name: "EPA Administrator", type: "Federal Official"})
```

*Analogy:* Instead of index cards with three fields, imagine a corkboard with pins (nodes) connected by colored strings (relationships). Each pin has a little note card attached with whatever information you want. Each string has a label saying what kind of connection it represents. You can follow strings to navigate between pins.

*Benefits:*
- More intuitive than RDF — the data model matches how people naturally think about graphs.
- Neo4j specifically has excellent developer tools, visualization, and documentation.
- The query language (Cypher) is generally considered easier to learn than SPARQL.
- Better performance for complex traversal queries ("find all paths from statute A to penalty B through chains of references").

*Drawbacks:*
- Not the international standard for ontologies. The legal ontology community uses RDF/OWL. Using Neo4j means we'd need to translate.
- Doesn't natively support the formal reasoning that OWL ontologies enable (e.g., automatic classification, consistency checking).
- Harder to link with other legal knowledge graphs (which are all in RDF).

*Available software:* Neo4j (free community edition, commercial enterprise edition).

**Option C: PostgreSQL + JSON**

*What it is:* A traditional relational database (tables with rows and columns) augmented with JSON columns for flexible data. This is what the contract prototype already uses.

*Analogy:* Think of a filing cabinet with labeled folders (tables). Each folder contains standardized forms (rows) with fixed fields (columns). Some fields can contain freeform notes in a structured format (JSON). To find connections, you look up references between folders.

*Benefits:*
- Most familiar technology. Enormous ecosystem of tools, tutorials, and developers.
- Very good for structured queries ("show me all obligations in Title 42").
- Excellent for the application layer (web APIs, user interfaces).
- Already set up from the contract prototype.

*Drawbacks:*
- Not designed for graph data. Following chains of relationships (A references B which references C which creates D) requires complex JOIN queries that get slow and hard to write.
- Doesn't support ontological reasoning at all.
- Doesn't benefit from the legal knowledge graph standards ecosystem (RDF, SPARQL, OWL).

**The recommendation:**

Use **RDF/OWL as the canonical representation** — this is a knowledge graph project, and RDF is the standard for knowledge graphs. The entire legal ontology community works in RDF, and all the standards we want to use (LKIF, ELI, LegalRuleML's RDFS metamodel, ALLOT) are in RDF.

Use **Neo4j or PostgreSQL as the application layer** if we need a web interface or API that doesn't want to speak SPARQL. The canonical RDF graph can be projected into Neo4j or PostgreSQL for specific application needs.

Think of it as: RDF is the "source of truth" (like the official text of a law), and Neo4j/PostgreSQL are "working copies" (like a summary or index that's easier to use for specific tasks).

---

## A8. Parsing Strategy Decision

**The core question:** Should we parse statutes one provision at a time (narrow context), or load large chunks of surrounding context (heavy context)?

**Decision: Heavy context, high quality, accept the token cost.**

Here's why: statutory provisions are *not self-contained*. A single section typically:
- References definitions from another section ("as defined in section 1234")
- Contains exceptions that reference other provisions ("except as provided in subsection (b)")
- Uses terms of art that have specific legal meaning established elsewhere
- Depends on the structure of the chapter it sits in (general provisions apply to all sections in the chapter unless overridden)

Parsing a provision in isolation will produce *wrong* extractions. The LLM will guess at the meaning of defined terms, miss cross-reference constraints, and fail to identify defeasibility relationships.

**The proposed parsing architecture:**

**Step 1: Context Assembly (deterministic, no LLM needed)**

For each provision to be parsed, assemble a context package:
- The provision text itself
- All definitions that apply (from the "Definitions" section of the same chapter/title, and any local definitions in the same section)
- All cross-referenced provisions (follow "as provided in" / "subject to" / "notwithstanding" references and include those texts)
- The chapter/subchapter structure (headings, to understand organizational context)
- Any relevant annotations from prior parsing passes (e.g., if we already parsed the definitions section, include those extracted norms)

This step is pure data retrieval — no LLM cost, just XML parsing and cross-reference resolution.

**Step 2: Normative Extraction (reasoning model, heavy context)**

Feed the assembled context to a reasoning-tier model (Claude Opus or equivalent) with a carefully designed prompt that:
- Provides the ontology schema as structured output specification
- Includes 3-5 manually annotated examples (few-shot)
- Asks for specific extraction targets (obligations, prohibitions, permissions, powers, definitions, exceptions, penalties)
- Requires confidence scores and source character offsets for each extraction
- Instructs the model to identify defeasibility relationships ("this provision is an exception to..." / "this provision is defeated by...")

**Step 3: Validation (can use a lighter model)**

Check extractions for schema conformance, cross-reference consistency, and obvious errors. Flag low-confidence extractions for human review.

**Why this is better than splitting into small, cheap calls:**

A provision like "Subject to paragraph (2), and except as provided in subsection (d), the Administrator shall, by regulation, establish emission standards..." contains *one sentence* that requires understanding of paragraph (2), subsection (d), the full context of what "emission standards" means in this title, and the general duties of the Administrator established elsewhere. A narrow-context parse would miss most of this. A heavy-context parse gets it right the first time, even if it costs more per call.

The token cost is justified because *correction is more expensive than getting it right the first time*. A bad extraction that goes into the graph and later needs to be found and fixed costs more in human review time than the extra tokens to do it right initially.

**Prompt development plan:**

1. Manually extract normative content from 10-15 representative provisions across different types (substantive rule, definition, penalty, delegation, exception)
2. Use these as the few-shot examples in the parsing prompt
3. Test the prompt against another 20-30 provisions and measure accuracy against manual extraction
4. Iterate on the prompt until accuracy reaches an acceptable threshold (target: 85%+ for deontic content identification, 75%+ for correct relationship extraction)
5. Only then begin scaling to full title extraction

---

## A9. Complete Legal Data Source Catalog

### Federal Data Sources

**1. US Constitution**
- Structured XML/JSON: github.com/hsurden/us-constitution
- Official PDF: uscode.house.gov/static/constitution.pdf
- Annotated (CONAN): govinfo.gov (GPO-CONAN-2022)
- Format: XML, JSON, PDF
- Bulk download: Yes

**2. United States Code (Federal Statutes) — ALL 54 TITLES**
- Primary source: uscode.house.gov/download/download.shtml
- Format: USLM XML (based on Akoma Ntoso / LegalDocML)
- Coverage: All 54 titles, current through latest public law
- Bulk download: Yes — ZIP files by title or all titles
- Also available: govinfo.gov/bulkdata (beta USLM XML, 113th Congress forward)
- API: GovInfo API (api.govinfo.gov) — requires api.data.gov key
- Schema documentation: github.com/usgpo/uslm

**3. Code of Federal Regulations (CFR) — ALL 50 TITLES**
- Annual editions (XML): govinfo.gov/bulkdata/CFR — organized by year and title, 1996-present
- Daily updated (eCFR): ecfr.gov — XML bulk download available
- API: GovInfo API
- Documentation: github.com/usgpo/bulk-data (CFR-XML User Guide, ECFR-XML User Guide)
- Note: Only PDF/text versions have official legal status; XML is derived

**4. Federal Register (daily publication of rules, proposed rules, notices)**
- Bulk XML: govinfo.gov/bulkdata/FR
- API: federalregister.gov/developers/documentation/api/v1 — NO key required
- Formats: XML, CSV, JSON
- Coverage: Multiple years
- Documentation: github.com/usgpo/bulk-data (FR-XML User Guide)

**5. Congressional Bills and Resolutions**
- Bulk XML: govinfo.gov/bulkdata/BILLS — 113th Congress (2013) forward
- Bill Status XML: govinfo.gov/bulkdata/BILLSTATUS — 108th Congress (2003) forward
- API: Congress.gov API (api.congress.gov) — requires api.data.gov key
- Community tools: github.com/unitedstates/congress (Python, public domain)
- Documentation: govinfo.gov/bulkdata/BILLS/resources/BILLS-XML_User-Guide-v2.pdf

**6. Public Laws (enrolled bills signed by President)**
- USLM XML: govinfo.gov/features/beta-uslm-xml — 113th Congress forward
- API: Congress.gov API, GovInfo API
- Browse: congress.gov/public-laws/

**7. Statutes at Large**
- USLM XML: govinfo.gov/features/beta-uslm-xml — Volumes 117+ (2003 forward)
- Historical (planned): Volumes 1-116 digitization in progress
- API: GovInfo API

**8. Executive Orders**
- Federal Register: federalregister.gov/presidential-documents/executive-orders
- Formats: CSV, Excel, JSON bulk downloads
- Coverage: Since 1937
- API: Federal Register API (no key required)

**9. Presidential Proclamations and Memoranda**
- Federal Register: federalregister.gov/presidential-documents/proclamations
- Other documents: federalregister.gov/presidential-documents/other-presidential-documents
- Formats: CSV, Excel, JSON
- Coverage: Since 1994

**10. Supreme Court Opinions**
- Official XML: supremecourt.gov/xmls/current and /xmls/archive
- CourtListener bulk data: courtlistener.com/help/api/bulk-data/ — ~600MB+ tar.gz
- Free Law Project: free.law/projects/supreme-court-data/
- Supreme Court Database (SCDB): scdb.wustl.edu/data.php
- Formats: XML, JSON
- API: CourtListener REST API

**11. Federal Circuit Court Opinions**
- CourtListener: courtlistener.com/help/api/bulk-data/ — 99%+ of precedential US case law
- GovInfo: govinfo.gov/help/uscourts — selected courts, 2004-present
- Federal Circuit Dataset: empirical.law.uiowa.edu/compendium-federal-circuit-decisions
- Formats: XML, JSON, PDF

**12. Federal District Court Opinions**
- CourtListener: courtlistener.com/help/api/bulk-data/ — 9+ million decisions
- RECAP Archive: courtlistener.com/recap/ — hundreds of millions of docket entries
- PACER: pacer.uscourts.gov — capped at $3.00/document
- Formats: XML, JSON, PDF

**13. Congressional Committee Reports**
- GovInfo: govinfo.gov/help/crpt — 104th Congress (1995) forward
- Formats: ASCII text, PDF
- API: Congress.gov API

**14. Congressional Research Service (CRS) Reports**
- Official: crsreports.congress.gov — 2017-present, PDF only
- Complete archive: everycrsreport.com — 23,005+ reports with bulk download
- UNT Digital Library: digital.library.unt.edu — since 1990

**15. Federal Court Rules**
- Official: uscourts.gov/forms-rules
- Cornell LII: law.cornell.edu/rules/frcp, /rules/fre, etc.
- Formats: PDF, HTML (no bulk XML available)
- Note: Also published as appendices to US Code Titles 18 and 28

**16. Treaties and International Agreements**
- UN Treaty Series: treaties.un.org
- US State Department: state.gov (Treaties in Force annual list)
- Formats: PDF, HTML (limited structured data)

### State Pilot Data Sources (New York)

- **NY Consolidated Laws (statutes):** legislation.nysenate.gov — Open Legislation API, JSON, free API key
- **NYC Administrative Code:** Available in XML via NYC Council website
- **NY Regulations (NYCRR):** Not in structured bulk format. Individual sections at dos.ny.gov. Phased inclusion or scraping required.
- **NY Court of Appeals opinions:** CourtListener bulk data (courtlistener.com/help/api/bulk-data/)
- **NY Appellate Division opinions:** CourtListener bulk data
- **NY trial court opinions:** Limited structured availability; not prioritized for pilot

### Alternative State Candidates

- **Vermont:** legislature.vermont.gov (API, structured HTML); archive.org/details/gov.vt.code (bulk). Small corpus, clean data. Good for secondary pilot.
- **Virginia:** The State Decoded project at vacode.org — XML format

### Central Data Hubs

- **GovInfo** (govinfo.gov) — the master hub for all GPO publications. Bulk data, API, search.
- **Congress.gov API** (api.congress.gov) — bills, laws, committee reports, nominations, treaties
- **Federal Register API** (federalregister.gov/developers) — rules, proposed rules, executive orders
- **CourtListener** (courtlistener.com) — case law across all federal courts

### Existing Semantic/KG Projects on US Law

- **Semantic CFR Knowledge Graph** — Title 21 and Title 48 formalized with deep learning (ACM Digital Library)
- **SKOS Vocabulary for CFR** — Title 21 terminology extracted into SKOS (Semantic Web Journal)
- **Free Law Project Semantic Search** — domain-adapted semantic search over CourtListener (launched 2025)
- **USLM standard** — already based on LegalDocML/Akoma Ntoso, providing structured legislative markup

---

## A10. Revised Implementation Plan

### Phase 0: Foundation and Data Acquisition (Weeks 1-6)

**Goal:** Get all the data, set up the infrastructure, finalize the ontology schema.

**Week 1-2: Data acquisition**
- Download US Code in USLM XML — all 54 titles from uscode.house.gov/download/download.shtml
- Download eCFR in XML — all 50 titles from ecfr.gov
- Download Executive Orders in JSON from Federal Register API
- Download NY Consolidated Laws via Open Legislation API
- Set up CourtListener API access for case law
- Register for GovInfo API key and Congress.gov API key
- Store all raw data in an organized directory structure

**Week 3-4: Ontology schema design**
- Define the core ontology in OWL combining:
  - UFO-L legal positions (Hohfeld + Alexy) — for the relational structure of norms
  - LegalRuleML concepts (adapted to OWL) — for defeasibility, norm types, deontic operators
  - USLM structural elements — for document hierarchy
  - Custom domain classes — for real-world things norms regulate
- Define namespace and URI scheme (e.g., `https://normgraph.org/us/usc/t42/s7412`)
- Set up RDF triple store (GraphDB Community or Apache Jena Fuseki)
- Define competency questions that the graph should answer

**Week 5-6: Manual extraction and prompt development**
- Select 15-20 representative provisions from across different US Code titles covering: substantive obligations, prohibitions, permissions, delegations of authority, definitions, penalties, exceptions, and cross-references
- Manually extract normative content from each into the ontology schema (this creates the gold standard)
- Begin designing the parsing prompt using these manual extractions as few-shot examples

### Phase 1: Structural Parsing (Weeks 7-10)

**Goal:** Get the entire structural skeleton of the US Code and CFR into the graph — every title, chapter, section, and subsection as a node, with cross-references as edges.

**Week 7-8: US Code structural parsing**
- Parse all 54 titles of USLM XML into RDF nodes
- Extract: structural hierarchy (Title > Subtitle > Chapter > Subchapter > Part > Section > Subsection > Paragraph)
- Extract: section headings, enactment dates, amendment references
- Extract: all cross-references between sections (tagged in USLM as `<ref>` elements)
- Extract: all definitions sections and their defined terms

**Week 9-10: CFR structural parsing + linkage**
- Parse all 50 titles of CFR XML into RDF nodes
- Link CFR provisions to their authorizing US Code sections (the CFR structure parallels the USC structure by title number)
- Extract cross-references within the CFR

**Deliverable:** A structural graph with ~100,000+ nodes (one per provision) connected by cross-reference edges. No normative content yet — just the skeleton.

### Phase 2: Parsing Prompt Development and Testing (Weeks 11-16)

**Goal:** Build, test, and refine the LLM parsing prompt until it reliably extracts normative content.

**Week 11-12: Initial prompt design**
- Design the parsing prompt with:
  - The ontology schema as structured output specification
  - The 15-20 manual extractions as few-shot examples
  - Instructions for handling each norm type (obligation, prohibition, permission, power, definition, exception, penalty)
  - Instructions for identifying defeasibility relationships
  - Instructions for confidence scoring
- Implement the context assembly pipeline (Step 1 from Section A8): for each provision, automatically gather definitions, cross-referenced provisions, and chapter structure

**Week 13-14: Prompt testing and iteration**
- Run the prompt against 50 additional provisions (not used in few-shot examples)
- Compare LLM extractions against manual expert review
- Measure: precision and recall for each norm type, accuracy of cross-reference identification, accuracy of defeasibility identification
- Iterate on prompt design based on error analysis
- Target: 85%+ identification of deontic content, 75%+ correct relationship extraction

**Week 15-16: Prompt finalization and pipeline engineering**
- Finalize the prompt
- Build the full pipeline: context assembly → extraction → validation → storage
- Implement batch processing for running the pipeline over hundreds/thousands of provisions
- Implement logging and error tracking
- Estimate token cost for full US Code extraction

### Phase 3: Full Federal Extraction (Weeks 17-30)

**Goal:** Run the extraction pipeline over the entire US Code and CFR.

**Week 17-20: US Code extraction — Phase A (Titles 1-18)**
- Run pipeline, monitor quality, catch errors
- Human review of flagged provisions (low confidence, detected conflicts)
- Refine prompt if systematic errors emerge

**Week 21-24: US Code extraction — Phase B (Titles 19-54)**
- Continue extraction
- Begin linking cross-title references (many titles reference each other)
- Begin extracting Executive Orders and linking them to relevant USC/CFR provisions

**Week 25-28: CFR extraction — Phase A (priority titles)**
- Start with CFR titles that correspond to the most normatively rich USC titles
- Link regulatory norms to their authorizing statutory norms

**Week 29-30: Quality review and gap-filling**
- Systematic review of extraction quality across a random sample
- Fill gaps: provisions that failed to parse, provisions with low confidence, provisions needing human review
- Generate statistics: total norms extracted, distribution by type, coverage metrics

### Phase 4: State Pilot and Court Interpretations (Weeks 31-40)

**Goal:** Extend to Vermont state law and begin incorporating judicial interpretations.

**Week 31-34: New York state law extraction**
- Acquire and parse NY Consolidated Laws via Open Legislation API
- Acquire NYC Administrative Code in XML
- Adapt the parsing prompt for state statutory language (which differs from federal)
- Extract normative content
- Link NY provisions to relevant federal provisions (e.g., NY laws implementing federal mandates)

**Week 35-38: Judicial interpretation layer**
- Select the most-cited provisions in the US Code (these have the most case law)
- Use CourtListener to retrieve key interpretive decisions
- Extract normative interpretations from court opinions
- Add these as interpretation nodes linked to the source provisions (as described in Section A4)

**Week 39-40: Query interface and visualization**
- Build a SPARQL query interface
- Build a visual graph explorer
- Validate against the competency questions defined in Phase 0
- Demonstrate end-to-end: "What must the EPA Administrator do under the Clean Air Act, and what happens if they don't?"

### Phase 5: Scale and Refine (Weeks 41+)

- Additional state pilots
- Full CFR extraction
- Treaty integration
- CRS report and legislative history integration
- Advanced reasoning: automated conflict detection, compliance checking
- Public API

---

## Summary of All Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Foundational ontology | UFO | Already invested; UFO-L's legal position modeling is best available |
| Legal positions | Hybrid: Hohfeld for specific norms, deontic operators for general norms | Pragmatic balance of precision and tractability |
| Defeasibility | LegalRuleML-style override annotations | Essential for statutory law; start with explicit overrides, add full defeasible reasoning later |
| Document structure | USLM (US variant of Akoma Ntoso) | Official format; already published by government |
| Scope | All federal law + New York as state pilot | Comprehensive with a meaningful, large-scale test case |
| Temporal model | Current law only | Historical versioning deferred; amendment metadata recorded |
| Storage | RDF/OWL canonical + application layer as needed | Standard for knowledge graphs; interoperable with legal ontology ecosystem |
| Parsing strategy | Heavy context, high quality, reasoning-tier model | Accuracy over speed; correction costs more than extra tokens |
| Domain ontology | Custom modules per domain, using DOLCE/schema.org as reference | Build what we need, formalize later |
