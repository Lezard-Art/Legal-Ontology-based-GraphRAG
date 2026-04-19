"""
Tests for the OWL/Turtle ontology files under ontology/.

Validates that each .ttl file:
  - Parses without error using rdflib
  - Declares the expected ontology URI
  - Contains a required subset of key classes and properties

Run:
    pytest tests/test_ontology.py -v
"""
from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef

ONTO_DIR = Path(__file__).parent.parent / "ontology"
NS = Namespace("urn:normgraph:onto#")
OWL_NS = OWL
RDF_NS = RDF


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load(filename: str) -> Graph:
    path = ONTO_DIR / filename
    assert path.exists(), f"Ontology file not found: {path}"
    g = Graph()
    g.parse(str(path), format="turtle")
    return g


def assert_class(g: Graph, local_name: str) -> None:
    uri = NS[local_name]
    triples = list(g.triples((uri, RDF.type, OWL.Class)))
    assert triples, f"Expected owl:Class <{uri}> not found in graph"


def assert_datatype_property(g: Graph, local_name: str) -> None:
    uri = NS[local_name]
    triples = list(g.triples((uri, RDF.type, OWL.DatatypeProperty)))
    assert triples, f"Expected owl:DatatypeProperty <{uri}> not found in graph"


def assert_object_property(g: Graph, local_name: str) -> None:
    uri = NS[local_name]
    triples = list(g.triples((uri, RDF.type, OWL.ObjectProperty)))
    assert triples, f"Expected owl:ObjectProperty <{uri}> not found in graph"


def assert_ontology_uri(g: Graph, expected_uri: str) -> None:
    uri = URIRef(expected_uri)
    triples = list(g.triples((uri, RDF.type, OWL.Ontology)))
    assert triples, f"Expected owl:Ontology declaration <{uri}> not found"


# ---------------------------------------------------------------------------
# ufo-l.ttl — Layer 1: Legal Positions
# ---------------------------------------------------------------------------


class TestUFOL:
    def setup_method(self) -> None:
        self.g = load("ufo-l.ttl")

    def test_parses_cleanly(self) -> None:
        assert len(self.g) > 0

    def test_ontology_uri(self) -> None:
        assert_ontology_uri(self.g, "urn:normgraph:onto/ufo-l")

    def test_core_classes(self) -> None:
        for cls in [
            "LegalAgent",
            "NamedPerson",
            "NamedOrganization",
            "LegalRole",
            "GovernmentEntity",
            "LegalRelator",
            "RightDutyRelator",
            "NoRightPermissionRelator",
            "PowerLiabilityRelator",
            "DisabilityImmunityRelator",
            "LibertyRelator",
            "ActionDescriptor",
            "LogicalCondition",
        ]:
            assert_class(self.g, cls)

    def test_key_datatype_properties(self) -> None:
        for prop in [
            "agentId",
            "agentType",
            "agentName",
            "isWildcard",
            "relatorId",
            "relatorType",
            "relatorStatus",
            "defeasibilityStatus",
            "rightType",
            "dutyType",
            "permissionType",
            "noRightType",
            "powerType",
            "liabilityType",
            "actionVerb",
            "actionPolarity",
            "conditionType",
            "simpleStatement",
        ]:
            assert_datatype_property(self.g, prop)

    def test_key_object_properties(self) -> None:
        for prop in [
            "holderAgent",
            "addresseeAgent",
            "affectedRelator",
            "triggersCondition",
            "immunityExceptions",
            "permissions",
            "actionDescriptor",
            "conditionChildren",
        ]:
            assert_object_property(self.g, prop)

    def test_subclass_relations(self) -> None:
        g = self.g
        # NamedPerson subClassOf LegalAgent
        assert (NS.NamedPerson, RDFS.subClassOf, NS.LegalAgent) in g
        # RightDutyRelator subClassOf LegalRelator
        assert (NS.RightDutyRelator, RDFS.subClassOf, NS.LegalRelator) in g
        # PowerLiabilityRelator subClassOf LegalRelator
        assert (NS.PowerLiabilityRelator, RDFS.subClassOf, NS.LegalRelator) in g


