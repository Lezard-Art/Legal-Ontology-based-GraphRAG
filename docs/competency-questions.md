# Competency Questions — NormGraph SPARQL Queries

Competency questions define what the knowledge graph must be able to answer.
Each question is paired with a SPARQL 1.1 query against the `normgraph` Fuseki dataset.

**Endpoint**: `http://localhost:3030/normgraph/sparql`
**Prefix shorthand used throughout**:
```sparql
PREFIX : <urn:normgraph:onto#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
```

---

## CQ-1 — What legal positions does a given statute create?

> "What Hohfeldian relators are created by 42 USC § 1983?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?relator ?relatorType ?holderName ?addresseeName
WHERE {
  ?extraction a :NormativeExtraction ;
              :sourceProvision <urn:uslm:statute:usc:42/1983> ;
              :createdPositions ?relator .
  ?relator :relatorType ?relatorType ;
           :holderAgent ?holder ;
           :addresseeAgent ?addressee .
  ?holder   :agentName ?holderName .
  ?addressee :agentName ?addresseeName .
}
ORDER BY ?relatorType
```

---

## CQ-2 — What obligations apply to a given legal role?

> "What must 'any employer' do under federal employment law?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?statementId ?sourceText ?deadline
WHERE {
  ?stmt a :PrescriptiveStatement ;
        :deonticOperator "Obligation" ;
        :targetAgent ?agent ;
        :statementId ?statementId ;
        :sourceText ?sourceText .
  ?agent :agentName ?agentName .
  FILTER(CONTAINS(LCASE(?agentName), "employer"))
  OPTIONAL { ?stmt :deadlineDuration ?deadline }
}
ORDER BY ?statementId
```

---

## CQ-3 — What government powers does a statute create?

> "What powers does the EPA Administrator hold?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?relatorId ?powerType ?sourceProvision ?actionVerb
WHERE {
  ?relator a :PowerLiabilityRelator ;
           :relatorId ?relatorId ;
           :powerType ?powerType ;
           :holderAgent ?holder .
  OPTIONAL { ?relator :sourceProvision ?sourceProvision }
  OPTIONAL {
    ?relator :actionDescriptor ?ad .
    ?ad :actionVerb ?actionVerb .
  }
  ?holder :agentName ?holderName .
  FILTER(CONTAINS(LCASE(?holderName), "epa") ||
         CONTAINS(LCASE(?holderName), "administrator"))
}
ORDER BY ?powerType
```

---

## CQ-4 — Which extraction is currently authoritative for a provision?

> "What is the controlling interpretation of 42 USC § 1983 in the Second Circuit?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?extractionId ?controllingCase ?validAsOf
WHERE {
  ?auth a :AuthoritativeInterpretation ;
        :authInterpProvision <urn:uslm:statute:usc:42/1983> ;
        :applicableJurisdiction <urn:uslm:domain:jurisdiction:second-circuit> ;
        :controllingDecision ?decision ;
        :validAsOf ?validAsOf .
  ?decision :caseName ?controllingCase .
  OPTIONAL { ?auth :overriddenByDecision ?superseded }
  FILTER(!BOUND(?superseded))   # exclude superseded interpretations
  BIND(STR(?auth) AS ?extractionId)
}
ORDER BY DESC(?validAsOf)
LIMIT 1
```

---

## CQ-5 — How has a provision's legal positions changed over time?

> "What amendments modified 42 USC § 1983 after 1990?"

```sparql
PREFIX : <urn:normgraph:onto#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?amendmentId ?amendmentType ?dateEnacted ?amendedText
WHERE {
  ?amend a :Amendment ;
         :amendmentId ?amendmentId ;
         :originalProvisionUri <urn:uslm:statute:usc:42/1983> ;
         :amendmentType ?amendmentType ;
         :dateEnacted ?dateEnacted .
  OPTIONAL { ?amend :amendedText ?amendedText }
  FILTER(?dateEnacted > "1990-01-01T00:00:00"^^xsd:dateTime)
}
ORDER BY ?dateEnacted
```

---

## CQ-6 — What terms does a statute define?

> "What terms are defined in Title 42 Chapter 21 (Civil Rights)?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?term ?definition ?scope
WHERE {
  ?defSection a :DefinitionsSection .
  ?defSection :nodeId ?nodeId .
  FILTER(STRSTARTS(STR(?nodeId), "urn:uslm:statute:usc:42"))
  ?defSection :sectionDefinedTerms ?dt .
  ?dt :term ?term ;
      :termDefinition ?definition .
  OPTIONAL { ?dt :termApplicability ?scope }
}
ORDER BY ?term
```

---

## CQ-7 — Which rules are defeasible and what defeats them?

> "List all defeasible rules and the rules that defeat them."

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?defeasibleRule ?defeaterRule ?overrideType
WHERE {
  ?stmt a :NormativeStatement ;
        :statementId ?defeasibleRule ;
        :defeasibilityStrength "Defeasible" ;
        :isDefeatedBy ?defeaterRule .
  OPTIONAL {
    ?override a :OverridingRule ;
              :overriddenRuleId ?defeasibleRule ;
              :overridingRuleId ?defeaterRule ;
              :overrideType ?overrideType .
  }
}
ORDER BY ?defeasibleRule
```

---

## CQ-8 — What penalty regime applies when an obligation is violated?

> "What penalties follow from violating 42 USC § 1983?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?penaltyId ?penaltyType ?penaltyDescription ?penaltyAmount ?isStrictLiability
WHERE {
  ?penalty a :PenaltyStatement ;
           :statementId ?penaltyId ;
           :triggeredBy <urn:uslm:normative-rule:42-usc-1983:rule-2> ;
           :penaltyType ?penaltyType ;
           :penaltyDescription ?penaltyDescription .
  OPTIONAL { ?penalty :penaltyAmount ?penaltyAmount }
  OPTIONAL { ?penalty :isStrictLiability ?isStrictLiability }
}
```

---

## CQ-9 — What domain entities does a provision regulate?

> "What regulated substances are subject to FDA controls in Title 21?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?entityId ?entityLabel ?regulatoryStatus ?controlLevel
WHERE {
  ?extraction a :NormativeExtraction ;
              :sourceProvision ?provision ;
              :domainEntities ?entity .
  FILTER(STRSTARTS(STR(?provision), "urn:uslm:statute:usc:21"))
  ?entity a :Substance ;
          :entityId ?entityId ;
          :entityLabel ?entityLabel ;
          :regulatoryStatus ?regulatoryStatus .
  OPTIONAL { ?entity :controlLevel ?controlLevel }
}
ORDER BY ?regulatoryStatus ?entityLabel
```

---

## CQ-10 — What are all known aliases for a canonical agent?

> "What aliases does 'EPA Administrator' have in the statute corpus?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?alias
WHERE {
  ?agent a :CanonicalAgent ;
         :primaryLabel "EPA Administrator" ;
         :canonicalAliases ?alias .
}
ORDER BY ?alias
```

---

## CQ-11 — Which extractions require human review and why?

> "Show all low-confidence extractions that require review."

```sparql
PREFIX : <urn:normgraph:onto#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?extractionId ?sourceProvision ?confidenceScore ?parsingNotes
WHERE {
  ?extraction a :NormativeExtraction ;
              :extractionId ?extractionId ;
              :sourceProvision ?sourceProvision ;
              :requiresHumanReview true ;
              :confidenceScore ?confidenceScore .
  OPTIONAL { ?extraction :parsingNotes ?parsingNotes }
}
ORDER BY ASC(?confidenceScore)
```

---

## CQ-12 — What provisions conflict with or override each other?

> "Find all lex specialis override relationships in the corpus."

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?generalRule ?specialRule ?scope
WHERE {
  ?override a :OverridingRule ;
            :overrideType "LexSpecialis" ;
            :overriddenRuleId ?generalRule ;
            :overridingRuleId ?specialRule .
  OPTIONAL { ?override :overrideScope ?scope }
}
ORDER BY ?generalRule
```

---

## CQ-13 — What cross-references does a section contain?

> "What other statutes does 42 USC § 1983 reference?"

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?targetStatute ?referenceType ?semanticRelation ?referenceText
WHERE {
  ?node a :DocumentNode ;
        :nodeId <urn:uslm:statute:usc:42/1983> ;
        :nodeCrossReferences ?ref .
  ?ref :targetStatute ?targetStatute ;
       :referenceType ?referenceType .
  OPTIONAL { ?ref :semanticRelation ?semanticRelation }
  OPTIONAL { ?ref :referenceText ?referenceText }
}
ORDER BY ?referenceType
```

---

## CQ-14 — What immunity protections exist in a given domain?

> "List all immunity relators created by federal employment law statutes."

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?relatorId ?holderName ?immunityScope ?exceptions
WHERE {
  ?relator a :DisabilityImmunityRelator ;
           :relatorId ?relatorId ;
           :sourceProvision ?provision ;
           :holderAgent ?holder .
  FILTER(STRSTARTS(STR(?provision), "urn:uslm:statute:usc:29") ||
         STRSTARTS(STR(?provision), "urn:uslm:statute:usc:42"))
  ?holder :agentName ?holderName .
  OPTIONAL { ?relator :immunityScope ?immunityScope }
  OPTIONAL {
    ?relator :immunityExceptions ?exc .
    ?exc :simpleStatement ?exceptions .
  }
}
ORDER BY ?relatorId
```

---

## CQ-15 — What is the complete normative structure of a provision?

> "Give the full normative analysis of 42 USC § 1983: rules, positions, penalties, interpretations."

```sparql
PREFIX : <urn:normgraph:onto#>

SELECT ?extractionId ?stmtType ?operator ?targetAgent ?penaltyType ?caseName ?authority
WHERE {
  ?extraction a :NormativeExtraction ;
              :extractionId ?extractionId ;
              :sourceProvision <urn:uslm:statute:usc:42/1983> .

  OPTIONAL {
    ?extraction :normativeStatements ?stmt .
    ?stmt :statementType ?stmtType .
    OPTIONAL { ?stmt :deonticOperator ?operator }
    OPTIONAL {
      ?stmt :targetAgent ?ta .
      ?ta :agentName ?targetAgent .
    }
    OPTIONAL { ?stmt :penaltyType ?penaltyType }
  }

  OPTIONAL {
    ?extraction :interpretations ?interp .
    ?interp :caseName ?caseName ;
            :interpretationAuthority ?authority .
  }
}
ORDER BY ?stmtType ?caseName
```

---

## Running Queries

**Via curl** (replace `QUERY` with URL-encoded SPARQL):
```bash
curl -G http://localhost:3030/normgraph/sparql \
  --data-urlencode "query=$(cat query.sparql)"
```

**Via Fuseki UI**: Navigate to http://localhost:3030 → `normgraph` → "query" tab.

**Via rdflib** (Python):
```python
from rdflib import ConjunctiveGraph
from rdflib.plugins.stores.sparqlstore import SPARQLStore

g = ConjunctiveGraph(store=SPARQLStore("http://localhost:3030/normgraph/sparql"))
for row in g.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"):
    print(row)
```