# ---------------------------------------------------------------------------
# legalruleml.ttl — Layer 2: Normative Rules
# ---------------------------------------------------------------------------


class TestLegalRuleML:
    def setup_method(self) -> None:
        self.g = load("legalruleml.ttl")

    def test_parses_cleanly(self) -> None:
        assert len(self.g) > 0

    def test_ontology_uri(self) -> None:
        assert_ontology_uri(self.g, "urn:normgraph:onto/legalruleml")

    def test_core_classes(self) -> None:
        for cls in [
            "NormativeStatement",
            "PrescriptiveStatement",
            "ConstitutiveStatement",
            "PenaltyStatement",
            "OverridingRule",
            "Amendment",
            "OffsetRange",
        ]:
            assert_class(self.g, cls)

    def test_key_datatype_properties(self) -> None:
        for prop in [
            "statementId",
            "statementType",
            "sourceText",
            "defeasibilityStrength",
            "deonticOperator",
            "ruleStrength",
            "definedTerm",
            "definition",
            "penaltyType",
            "overrideType",
            "amendmentType",
            "startOffset",
            "endOffset",
        ]:
            assert_datatype_property(self.g, prop)

    def test_key_object_properties(self) -> None:
        for prop in [
            "sourceOffsets",
            "createLegalPositions",
            "condition",
            "consequence",
            "defenses",
            "superiorityRelations",
            "createsNewRights",
        ]:
            assert_object_property(self.g, prop)

    def test_subclass_relations(self) -> None:
        g = self.g
        assert (NS.PrescriptiveStatement, RDFS.subClassOf, NS.NormativeStatement) in g
        assert (NS.ConstitutiveStatement, RDFS.subClassOf, NS.NormativeStatement) in g
        assert (NS.PenaltyStatement, RDFS.subClassOf, NS.NormativeStatement) in g


# ---------------------------------------------------------------------------
# domain.ttl — Layer 3: Domain Ontology
# ---------------------------------------------------------------------------


class TestDomain:
    def setup_method(self) -> None:
        self.g = load("domain.ttl")

    def test_parses_cleanly(self) -> None:
        assert len(self.g) > 0

    def test_ontology_uri(self) -> None:
        assert_ontology_uri(self.g, "urn:normgraph:onto/domain")

    def test_core_classes(self) -> None:
        for cls in [
            "DomainEntity",
            "Person",
            "Organization",
            "Place",
            "Activity",
            "RegulatedObject",
            "Substance",
            "Event",
            "Situation",
            "Quantity",
            "DomainModule",
        ]:
            assert_class(self.g, cls)

    def test_domain_entity_subclasses(self) -> None:
        g = self.g
        for subclass in [
            "Person",
            "Organization",
            "Place",
            "Activity",
            "RegulatedObject",
            "Substance",
            "Event",
            "Situation",
            "Quantity",
        ]:
            assert (NS[subclass], RDFS.subClassOf, NS.DomainEntity) in g, (
                f"{subclass} should be subClassOf DomainEntity"
            )

    def test_key_datatype_properties(self) -> None:
        for prop in [
            "entityId",
            "entityType",
            "entityLabel",
            "personType",
            "organizationType",
            "placeType",
            "activityType",
            "objectType",
            "substanceType",
            "regulatoryStatus",
            "eventType",
            "situationType",
            "quantityType",
            "quantityValue",
            "quantityUnit",
            "isThreshold",
            "moduleId",
            "moduleName",
        ]:
            assert_datatype_property(self.g, prop)

    def test_key_object_properties(self) -> None:
        for prop in [
            "relatedConcepts",
            "employees",
            "subOrganizations",
            "containedWithin",
            "prerequisiteEvents",
            "consequentEvents",
            "parties",
            "constituents",
            "implies",
            "moduleEntities",
            "extendsModule",
        ]:
            assert_object_property(self.g, prop)


# ---------------------------------------------------------------------------
# uslm.ttl — Layer 4: Document Structure
# ---------------------------------------------------------------------------


class TestUSLM:
    def setup_method(self) -> None:
        self.g = load("uslm.ttl")

    def test_parses_cleanly(self) -> None:
        assert len(self.g) > 0

    def test_ontology_uri(self) -> None:
        assert_ontology_uri(self.g, "urn:normgraph:onto/uslm")

    def test_core_classes(self) -> None:
        for cls in [
            "DocumentNode",
            "DefinitionsSection",
            "CrossReference",
            "DefinedTerm",
            "Provenance",
            "Change",
            "OffsetRange",
            "Amendment",
        ]:
            assert_class(self.g, cls)

    def test_definitions_section_subclass(self) -> None:
        g = self.g
        assert (NS.DefinitionsSection, RDFS.subClassOf, NS.DocumentNode) in g

    def test_key_datatype_properties(self) -> None:
        for prop in [
            "nodeId",
            "nodeType",
            "nodeTitle",
            "nodeNumber",
            "nodeOrdinal",
            "textContent",
            "referenceType",
            "term",
            "termDefinition",
            "sourceType",
            "changeType",
            "amendmentType",
        ]:
            assert_datatype_property(self.g, prop)

    def test_key_object_properties(self) -> None:
        for prop in [
            "parentNode",
            "childNodes",
            "precedingNode",
            "followingNode",
            "nodeCrossReferences",
            "sourceProvenance",
            "legislativeHistory",
            "sectionDefinedTerms",
            "sourceNode",
            "targetNode",
            "changes",
        ]:
            assert_object_property(self.g, prop)


# ---------------------------------------------------------------------------
# combined.ttl — Integration Layer
# ---------------------------------------------------------------------------


class TestCombined:
    def setup_method(self) -> None:
        self.g = load("combined.ttl")

    def test_parses_cleanly(self) -> None:
        assert len(self.g) > 0

    def test_ontology_uri(self) -> None:
        assert_ontology_uri(self.g, "urn:normgraph:onto/combined")

    def test_declares_owl_imports(self) -> None:
        g = self.g
        combined_uri = URIRef("urn:normgraph:onto/combined")
        imported = {
            str(o)
            for s, p, o in g.triples((combined_uri, OWL.imports, None))
        }
        expected = {
            "urn:normgraph:onto/ufo-l",
            "urn:normgraph:onto/legalruleml",
            "urn:normgraph:onto/domain",
            "urn:normgraph:onto/uslm",
        }
        assert expected == imported, f"owl:imports mismatch: {imported}"

    def test_integration_classes(self) -> None:
        for cls in [
            "NormativeExtraction",
            "JudicialInterpretation",
            "CanonicalAgent",
            "AliasResolutionRule",
            "AuthoritativeInterpretation",
            "Ambiguity",
            "RelatedProvision",
        ]:
            assert_class(self.g, cls)

    def test_normative_extraction_properties(self) -> None:
        for prop in [
            "extractionId",
            "extractionDate",
            "modelVersion",
            "confidenceScore",
            "requiresHumanReview",
            "parsingNotes",
        ]:
            assert_datatype_property(self.g, prop)

    def test_normative_extraction_object_properties(self) -> None:
        for prop in [
            "sourceDocument",
            "normativeStatements",
            "createdPositions",
            "domainEntities",
            "usedDefinitions",
            "relatedProvisions",
            "overridingRules",
            "interpretations",
            "ambiguities",
        ]:
            assert_object_property(self.g, prop)

    def test_judicial_interpretation_properties(self) -> None:
        for prop in [
            "interpretationId",
            "caseName",
            "courtName",
            "courtLevel",
            "holding",
            "interpretationAuthority",
        ]:
            assert_datatype_property(self.g, prop)

    def test_canonical_agent_properties(self) -> None:
        for prop in ["canonicalId", "primaryLabel", "canonicalAliases", "isLegalRole"]:
            assert_datatype_property(self.g, prop)

    def test_alias_resolution_rule_properties(self) -> None:
        assert_datatype_property(self.g, "aliasPattern")
        assert_object_property(self.g, "resolvesTo")

    def test_ambiguity_properties(self) -> None:
        for prop in ["ambiguityId", "ambiguityType", "ambiguousText"]:
            assert_datatype_property(self.g, prop)

    def test_related_provision_properties(self) -> None:
        for prop in ["relatedProvisionUri", "relationshipType"]:
            assert_datatype_property(self.g, prop)
