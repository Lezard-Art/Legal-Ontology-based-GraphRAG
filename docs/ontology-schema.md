# Combined Normative Ontology Schema
## A Unified Four-Layer Ontology for LLM-Driven Statutory Knowledge Extraction

**Version:** 1.0
**Date:** 2026-04-02
**Purpose:** This document defines the complete ontological structure for extracting, representing, and reasoning about US federal statutory law as a formal normative knowledge graph. It serves as the canonical reference document for parsing models and downstream reasoning systems.

**Target User:** An LLM model tasked with reading statutory text (legislation, regulations, case law) and producing structured normative extractions in the format specified below.

---

## Table of Contents

1. [Document Overview](#document-overview)
2. [Namespace and URI Conventions](#namespace-and-uri-conventions)
3. [Layer 1: Legal Positions (UFO-L)](#layer-1-legal-positions-ufo-l)
4. [Layer 2: Normative Rules (LegalRuleML)](#layer-2-normative-rules-legalruleml)
5. [Layer 3: Domain Ontology](#layer-3-domain-ontology)
6. [Layer 4: Document Structure (USLM/Akoma Ntoso)](#layer-4-document-structure-uslmakoma-ntoso)
7. [Unified NormativeExtraction Output Schema](#unified-normativeextraction-output-schema)
8. [Entity Resolution and Canonical Identifiers](#entity-resolution-and-canonical-identifiers)
9. [Interpretation and Judicial Override](#interpretation-and-judicial-override)
10. [Example Extractions](#example-extractions)
11. [Annotation Guidelines for Parsing Models](#annotation-guidelines-for-parsing-models)

---

## Document Overview

This ontology represents four conceptual layers of US statutory law:

1. **Legal Positions (UFO-L layer)**: The deontic backbone — who holds which Hohfeldian legal position (Right, Duty, Power, etc.) against whom, regarding what action. This layer is based on Hohfeld's fundamental legal conceptions extended by Alexy's triadic model to distinguish positive actions from negative (omissions).

2. **Normative Rules (LegalRuleML layer)**: The rule logic — how statutory provisions create, modify, and extinguish legal positions through prescriptive statements, constitutive definitions, and penalty rules. This layer captures defeasibility (when rules can be overridden), temporal parameters, and conflict resolution.

3. **Domain Ontology**: The real-world things that norms regulate — persons, organizations, places, activities, objects, substances, events, and thresholds. These are the subjects and objects of normative statements.

4. **Document Structure (USLM/Akoma Ntoso)**: The legislative hierarchy — how statutory text is organized from Title down to paragraph-level, with cross-references, amendment metadata, and source provenance.

A **NormativeExtraction** object (Section 7) bundles all four layers together, representing the structured semantic content of a single statutory provision or judicial interpretation. This is what the parser produces for each provision it reads.

---

## Namespace and URI Conventions

All ontology entities use IRIs (Internationalized Resource Identifiers) following these conventions:

### Base Namespaces

```
urn:uslm:                           -- US Legal Markup (document structure, provisions)
urn:uslm:legal-position:            -- Legal Positions (Hohfeldian and Alexy extensions)
urn:uslm:normative-rule:            -- Normative Rules (prescriptive, constitutive, penalty)
urn:uslm:domain:                    -- Domain Ontology (real-world concepts)
urn:uslm:entity:                    -- Canonical entity identifiers (agents, places, etc.)
urn:uslm:interpretation:            -- Judicial interpretations (court holdings, overrides)
urn:uslm:statute:usc:{title}/{section}  -- Canonical US Code reference
urn:uslm:cfr:{title}/{section}      -- Canonical Code of Federal Regulations reference
urn:uslm:statute:public-law:{congress}/{number}  -- Public Law identifier
```

### Entity Naming Patterns

- **Legal Positions**: `urn:uslm:legal-position:{statute-id}:{position-type}:{holder-id}:{addressee-id}:{action-id}:{polarity}`
  - Example: `urn:uslm:legal-position:42-usc-1983:right:state-official:citizen:deprive-liberty:positive`

- **Normative Rules**: `urn:uslm:normative-rule:{statute-id}:{rule-sequence-number}`
  - Example: `urn:uslm:normative-rule:42-usc-1983:rule-1`

- **Agents**: `urn:uslm:entity:agent:{category}:{identifier}:{jurisdiction}`
  - Example: `urn:uslm:entity:agent:person:john-doe:*` (wildcard jurisdiction = any person)
  - Example: `urn:uslm:entity:agent:official:epa-administrator:federal` (EPA Administrator role)

- **Provisions**: `urn:uslm:statute:usc:42/1983` (standard US Code format)

---

## Layer 1: Legal Positions (UFO-L)

Legal Positions are the fundamental relational units in law. Every statutory provision, when fully unpacked, creates, modifies, or extinguishes legal positions. This layer combines:

- **Hohfeld's eight fundamental legal conceptions** (Right, Duty, Liberty, NoRight, Power, Disability, Immunity, Subjection)
- **Alexy's triadic model** (distinguishing positive actions from negative/omissions)
- **Correlative structure** (every position implies a counterpart position in another agent)

### Core Classes

#### LegalAgent
A participant in a legal relation. Can be a named individual, an organization, or a **legal role** (e.g., "any person", "the Secretary", "a federal officer").

```
Class: LegalAgent
  Properties:
    agentId: URI [required]
      -- Canonical identifier following namespace conventions
    agentType: Enum [required]
      -- One of: NamedPerson, NamedOrganization, LegalRole, GovernmentEntity
    agentName: String [required]
      -- Natural language name (e.g., "John Smith" or "EPA Administrator")
    agentDescription: String [optional]
      -- Clarification (e.g., "any person acting under color of state law")
    aliases: List<String> [optional]
      -- Alternative names/references in statute (e.g., "she", "the Director", "Defendant")
    jurisdiction: URI [optional]
      -- Jurisdiction(s) in which agent acts; URI from Domain Ontology
      -- Examples: urn:uslm:domain:jurisdiction:federal, urn:uslm:domain:jurisdiction:state
    canonicalDefinition: String [optional]
      -- Source statute section that defines this role
    isWildcard: Boolean [default: false]
      -- true = agent represents a category ("any person"), false = specific individual
```

**Subtypes of LegalAgent:**

- **NamedPerson**: A specific individual (proper name). Used primarily in contracts or specific case facts, rarely in statutes.
- **NamedOrganization**: A specific legal entity (e.g., "The United States", "State Department").
- **LegalRole**: A generic category (e.g., "any person", "a federal officer", "the employer"). This is the most common in statutory law.
- **GovernmentEntity**: A public body with authority (e.g., "EPA", "Secretary of Labor"). Subtype of both NamedOrganization and LegalRole.

#### LegalRelator
A legal relation that bundles two or more correlative legal positions. This is what Hohfeld's theory is about: relations are *relational*. A right in one party always implies a duty in another.

```
Class: LegalRelator
  Properties:
    relatorId: URI [required]
    relatorType: Enum [required]
      -- One of: RightDutyRelator, NoRightPermissionRelator, PowerLiabilityRelator,
      --         DisabilityImmunityRelator, LibertyRelator
    holderAgent: LegalAgent [required]
      -- The agent that holds the "active" position (right, permission, power, immunity)
    addresseeAgent: LegalAgent [required]
      -- The agent that holds the "passive" position (duty, no-right, liability, disability)
    sourceProvision: URI [required]
      -- Which statute/section created this relator
    effectiveDate: DateTime [optional]
      -- When the relator comes into effect
    expirationDate: DateTime [optional]
      -- When the relator ceases
    status: Enum [default: Active]
      -- One of: Pending, Active, Suspended, Terminated, Void
    defeasibilityStatus: Enum [default: Strict]
      -- One of: Strict (cannot be overridden), Defeasible (can be overcome by stronger rule),
      --         Defeater (overrides a defeasible rule)
```

#### RightDutyRelator
Represents Hohfeld's prototypical correlative pair. One agent has a right; the correlate agent has a duty.

```
Class: RightDutyRelator extends LegalRelator
  relatorType: always RightDutyRelator

  Properties:
    rightType: Enum [required]
      -- One of: RightToAction, RightToOmission
    dutyType: Enum [required]
      -- Correlative to rightType:
      -- RightToAction correlates with DutyToAct
      -- RightToOmission correlates with DutyToOmit
    actionDescriptor: ActionDescriptor [required]
      -- What action is the subject of the right/duty?
      -- See ActionDescriptor below.

  Invariants:
    - If rightType == RightToAction, then dutyType == DutyToAct
    - If rightType == RightToOmission, then dutyType == DutyToOmit
    - holderAgent.holds(Right_) iff addresseeAgent.holds(Duty_)
```

#### NoRightPermissionRelator
Hohfeld's second fundamental pair: Permission and No-Right. One agent has a permission (right to do X without violating any duty); the correlate agent has no right to interfere.

```
Class: NoRightPermissionRelator extends LegalRelator
  relatorType: always NoRightPermissionRelator

  Properties:
    permissionType: Enum [required]
      -- One of: PermissionToAct, PermissionToOmit
    noRightType: Enum [required]
      -- Correlative to permissionType:
      -- PermissionToAct correlates with NoRightToAction
      -- PermissionToOmit correlates with NoRightToOmission
    actionDescriptor: ActionDescriptor [required]
      -- What action is permitted?

  Invariants:
    - If permissionType == PermissionToAct, then noRightType == NoRightToAction
    - If permissionType == PermissionToOmit, then noRightType == NoRightToOmission
    - holderAgent.has(Permission_) iff addresseeAgent.has(NoRight_)
```

#### PowerLiabilityRelator
Hohfeld's third fundamental pair, extended by Alexy. One agent has a power (capacity to change legal relations); the correlate agent is subject to that power (liability/subjection).

```
Class: PowerLiabilityRelator extends LegalRelator
  relatorType: always PowerLiabilityRelator

  Properties:
    powerType: Enum [required]
      -- One of: PowerToCreate, PowerToModify, PowerToExtinguish
    liabilityType: Enum [required]
      -- Correlative to powerType:
      -- PowerToCreate correlates with LiabilityToCreation
      -- PowerToModify correlates with LiabilityToModification
      -- PowerToExtinguish correlates with LiabilityToExtinguishment
    affectedRelator: LegalRelator [optional]
      -- Which legal relator does this power affect? (what is created/modified/extinguished?)
      -- May be null if power affects a broad class of relations.
    triggersCondition: LogicalCondition [optional]
      -- Condition that activates the power. See LogicalCondition below.
    exerciseMethod: String [optional]
      -- How is the power exercised? (e.g., "written notice", "unilateral declaration")

  Invariants:
    - If powerType == PowerToCreate, then liabilityType == LiabilityToCreation
    - If powerType == PowerToModify, then liabilityType == LiabilityToModification
    - If powerType == PowerToExtinguish, then liabilityType == LiabilityToExtinguishment
```

#### DisabilityImmunityRelator
Hohfeld's fourth fundamental pair. One agent has an immunity (cannot have a power exercised against them); the correlate agent has a disability (lacks the power to affect that immunity).

```
Class: DisabilityImmunityRelator extends LegalRelator
  relatorType: always DisabilityImmunityRelator

  Properties:
    immunityType: Enum [required]
      -- General label (e.g., "Immunity from Suit", "Immunity from Termination")
    disabilityType: Enum [required]
      -- Correlative label (e.g., "Disability to Sue", "Disability to Terminate")
    scope: String [required]
      -- Scope of the immunity (what cannot be done to the holder?)
    exceptions: List<LogicalCondition> [optional]
      -- Conditions that waive or limit the immunity

  Invariants:
    - holderAgent cannot have a power exercised against them (within scope)
    - addresseeAgent lacks the power to exercise against holderAgent
```

#### LibertyRelator
A complex position: Liberty is the composite of Permission to Act AND Permission to Omit. Its correlate is the composite of NoRight to Act AND NoRight to Omit.

```
Class: LibertyRelator extends LegalRelator
  relatorType: always LibertyRelator

  Properties:
    actionDescriptor: ActionDescriptor [required]
      -- What is the agent at liberty to do (or not do)?
    permissions: List<NoRightPermissionRelator> [required]
      -- The two component relators:
      -- 1. PermissionToAct + NoRightToAction
      -- 2. PermissionToOmit + NoRightToOmission

  Invariants:
    - Must contain exactly 2 NoRightPermissionRelator instances
    - holderAgent has freedom to act or not act without violating a duty to others
```

### Supporting Structures for Legal Positions

#### ActionDescriptor
Describes what action (or omission) is the subject of a legal position. Actions can be described at various levels of abstraction.

```
Class: ActionDescriptor
  Properties:
    actionId: URI [required]
    actionVerb: String [required]
      -- The action (e.g., "deprive", "discharge", "employ")
    actionPolarity: Enum [required]
      -- One of: Positive (doing X), Negative (not doing X / refraining from X)
    actionObject: String [optional]
      -- What is acted upon (e.g., "liberty", "employment")
    actionObjectUri: URI [optional]
      -- Canonical URI of the object if it's in the domain ontology
    actionMannerConstraints: List<String> [optional]
      -- How must the action be performed? (e.g., "without due process", "arbitrarily")
    actionScope: String [optional]
      -- Scope/context of the action (e.g., "under color of state law")
    canonicalDefinition: URI [optional]
      -- Source statute that defines this action
```

#### LogicalCondition
Represents a condition that triggers or constrains a legal position. Can be simple (boolean) or complex (nested logical expressions).

```
Class: LogicalCondition
  Properties:
    conditionId: URI [required]
    conditionType: Enum [required]
      -- One of: Simple, Conjunction (AND), Disjunction (OR), Negation (NOT), Conditional (IF-THEN)
    -- For Simple conditions:
    simpleStatement: String [optional]
      -- Natural language description (e.g., "the person is a federal officer")
    simpleStatementUri: URI [optional]
      -- URI of the domain concept being referenced
    -- For compound conditions:
    children: List<LogicalCondition> [optional]
      -- Nested sub-conditions
    -- Temporal parameters:
    activeAfter: DateTime [optional]
    activeBefore: DateTime [optional]
    temporalDuration: Duration [optional]
      -- How long does the condition apply? (e.g., "6 months")
```

---

## Layer 2: Normative Rules (LegalRuleML)

This layer captures the rule logic of legislation: how provisions prescribe behavior, define terms, specify consequences, and interact with each other through override relations.

### Core Classes

#### NormativeStatement
The superclass for all rule-like provisions. Represents any statement that imposes, permits, defines, or enforces obligations.

```
Class: NormativeStatement
  Properties:
    statementId: URI [required]
    statementType: Enum [required]
      -- One of: PrescriptiveStatement, ConstitutiveStatement, PenaltyStatement
    sourceProvision: URI [required]
      -- Which statute/section contains this statement
    sourceText: String [required]
      -- The exact text from the statute
    sourceOffsets: OffsetRange [required]
      -- Character offsets in the source document
      -- See OffsetRange below
    language: String [default: "en"]
    effectiveDate: DateTime [optional]
    expirationDate: DateTime [optional]
    defeasibilityStrength: Enum [required]
      -- One of: Strict, Defeasible, Defeater
      -- Strict: cannot be overridden
      -- Defeasible: can be overridden by a stronger rule
      -- Defeater: itself overrides a defeasible rule
    defeasesRules: List<URI> [optional]
      -- Which other rules does this rule defeat/override?
    isDefeatedBy: List<URI> [optional]
      -- Which rules defeat this one?
    superiorityRelations: List<OverridingRule> [optional]
      -- See OverridingRule below
```

#### PrescriptiveStatement
Imposes an obligation, prohibition, or permission on agents. The normative operator is what makes it prescriptive.

```
Class: PrescriptiveStatement extends NormativeStatement
  Properties:
    deonticOperator: Enum [required]
      -- One of: Obligation, Prohibition, Permission
    -- Obligation: agent MUST perform action (creates duty)
    -- Prohibition: agent MUST NOT perform action (creates prohibition = duty to omit)
    -- Permission: agent MAY perform action (creates permission and no-right)

    createLegalPositions: List<LegalRelator> [required]
      -- Which legal relators does this statement create?
      -- For Obligation: creates a RightDutyRelator (creditor has right, debtor has duty)
      -- For Prohibition: creates a RightDutyRelator with DutyToOmit
      -- For Permission: creates a NoRightPermissionRelator

    condition: LogicalCondition [required]
      -- IF this condition holds (antecedent)
    consequence: LogicalCondition [required]
      -- THEN this must be done (consequent)
      -- The consequence describes the required state of affairs or action

    ruleStrength: Enum [required]
      -- One of:
      -- → : Strict rule (if condition, then consequence always holds)
      -- ⇒ : Defeasible rule (if condition, then consequence usually/typically holds, unless overridden)
      -- ~> : Defeater rule (if condition, then the defeasible rule it targets does NOT hold)

    targetAgent: LegalAgent [required]
      -- To whom is the obligation/prohibition/permission directed?
    affectedAgent: LegalAgent [optional]
      -- If different from targetAgent, who else is affected?

    deadline: DateTime [optional]
      -- By when must the obligation be fulfilled?
    deadlineDuration: Duration [optional]
      -- Relative deadline (e.g., "within 30 days")

    exceptions: List<LogicalCondition> [optional]
      -- Conditions under which the prescription does NOT apply

    crossReferences: List<URI> [optional]
      -- Related provisions that constrain or clarify this rule
```

#### ConstitutiveStatement
Defines what something is, for purposes of the statute. Does not directly create obligations but provides definitions that other rules depend on.

```
Class: ConstitutiveStatement extends NormativeStatement
  Properties:
    definedTerm: String [required]
      -- What term is being defined? (e.g., "deprive", "under color of state law")
    definedTermUri: URI [optional]
      -- Canonical URI in Domain Ontology

    definition: String [required]
      -- The definition (e.g., "For purposes of this section, 'under color of state law' means...")

    definingStructure: DomainOntologyReference [optional]
      -- If the definition maps to a domain concept, reference it

    scope: String [required]
      -- Scope of applicability (e.g., "For purposes of this Chapter")

    applicableTo: List<URI> [optional]
      -- Which rules/relators does this definition constrain?

    isInterpreted: Boolean [optional]
      -- Has this definition been judicially interpreted differently than the text suggests?
```

#### PenaltyStatement
Specifies consequences of violation. Creates new obligations or legal positions that are triggered by breach.

```
Class: PenaltyStatement extends NormativeStatement
  Properties:
    triggeredBy: URI [required]
      -- Which obligation/rule, when violated, triggers this penalty?

    penaltyType: Enum [required]
      -- One of: CivilLiability, CriminalPenalty, AdministrativePenalty,
      --         Injunction, EquitableLiability, RightsCreation

    penaltyDescription: String [required]
      -- What is the penalty? (e.g., "liable in an action at law or in equity")

    penaltyAmount: String [optional]
      -- If monetary: amount or formula (e.g., "$10,000 per violation", "treble damages")

    createsNewRights: List<LegalRelator> [optional]
      -- Penalties create new legal positions. Examples:
      -- - A violation of duty creates a right to sue (Right-Duty: plaintiff has right to remedy, defendant has duty to pay)
      -- - Creates a Power: injured party has power to obtain injunction

    createsNewDuties: List<LegalRelator> [optional]
      -- New duties imposed on violator

    isStrictLiability: Boolean [optional]
      -- Is liability imposed regardless of intent/fault?

    defenses: List<LogicalCondition> [optional]
      -- What conditions excuse or mitigate the penalty?

    lossesRecoverable: String [optional]
      -- What types of loss can be recovered? (e.g., "economic damages", "emotional distress", "punitive damages")
```

### Override and Superiority Relations

#### OverridingRule
Captures how one rule overrides another — lex specialis, lex posterior, lex superior, defeasibility, etc.

```
Class: OverridingRule
  Properties:
    overriddenRuleId: URI [required]
      -- Which rule is being overridden?
    overridingRuleId: URI [required]
      -- Which rule does the overriding?
    overrideType: Enum [required]
      -- One of:
      -- LexSpecialis: more specific rule overrides general rule
      -- LexPosterior: later rule overrides earlier rule (when both apply)
      -- LexSuperior: higher authority overrides lower (federal > state)
      -- Defeasibility: defeasible rule overcome by defeater rule
      -- ExceptionClause: explicit exception in a statute

    priority: Integer [optional]
      -- If multiple overrides apply, numeric priority

    scope: String [optional]
      -- In what context does the override apply?

    sourceAuthority: URI [optional]
      -- Court decision or statute that established this override
```

### Temporal and Amendment Parameters

#### Amendment
Tracks how legislation has been modified over time.

```
Class: Amendment
  Properties:
    amendmentId: URI [required]
    originalProvisionUri: URI [required]
      -- What provision was amended?
    publicLawSource: URI [required]
      -- e.g., urn:uslm:statute:public-law:117/123 (Public Law 117-123)
    dateEnacted: DateTime [required]
    effectiveDate: DateTime [required]
    sunsetDate: DateTime [optional]
      -- When does the amendment expire (if temporary)?

    amendmentType: Enum [required]
      -- One of: Added, Modified, Repealed, Reenacted

    amendedText: String [optional]
      -- The new text (if Modified or Added)

    previousText: String [optional]
      -- The old text (for comparison, if Modified)

    repealdDate: DateTime [optional]
      -- If Repealed, when does repeal take effect?

    successorProvision: URI [optional]
      -- If repealed, what provision(s) replace it?
```

---

## Layer 3: Domain Ontology

The domain ontology represents the real-world concepts that statutes regulate. This is where abstract legal positions become concrete.

### Core Domain Categories

#### DomainEntity
The superclass for all domain concepts.

```
Class: DomainEntity
  Properties:
    entityId: URI [required]
    entityType: Enum [required]
      -- One of: Person, Organization, Place, Activity, Object, Substance, Event, Situation, Quantity
    label: String [required]
    description: String [optional]
    definedIn: URI [optional]
      -- Which statute defines this concept?
    synonyms: List<String> [optional]
      -- Alternative names
    relatedConcepts: List<URI> [optional]
      -- Other domain entities related to this one
```

#### Person
Represents persons/individuals.

```
Class: Person extends DomainEntity
  Properties:
    -- Inherits: entityId, label, description, etc.
    firstName: String [optional]
    lastName: String [optional]
    personType: Enum [optional]
      -- One of: Individual, LegalFictionalPerson, Deceased, Incapacitated, etc.
    citizenship: String [optional]
    residenceJurisdiction: URI [optional]
    roleCategoryInLaw: List<String> [optional]
      -- What roles can this person play? (e.g., "employee", "creditor", "plaintiff")
```

#### Organization
Represents organizations, agencies, corporations.

```
Class: Organization extends DomainEntity
  Properties:
    organizationType: Enum [required]
      -- One of: Corporation, Partnership, GovernmentAgency, NonProfit, Union, etc.
    isGovernmentEntity: Boolean
    jurisdiction: URI [optional]
      -- Jurisdiction of incorporation/authority
    legalAuthority: String [optional]
      -- Source statute establishing this entity
    capacity: String [optional]
      -- What can this organization legally do? (determined by statute)
    employees: List<Person> [optional]
    subOrganizations: List<Organization> [optional]
```

#### Place
Represents jurisdictions, territories, physical locations.

```
Class: Place extends DomainEntity
  Properties:
    placeType: Enum [required]
      -- One of: State, County, Municipality, FederalTerritory, NativeAmericanLand, InternationalLocation
    jurisdiction: URI [optional]
      -- If this is a jurisdiction, its canonical URI
    containedWithin: URI [optional]
      -- Broader jurisdiction (state contains county, etc.)
    legalStatus: String [optional]
      -- E.g., "independent nation", "US state", "incorporated city"
    governingAuthority: URI [optional]
      -- Which government body has authority here?
```

#### Activity
Represents actions, processes, or conduct that law regulates.

```
Class: Activity extends DomainEntity
  Properties:
    activityType: Enum [required]
      -- One of: Employment, Commerce, Transportation, Communication, Scientific, Medical,
      --         LandUse, Financial, PublicService, CriminalConduct, etc.
    legalRegulation: String [optional]
      -- Brief description of how law regulates this activity
    requiredCertifications: List<String> [optional]
      -- What qualifications must actors have?
    requiredPermits: List<String> [optional]
      -- What permissions must be obtained?
    standardsOrRequirements: List<String> [optional]
      -- What standards must the activity meet?
```

#### Object
Represents tangible things (property, goods, equipment, etc.).

```
Class: Object extends DomainEntity
  Properties:
    objectType: Enum [required]
      -- One of: RealProperty, PersonalProperty, Money, Security, Vehicle, Weapon, etc.
    isRegulated: Boolean
    regulatoryFramework: String [optional]
      -- E.g., "subject to FDA regulation"
    ownershipRules: String [optional]
      -- Who can own this? Any restrictions?
    usageRestrictions: List<String> [optional]
      -- Permitted/prohibited uses
    valueOrQuantification: String [optional]
      -- How is value measured? (monetary, by weight, by volume, etc.)
```

#### Substance
Represents material substances (chemicals, drugs, etc.).

```
Class: Substance extends DomainEntity
  Properties:
    substanceType: Enum [required]
      -- One of: Drug, Chemical, Biological, Controlled, Hazardous, etc.
    regulatoryStatus: Enum [required]
      -- One of: Prohibited, Controlled, Licensed, Approved, Unregulated
    controlLevel: String [optional]
      -- If controlled: "Schedule I", "List Chemical", etc.
    usagePermissions: List<String> [optional]
      -- Who can use it and under what conditions?
    possessionRules: String [optional]
      -- Who can possess it? Quantity limits?
```

#### Event
Represents discrete happenings in time.

```
Class: Event extends DomainEntity
  Properties:
    eventType: Enum [required]
      -- One of: LegalProceeding, Injury, Violation, Approval, Denial, Notification, etc.
    timing: DateTime [optional]
    duration: Duration [optional]
    prerequisiteEvents: List<URI> [optional]
      -- Events that must occur first
    consequentEvents: List<URI> [optional]
      -- Events triggered by this one
    parties: List<LegalAgent> [optional]
      -- Who is involved?
```

#### Situation
Represents states of affairs (conditions) that can hold over time intervals.

```
Class: Situation extends DomainEntity
  Properties:
    situationType: Enum [required]
      -- One of: Legal Status, Physical Condition, Contractual State, Emergency, etc.
    temporalExtent: TimeInterval [optional]
      -- When does this situation hold?
    constituents: List<DomainEntity> [optional]
      -- What entities make up this situation?
    implies: List<Situation> [optional]
      -- What other situations does this imply?
```

#### Quantity / Threshold
Represents numerical or measurable quantities used in legal rules (e.g., monetary amounts, time periods, age thresholds).

```
Class: Quantity extends DomainEntity
  Properties:
    quantityType: Enum [required]
      -- One of: Monetary, Temporal, Age, Weight, Volume, Distance, Percentage, etc.
    value: Number [required]
    unit: String [required]
      -- "dollars", "days", "years", "pounds", "gallons", etc.
    isThreshold: Boolean [optional]
      -- Is this a boundary that triggers legal effects?
    adjustmentMechanism: String [optional]
      -- How is this amount adjusted over time? (e.g., "annually for inflation", "by regulation")
    sourceStatute: URI [optional]
```

### Domain Module Pattern

The domain ontology is organized as composable **modules**. Each statutory domain (employment, environmental, securities, etc.) gets its own module that extends the core domain categories.

```
Class: DomainModule
  Properties:
    moduleId: URI [required]
      -- E.g., urn:uslm:domain:module:employment
    moduleName: String [required]
    description: String
    applicableStatutes: List<URI> [required]
      -- Which statutes does this module cover?
    entities: List<DomainEntity> [required]
      -- All entities defined in this module
    version: String
    extendsModule: URI [optional]
      -- If this module builds on another module
```

---

## Layer 4: Document Structure (USLM/Akoma Ntoso)

This layer captures the hierarchical and structural organization of legislation as it appears in the United States Code, Code of Federal Regulations, and Public Laws.

### Document Hierarchy

US statutory documents follow a strict hierarchy. All are captured as DocumentNode objects with parent-child relationships.

```
Class: DocumentNode
  Properties:
    nodeId: URI [required]
      -- Unique identifier for this provision
      -- Format: urn:uslm:statute:usc:{title}/{section}[/{subsection}/...]
    nodeType: Enum [required]
      -- One of: Title, Subtitle, Chapter, Subchapter, Part, Subpart,
      --         Section, Subsection, Paragraph, Clause, Subclause
    title: String [required]
      -- The official heading
    number: String [required]
      -- The ordinal number (e.g., "§ 1983", "42 USC 1983")
    ordinal: Integer [required]
      -- Sequence number among siblings (for sorting)

    textContent: String [required]
      -- The full text of this node and all children (recursive aggregation)

    shortText: String [optional]
      -- First sentence or brief summary

    parentNode: URI [optional]
      -- Reference to parent node in hierarchy
    childNodes: List<URI> [optional]
      -- References to immediate child nodes (not recursive)

    precedingNode: URI [optional]
      -- Reference to the previous sibling (for reading order)
    followingNode: URI [optional]
      -- Reference to the next sibling

    crossReferences: List<CrossReference> [required]
      -- All citations to other sections within the text

    definedTerms: List<String> [optional]
      -- Terms defined in this node (extracted from "For purposes of" clauses)

    sourceProvenance: Provenance [required]
      -- See Provenance below

    authorityStatement: String [optional]
      -- E.g., "Authorized by 42 USC § 1981a"

    legislativeHistory: List<Amendment> [optional]
      -- All amendments that affected this node
```

### Cross-References

```
Class: CrossReference
  Properties:
    referenceId: URI [required]
    sourceNode: URI [required]
      -- Node that contains the reference
    targetNode: URI [required]
      -- Node being referenced
    targetStatute: String [required]
      -- Canonical citation (e.g., "42 USC § 1983")
    referenceText: String [required]
      -- The actual text that makes the reference (e.g., "under 42 USC § 1983")
    referenceType: Enum [required]
      -- One of: Direct (cites specific section), Conceptual (alludes without citation),
      --         ParallelLaw (references analogous law in another jurisdiction),
      --         Implementing (implementing regulation for statute)
    semanticRelation: Enum [optional]
      -- One of: Defines, Applies, Modifies, Excepts, Incorporates, Interprets
```

### Definitions Section

Many statutes have dedicated definitions sections.

```
Class: DefinitionsSection extends DocumentNode
  Properties:
    definedTerms: List<DefinedTerm> [required]
    applicableSections: List<URI> [required]
      -- Which sections of the statute use these definitions?
```

```
Class: DefinedTerm
  Properties:
    term: String [required]
    definition: String [required]
    domainOntologyUri: URI [optional]
      -- Maps to domain ontology concept if applicable
    applicability: String [optional]
      -- "Applies throughout this chapter" or similar
```

### Provenance and Amendment Metadata

```
Class: Provenance
  Properties:
    sourceType: Enum [required]
      -- One of: OriginalEnactment, Amendment, Restatement, JudicialInterpretation

    publicLawSource: URI [optional]
      -- E.g., urn:uslm:statute:public-law:42/1983

    congressNumber: Integer [optional]
      -- E.g., 97 for Public Law 97-166

    enactmentDate: DateTime
    effectiveDate: DateTime

    changes: List<Change> [optional]
      -- What changed in this amendment?
```

```
Class: Change
  Properties:
    changeType: Enum [required]
      -- One of: TextReplaced, TextAdded, TextRemoved, SectionRepealed, etc.
    beforeText: String [optional]
    afterText: String [optional]
    changeLocation: String
      -- Description of where in the node the change occurred
```

### Offset and Position Information

For mapping back to source documents, we track character and line offsets.

```
Class: OffsetRange
  Properties:
    startOffset: Integer [required]
      -- Character offset of start in source document (0-indexed)
    endOffset: Integer [required]
      -- Character offset of end (exclusive)
    startLine: Integer [optional]
    endLine: Integer [optional]
    startColumn: Integer [optional]
    endColumn: Integer [optional]
    sourceDocument: URI [optional]
      -- If extracted from multiple documents, which one?
```

---

## Unified NormativeExtraction Output Schema

A **NormativeExtraction** object is the complete structured representation of a single statutory provision (or portion thereof, or judicial interpretation thereof). This is what the parsing model produces for each provision it reads.

### Main NormativeExtraction Class

```
Class: NormativeExtraction
  Properties:
    extractionId: URI [required]
      -- Unique ID for this extraction
      -- Format: urn:uslm:extraction:{source-provision}:{interpretation-id}:{version}

    # === Source Information ===
    sourceProvision: URI [required]
      -- The statute/regulation this extraction is from
    sourceText: String [required]
      -- The actual text being extracted
    sourceOffsets: OffsetRange [required]
      -- Where in the source document this text appears
    sourceDocument: DocumentNode [required]
      -- Reference to the full document structure

    extractionDate: DateTime [required]
    modelVersion: String [required]
      -- Which parsing model version produced this?
    confidenceScore: Float [required, range: 0.0-1.0]
      -- How confident is the model in this extraction?

    # === Normative Rule Layer ===
    normativeStatements: List<NormativeStatement> [required]
      -- All prescriptive, constitutive, and penalty statements in this provision

    # === Legal Positions Layer ===
    createdPositions: List<LegalRelator> [required]
      -- All Hohfeldian legal positions this provision creates
    modifiedPositions: List<URI> [optional]
      -- References to existing positions that this provision modifies
    extinguishedPositions: List<URI> [optional]
      -- References to positions that cease to apply

    # === Domain Layer ===
    domainEntities: List<DomainEntity> [optional]
      -- Real-world things this provision concerns
    usedDefinitions: List<DefinedTerm> [optional]
      -- Definitions from the statute that apply to this provision

    # === Relationships and Dependencies ===
    relatedProvisions: List<RelatedProvision> [optional]
      -- Other provisions this one depends on, modifies, or relates to
    overridingRules: List<OverridingRule> [optional]
      -- How this provision overrides or is overridden by others

    # === Interpretation and Judicial Layer ===
    interpretations: List<JudicialInterpretation> [optional]
      -- How courts have interpreted this provision
    currentValidInterpretation: URI [optional]
      -- Which interpretation is currently authoritative?

    # === Temporal Information ===
    effectiveDate: DateTime [optional]
    expirationDate: DateTime [optional]
    temporalScope: Duration [optional]
      -- How long does this provision apply?

    # === Quality and Uncertainty ===
    ambiguities: List<Ambiguity> [optional]
      -- Places where the text is ambiguous or disputed
    parsingNotes: String [optional]
      -- Parsing model's notes on difficult aspects
    requiresHumanReview: Boolean [default: false]
      -- Should a human expert review this?
```

### Related Provision (Cross-Document Relationships)

```
Class: RelatedProvision
  Properties:
    relatedProvisionUri: URI [required]
    relationshipType: Enum [required]
      -- One of: ModifiesOrAmends, DependsOn, ConflictsWith, ImplementedBy,
      --         AppliedBy, DefinedBy, ExceptedBy
    description: String [optional]
    semanticJustification: String [optional]
      -- Why are these related?
```

### Judicial Interpretation

```
Class: JudicialInterpretation
  Properties:
    interpretationId: URI [required]
    caseName: String [required]
      -- E.g., "United States v. Thurston"
    courtName: String [required]
      -- Which court decided this?
    courtLevel: Enum [required]
      -- One of: DistrictCourt, CircuitCourt, SupremeCourt, State, Other
    decisionDate: DateTime [required]
    caseNumber: String [optional]
    publicationCitation: String [optional]
      -- E.g., "42 F.3d 123"

    interpretedProvision: URI [required]
      -- Which statute/provision does this interpret?

    holding: String [required]
      -- What did the court hold?

    interpretsAsCreatingPositions: List<LegalRelator> [optional]
      -- How does the court interpret this provision's legal positions?
    interpretsAsProhibiting: List<String> [optional]
      -- What does the court say the statute prohibits?

    overridesStatutoryText: Boolean [default: false]
      -- Does this interpretation override the plain text?

    ifSoOverrides: List<NormativeStatement> [optional]
      -- Which statutory statements does it override?

    authority: Enum [required]
      -- One of: SupremeLawOfLand, BindingPrecedent (circuit), PersuasivePrecedent

    jurisdiction: String [optional]
      -- Geographic/jurisdictional scope of binding effect

    dissent: String [optional]
      -- If the decision wasn't unanimous, what did dissenters argue?

    retroactiveEffect: Boolean [optional]
      -- Can this interpretation be applied retroactively?

    relatedDecisions: List<URI> [optional]
      -- Other cases that cited or followed this one
```

### Ambiguity (for disambiguation)

```
Class: Ambiguity
  Properties:
    ambiguityId: URI [required]
    ambiguityType: Enum [required]
      -- One of: Syntactic (ambiguous parsing), Semantic (multiple meanings),
      --         ReferentialAmbiguity (unclear antecedent), TemporalAmbiguity (unclear timing),
      --         ScopeAmbiguity (unclear what applies to what)

    ambiguousText: String [required]
    possibleInterpretations: List<String> [required]
      -- Multiple readings of the text

    resolvingAuthority: URI [optional]
      -- Court decision or regulation that resolves it

    selectedInterpretation: String [optional]
      -- Which interpretation did we adopt, and why?
```

---

## Entity Resolution and Canonical Identifiers

One of the most challenging aspects of statutory knowledge extraction is entity resolution: recognizing that "the Secretary", "Secretary of Labor", and "Secretary" in different contexts refer to the same or different agents.

### Canonical Agent Registry

```
Class: CanonicalAgent
  Properties:
    canonicalId: URI [required]
      -- Single IRI representing this agent, used everywhere
    primaryLabel: String [required]
    aliases: List<String> [required]
      -- All names by which this agent is known in statutes
    agentType: Enum [required]
      -- Person, Organization, GovernmentOffice, Role, etc.

    # For government offices:
    createdByStatute: URI [optional]
      -- Which statute created this office?
    jurisdiction: URI [required]
    parentOrganization: URI [optional]

    # For roles (not specific individuals):
    isLegalRole: Boolean [optional]
      -- If true, this represents a position (e.g., "Attorney General"), not a person
    roleDescription: String [optional]

    # Temporal:
    creationDate: DateTime [optional]
    dissolutionDate: DateTime [optional]
      -- If the office/position was abolished

    # Relationships:
    equivalentAgents: List<URI> [optional]
      -- Agents that are considered equivalent for legal purposes
    subordinateAgents: List<URI> [optional]
      -- Agents under this one's authority
```

### Instance vs. Role Distinction

This is critical. When a statute says "the EPA Administrator", it can mean:

1. **The specific person** currently serving as Administrator (instance)
2. **The office/role** of EPA Administrator (type)

The extraction must distinguish these:

```
Example extraction for "42 USC § 1983":

    Agent A (in the statute): "a person acting under color of state law"
    canonicalId: urn:uslm:entity:agent:legal-role:color-of-state-law:*
    isWildcard: true
    isLegalRole: true
    roleDescription: "any person exercising governmental authority"

    Agent B (in the statute): "the deprivation of ... liberty"
    This is not an agent; it's an action. Represented in ActionDescriptor, not LegalAgent.

    Agent C (created by judicial interpretation):
    Name: "Federal Officers Sued in Individual Capacity"
    canonicalId: urn:uslm:entity:agent:person:federal-officer:individual-capacity
    isLegalRole: true
    roleDescription: "federal officers being sued for damages in their individual capacity"
```

### Alias Resolution Rules

When parsing, a model must resolve alias references to canonical agents:

```
Class: AliasResolutionRule
  Properties:
    aliasPattern: String [required]
      -- Regex or pattern for the alias (e.g., "the Secretary" when preceded by "Labor")
    contextRequirements: String [optional]
      -- What context resolves the alias? (e.g., "within Chapter 21 (Labor)")
    resolvesTo: URI [required]
      -- Canonical agent ID
    confidence: Float [optional]
      -- How confident are we in this resolution?
    counterExamples: List<String> [optional]
      -- Cases where the pattern doesn't apply
```

---

## Interpretation and Judicial Override

The ontology treats judicial interpretations not as metadata but as **first-class entities** that can create, modify, or override statutory legal positions.

### How Court Decisions Interact with Statutory Provisions

When a court interprets a statute, it is implicitly creating or modifying legal positions. Example:

**Statutory text (42 USC § 1983):**
```
"Every person who, under color of any statute ... subjects ...
any citizen of the United States ... to the deprivation of any rights ...
shall be liable to the party injured in an action at law, suit in equity,
or other proper proceeding for redress."
```

**What the statute creates (plain reading):**
- RightDutyRelator: Citizen (holder) has a Right to Sue; State Official (addressee) has a Duty to Respect Rights
- NoRightPermissionRelator: Citizen (holder) has Permission to bring suit; State (addressee) has NoRight to prevent suit
- PowerLiabilityRelator: Citizen (creditor) has Power to sue; State Official (debtor) has Liability to damages

**How courts interpret this (Monell v. Department of Social Services, 436 U.S. 658, 1978):**
- The Court held that municipalities are "persons" under § 1983
- This creates a NEW instance of RightDutyRelator that the statutory text doesn't explicitly state
- The Court simultaneously held that municipalities cannot face vicarious liability
- This creates a DISABILITY for municipal officials (they lack power to expose municipalities unless acting via official policy)

The ontology represents this as:

```
NormativeExtraction for "42 USC § 1983 as interpreted by Monell":

    sourceProvision: urn:uslm:statute:usc:42/1983

    createdPositions:
      - RightDutyRelator (statutory):
        holderAgent: urn:uslm:entity:agent:person:citizen:*
        addresseeAgent: urn:uslm:entity:agent:person:state-official:*
        rightType: RightToAction (sue)
        sourceProvision: urn:uslm:statute:usc:42/1983

      - RightDutyRelator (judicial interpretation, Monell):
        holderAgent: urn:uslm:entity:agent:person:citizen:*
        addresseeAgent: urn:uslm:entity:agent:organization:municipality:*
        rightType: RightToAction (sue)
        sourceProvision: urn:uslm:statute:usc:42/1983
        interpreterDecision: urn:uslm:interpretation:case:monell-v-department-1978
        confidence: 1.0 (Supreme Court, explicit holding)

      - DisabilityImmunityRelator (judicial interpretation, Monell):
        holderAgent: urn:uslm:entity:agent:person:municipality-official:*
        immunityType: "Immunity from Vicarious Liability"
        sourceProvision: urn:uslm:statute:usc:42/1983
        interpreterDecision: urn:uslm:interpretation:case:monell-v-department-1978
        exceptions:
          - Condition: "Municipality acts via official policy or custom"
            Effect: "Immunity does not apply"

    interpretations:
      - JudicialInterpretation:
        caseName: "Monell v. Department of Social Services"
        decisionDate: 1978-06-06
        holding: "Municipalities are 'persons' subject to § 1983 liability, but not for vicarious liability absent policy/custom"
        interpretsAsCreatingPositions:
          - RightDutyRelator (citizen vs. municipality)
        authority: SupremeLawOfLand
```

### Multiple Interpretations at Different Authority Levels

Different courts may interpret the same statute differently. The ontology allows multiple NormativeExtraction instances for the same provision:

```
urn:uslm:extraction:42-usc-1983:plain-text:1.0
  -- Plain text reading
  createdPositions: [statutory positions only]

urn:uslm:extraction:42-usc-1983:supreme-court-interpretation:2.0
  -- As interpreted by Supreme Court
  createdPositions: [statutory + confirmed/modified by SCOTUS]
  interpretations: [list of SCOTUS cases]
  authority: BindingPrecedent (nationwide)

urn:uslm:extraction:42-usc-1983:second-circuit-interpretation:2.0
  -- As interpreted by Second Circuit
  createdPositions: [modified by circuit decisions]
  interpretations: [circuit-level cases]
  authority: BindingPrecedent (Second Circuit only)
```

The parsing system must track which interpretation is **currently controlling** by jurisdiction.

```
Class: AuthoritativeInterpretation
  Properties:
    provision: URI [required]
    applicableJurisdiction: URI [required]
      -- Where is this interpretation binding?
    authorityHierarchy: Integer [required]
      -- 1 = SCOTUS, 2 = Circuit, 3 = District, 4 = Non-binding
    controllingDecision: URI [required]
      -- The case that establishes this interpretation
    validAsOf: DateTime [required]
    overriddenBy: URI [optional]
      -- More recent decision that changed the law
    notes: String [optional]
```

---

## Example Extractions

### Example 1: Clean Air Act — EPA Administrator Authority

**Source:** 42 USC § 7401 et seq. (Clean Air Act)

**Statutory Text (simplified):**
```
The Administrator of the Environmental Protection Agency (EPA) is authorized to
establish and enforce national ambient air quality standards. Each state shall
develop a state implementation plan (SIP) to meet these standards within 5 years.
```

**Parsing Model Output (NormativeExtraction):**

```json
{
  "extractionId": "urn:uslm:extraction:42-usc-7401:plaintext:1.0",
  "sourceProvision": "urn:uslm:statute:usc:42/7401",
  "sourceText": "The Administrator of the Environmental Protection Agency (EPA) is authorized to establish and enforce national ambient air quality standards. Each state shall develop a state implementation plan (SIP) to meet these standards within 5 years.",
  "sourceOffsets": {
    "startOffset": 1234,
    "endOffset": 1567
  },
  "extractionDate": "2026-04-02T00:00:00Z",
  "modelVersion": "claude-4.5",
  "confidenceScore": 0.95,

  "normativeStatements": [
    {
      "statementId": "urn:uslm:normative-rule:42-usc-7401:rule-1",
      "statementType": "PrescriptiveStatement",
      "deonticOperator": "Permission",
      "sourceText": "The Administrator is authorized to establish and enforce national ambient air quality standards",
      "targetAgent": "urn:uslm:entity:agent:organization:epa:administrator",
      "ruleStrength": "→",
      "createLegalPositions": [
        "urn:uslm:legal-position:42-usc-7401:power-to-create:epa-admin:public:naaqs:positive"
      ]
    },
    {
      "statementId": "urn:uslm:normative-rule:42-usc-7401:rule-2",
      "statementType": "PrescriptiveStatement",
      "deonticOperator": "Obligation",
      "sourceText": "Each state shall develop a state implementation plan (SIP) to meet these standards within 5 years",
      "targetAgent": "urn:uslm:entity:agent:organization:state:*",
      "ruleStrength": "→",
      "deadline": "P5Y",
      "createLegalPositions": [
        "urn:uslm:legal-position:42-usc-7401:right-duty:public:state:develop-sip:positive"
      ]
    }
  ],

  "createdPositions": [
    {
      "relatorId": "urn:uslm:legal-position:42-usc-7401:power-to-create:epa-admin:public:naaqs:positive",
      "relatorType": "PowerLiabilityRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:organization:epa:administrator",
        "agentType": "GovernmentEntity",
        "agentName": "EPA Administrator",
        "isWildcard": true
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:person:*:*",
        "agentType": "LegalRole",
        "agentName": "any person",
        "isWildcard": true
      },
      "powerType": "PowerToCreate",
      "affectedRelator": "any norm pertaining to air quality standards",
      "sourceProvision": "urn:uslm:statute:usc:42/7401"
    },
    {
      "relatorId": "urn:uslm:legal-position:42-usc-7401:right-duty:public:state:develop-sip:positive",
      "relatorType": "RightDutyRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:organization:public:epa",
        "agentType": "GovernmentEntity",
        "agentName": "EPA (acting as public representative)"
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:organization:state:*",
        "agentType": "GovernmentEntity",
        "agentName": "any state",
        "isWildcard": true
      },
      "rightType": "RightToAction",
      "actionDescriptor": {
        "actionVerb": "enforce",
        "actionObject": "state implementation plan compliance",
        "actionPolarity": "Positive",
        "actionScope": "within jurisdiction"
      },
      "deadline": "P5Y"
    }
  ],

  "domainEntities": [
    {
      "entityId": "urn:uslm:domain:concept:national-ambient-air-quality-standards",
      "entityType": "Activity",
      "label": "National Ambient Air Quality Standards (NAAQS)",
      "description": "Standards established by EPA for air pollution levels"
    },
    {
      "entityId": "urn:uslm:domain:concept:state-implementation-plan",
      "entityType": "Activity",
      "label": "State Implementation Plan (SIP)",
      "description": "A state's plan to achieve and maintain air quality standards"
    }
  ],

  "relatedProvisions": [
    {
      "relatedProvisionUri": "urn:uslm:statute:usc:42/7409",
      "relationshipType": "AppliedBy",
      "description": "Details the NAAQS process"
    }
  ],

  "effectiveDate": "1970-12-31",
  "parsingNotes": "Clean Air Act section; core authority for EPA's role. Multiple amendments have refined this over time. Consider Chevron deference (Chevron U.S.A., Inc. v. Natural Resources Defense Council, 467 U.S. 837, 1984) when evaluating EPA interpretations.",
  "requiresHumanReview": false
}
```

---

### Example 2: 42 USC § 1983 with Multiple Interpretations

**Source:** 42 USC § 1983 (Civil Action for Deprivation of Rights) — with judicial interpretations

**Statutory Text:**
```
Every person who, under color of any statute, ordinance, regulation, custom, or usage, of any State or Territory or the District of Columbia, subjects, or causes to be subjected, any citizen of the United States or any other person within the jurisdiction thereof to the deprivation of any rights, privileges, or immunities secured by the Constitution and laws, shall be liable to the party injured in an action at law, suit in equity, or other proper proceeding for redress.
```

**Parsing Model Output (Plain Text Interpretation):**

```json
{
  "extractionId": "urn:uslm:extraction:42-usc-1983:plaintext:1.0",
  "sourceProvision": "urn:uslm:statute:usc:42/1983",
  "sourceText": "[full statutory text as above]",
  "extractionDate": "2026-04-02T00:00:00Z",
  "modelVersion": "claude-4.5",
  "confidenceScore": 0.88,

  "normativeStatements": [
    {
      "statementId": "urn:uslm:normative-rule:42-usc-1983:rule-1",
      "statementType": "ConstitutiveStatement",
      "definedTerm": "under color of state law",
      "definition": "Acting in official capacity, exercising governmental authority delegated by the state",
      "scope": "For purposes of this section"
    },
    {
      "statementId": "urn:uslm:normative-rule:42-usc-1983:rule-2",
      "statementType": "PrescriptiveStatement",
      "deonticOperator": "Prohibition",
      "sourceText": "Every person who, under color of state law, subjects any citizen to deprivation of rights shall be liable",
      "targetAgent": "urn:uslm:entity:agent:person:state-official:under-color-of-law",
      "ruleStrength": "→",
      "condition": {
        "conditionType": "Conjunction",
        "children": [
          {
            "conditionType": "Simple",
            "simpleStatement": "Agent acts under color of state law"
          },
          {
            "conditionType": "Simple",
            "simpleStatement": "Agent deprives person of constitutional right"
          }
        ]
      },
      "consequence": {
        "conditionType": "Simple",
        "simpleStatement": "Agent is liable in action for redress"
      },
      "createLegalPositions": [
        "urn:uslm:legal-position:42-usc-1983:right-duty:citizen:official:seek-redress:positive"
      ]
    }
  ],

  "createdPositions": [
    {
      "relatorId": "urn:uslm:legal-position:42-usc-1983:right-duty:citizen:official:seek-redress:positive",
      "relatorType": "RightDutyRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:person:citizen:*",
        "agentType": "LegalRole",
        "agentName": "citizen of the United States",
        "isWildcard": true
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:person:state-official:color-of-law",
        "agentType": "LegalRole",
        "agentName": "person acting under color of state law",
        "isWildcard": true
      },
      "rightType": "RightToAction",
      "actionDescriptor": {
        "actionVerb": "bring suit",
        "actionObject": "against state official for constitutional deprivation",
        "actionPolarity": "Positive",
        "actionScope": "in law, equity, or other proper proceeding"
      },
      "sourceProvision": "urn:uslm:statute:usc:42/1983"
    }
  ],

  "domainEntities": [
    {
      "entityId": "urn:uslm:domain:concept:constitutional-right",
      "entityType": "Activity",
      "label": "Constitutional Right",
      "description": "Rights secured by the Constitution (includes individual freedoms, due process, equal protection, etc.)"
    }
  ],

  "ambiguities": [
    {
      "ambiguityId": "urn:uslm:ambiguity:1983:municipal-liability",
      "ambiguityType": "Semantic",
      "ambiguousText": "Every person who ... under color of ... state law",
      "possibleInterpretations": [
        "Only state officials acting in official capacity",
        "Includes municipalities and municipal employees",
        "Includes private persons conspiring with officials"
      ],
      "resolvingAuthority": "urn:uslm:interpretation:case:monell-v-department-1978"
    }
  ],

  "interpretations": [
    {
      "interpretationId": "urn:uslm:interpretation:case:monell-v-department-1978",
      "caseName": "Monell v. Department of Social Services",
      "courtName": "Supreme Court of the United States",
      "courtLevel": "SupremeCourt",
      "decisionDate": "1978-06-06",
      "caseNumber": "No. 76-1495",
      "publicationCitation": "436 U.S. 658",
      "interpretedProvision": "urn:uslm:statute:usc:42/1983",
      "holding": "Municipalities are 'persons' subject to § 1983 liability. However, municipalities cannot be held liable under a theory of respondeat superior (vicarious liability). Liability only attaches when the deprivation is caused by execution of a municipality's policy or custom.",
      "overridesStatutoryText": true,
      "ifSoOverrides": [
        "urn:uslm:normative-rule:42-usc-1983:rule-2"
      ],
      "interpretsAsCreatingPositions": [
        {
          "relatorId": "urn:uslm:legal-position:42-usc-1983:right-duty:citizen:municipality:seek-redress:judicial-interpretation",
          "relatorType": "RightDutyRelator",
          "holderAgent": {
            "agentId": "urn:uslm:entity:agent:person:citizen:*"
          },
          "addresseeAgent": {
            "agentId": "urn:uslm:entity:agent:organization:municipality:*"
          },
          "interpreterDecision": "urn:uslm:interpretation:case:monell-v-department-1978"
        }
      ],
      "authority": "SupremeLawOfLand"
    },
    {
      "interpretationId": "urn:uslm:interpretation:case:bivens-v-six-unknown-agents-1971",
      "caseName": "Bivens v. Six Unknown Federal Narcotics Agents",
      "courtName": "Supreme Court of the United States",
      "courtLevel": "SupremeCourt",
      "decisionDate": "1971-06-04",
      "caseNumber": "No. 70-1736",
      "publicationCitation": "403 U.S. 388",
      "interpretedProvision": "urn:uslm:statute:usc:42/1983",
      "holding": "Although § 1983 applies only to state officials, the Constitution implies a private right of action against federal officers for violations of the Fourth Amendment and other constitutional rights.",
      "overridesStatutoryText": false,
      "authority": "SupremeLawOfLand"
    }
  ],

  "currentValidInterpretation": "urn:uslm:extraction:42-usc-1983:supreme-court-interpretation:2.0",
  "parsingNotes": "This is one of the most litigated statutes in US law. The plain text appears to apply only to state officials, but Supreme Court has extended it to municipalities (Monell), recognized implied damages suits against federal officers (Bivens), and created various exceptions. Multiple circuit splits exist on specific questions (e.g., scope of qualified immunity, municipal policy requirements). This extraction focuses on the core holding. Consider jurisdictional factors when applying.",
  "requiresHumanReview": false
}
```

**Parsing Model Output (Supreme Court Interpretation):**

```json
{
  "extractionId": "urn:uslm:extraction:42-usc-1983:supreme-court-interpretation:2.0",
  "sourceProvision": "urn:uslm:statute:usc:42/1983",
  "sourceText": "[statutory text as above]",
  "extractionDate": "2026-04-02T00:00:00Z",
  "modelVersion": "claude-4.5",
  "confidenceScore": 0.92,

  "normativeStatements": [
    {
      "statementId": "urn:uslm:normative-rule:42-usc-1983:rule-2-monell-interpretation",
      "statementType": "PrescriptiveStatement",
      "deonticOperator": "Obligation",
      "sourceText": "Municipal liability under § 1983 requires proof of official policy or custom",
      "targetAgent": "urn:uslm:entity:agent:organization:municipality:*",
      "ruleStrength": "→",
      "condition": {
        "conditionType": "Conjunction",
        "children": [
          {
            "conditionType": "Simple",
            "simpleStatement": "Deprivation caused by execution of municipality's policy or custom"
          }
        ]
      },
      "consequence": {
        "conditionType": "Simple",
        "simpleStatement": "Municipality is liable; employee is not automatically liable"
      },
      "exceptions": [
        {
          "conditionType": "Simple",
          "simpleStatement": "Employee sued in individual capacity for personal conduct outside scope of employment"
        }
      ]
    }
  ],

  "createdPositions": [
    {
      "relatorId": "urn:uslm:legal-position:42-usc-1983:right-duty:citizen:official:seek-redress:positive",
      "relatorType": "RightDutyRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:person:citizen:*"
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:person:state-official:color-of-law"
      },
      "rightType": "RightToAction",
      "sourceProvision": "urn:uslm:statute:usc:42/1983",
      "defeasibilityStatus": "Defeasible",
      "notes": "Can be overcome by qualified immunity"
    },
    {
      "relatorId": "urn:uslm:legal-position:42-usc-1983:right-duty:citizen:municipality:seek-redress:judicial-interpretation",
      "relatorType": "RightDutyRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:person:citizen:*"
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:organization:municipality:*"
      },
      "rightType": "RightToAction",
      "actionDescriptor": {
        "actionVerb": "sue",
        "actionObject": "municipality for constitutional deprivation",
        "actionScope": "only if deprivation caused by official policy or custom"
      },
      "sourceProvision": "urn:uslm:statute:usc:42/1983",
      "interpreterDecision": "urn:uslm:interpretation:case:monell-v-department-1978"
    },
    {
      "relatorId": "urn:uslm:legal-position:42-usc-1983:disability-immunity:municipality-employee:policy-requirement",
      "relatorType": "DisabilityImmunityRelator",
      "holderAgent": {
        "agentId": "urn:uslm:entity:agent:person:municipal-employee:*"
      },
      "addresseeAgent": {
        "agentId": "urn:uslm:entity:agent:organization:municipality:*"
      },
      "immunityType": "Vicarious Liability Immunity",
      "disabilityType": "Disability to Impose Vicarious Liability",
      "scope": "Municipality cannot be liable for employee misconduct unless caused by official policy or custom",
      "exceptions": [
        {
          "conditionType": "Simple",
          "simpleStatement": "Policy or custom of municipality caused the deprivation"
        }
      ],
      "sourceProvision": "urn:uslm:statute:usc:42/1983",
      "interpreterDecision": "urn:uslm:interpretation:case:monell-v-department-1978"
    }
  ],

  "interpretations": [
    {
      "interpretationId": "urn:uslm:interpretation:case:monell-v-department-1978",
      "caseName": "Monell v. Department of Social Services",
      "courtName": "Supreme Court of the United States",
      "decisionDate": "1978-06-06",
      "holding": "Municipalities are 'persons' under § 1983 but liable only for official policy or custom"
    }
  ],

  "currentValidInterpretation": "urn:uslm:extraction:42-usc-1983:supreme-court-interpretation:2.0",
  "parsingNotes": "This represents the law as clarified by Supreme Court. Further circuit splits on specific applications remain unresolved (e.g., Monell causation standard). Model treated plain statutory text as defeasible and updated per Monell and related holdings.",
  "requiresHumanReview": false
}
```

---

## Annotation Guidelines for Parsing Models

This section provides explicit instructions for how a parsing model should use this ontology when extracting statutory content.

### Step 1: Parse and Identify Provision Boundaries

When reading a statute:

1. Identify the provision boundaries (section, subsection, paragraph).
2. Extract the exact source text.
3. Record the document hierarchy (Title > Chapter > Section > Subsection).
4. Capture offsets for traceability.

**Output:** DocumentNode with sourceText and OffsetRange.

### Step 2: Recognize Constitutive (Definitional) Statements

Many statutes define key terms. Recognize patterns:

```
"For purposes of this section, _____ means _____"
"The term '______' includes ____"
"'______' shall be defined as ____"
"___ is defined to mean ___"
```

**Action:** Create ConstitutiveStatement object. Extract the defined term and definition. Link to domain ontology if applicable.

### Step 3: Identify Prescriptive Rules (Obligations, Prohibitions, Permissions)

Statutory commands use specific linguistic patterns:

**Obligation:**
```
"shall _____" (mandatory)
"must _____"
"is required to _____"
"is obligated to _____"
```

**Prohibition:**
```
"shall not _____"
"must not _____"
"is prohibited from _____"
"no _____ may _____"
```

**Permission:**
```
"may _____"
"is authorized to _____"
"has the right to _____"
"is permitted to _____"
"has authority to _____"
```

**Action:**
1. Extract the deontic operator (Obligation, Prohibition, or Permission).
2. Identify the agent to whom the rule is directed (targetAgent).
3. Extract the action being prescribed (actionDescriptor).
4. Identify any conditions (if any), deadlines, and exceptions.
5. Create a PrescriptiveStatement object.
6. Determine what legal relators this creates:
   - Obligation → RightDutyRelator (creditor has right, debtor has duty)
   - Prohibition → RightDutyRelator with DutyToOmit
   - Permission → NoRightPermissionRelator

### Step 4: Resolve Agent References

Statutes often use multiple ways to refer to the same agent. When you see:

- "the Secretary" — resolve to canonical agent (e.g., Secretary of Labor, if in Labor chapter)
- "any person" — mark as wildcard = true
- "a federal officer" — mark as LegalRole
- "the EPA" — map to urn:uslm:entity:agent:organization:epa

**Action:**
1. Collect all agent references.
2. Resolve aliases to canonical agents.
3. Create LegalAgent objects with agentId, agentType, aliases, isWildcard.

### Step 5: Identify Conditions and Consequences

Prescriptive rules have the structure: **IF condition THEN consequence.**

Conditions use words:
```
"if _____" or "when _____" or "upon _____" or "where _____" or "in case _____"
```

Consequences describe what action must be taken or what state must result.

**Action:**
1. Extract condition as LogicalCondition.
2. Extract consequence as LogicalCondition.
3. If conditions involve temporal elements (deadlines, durations), extract as DateTime or Duration.

### Step 6: Identify Penalties and Consequences of Violation

Penalties create new legal positions (rights to sue, duties to pay damages, etc.).

Patterns:
```
"shall be liable _____"
"shall be subject to _____"
"may be fined _____"
"shall be imprisoned _____"
"shall pay damages _____"
"is subject to civil action _____"
"shall be injunction _____"
```

**Action:**
1. Create PenaltyStatement linked to the violated obligation.
2. Identify the penalty type (Civil, Criminal, Administrative, etc.).
3. Identify what legal positions the penalty creates:
   - "liable in action for damages" → creates Right-Duty relator (plaintiff has right to sue, defendant has duty to pay)
   - "injunction" → creates Power-Liability relator (court/plaintiff has power to compel, defendant has liability)

### Step 7: Map to Domain Ontology

Statutes regulate real-world things. Identify what domain entities this provision concerns:

- Persons: employees, employers, citizens, officers
- Organizations: agencies, corporations, unions
- Places: states, counties, jurisdictions
- Activities: employment, commerce, transportation
- Objects: property, goods, weapons
- Substances: chemicals, drugs, hazardous materials
- Events: accidents, violations, approvals
- Situations: emergency, bankruptcy, employment

**Action:**
1. For each real-world concept mentioned, create or reference a DomainEntity.
2. If the statute defines the concept, link to ConstitutiveStatement.

### Step 8: Identify Overrides and Related Provisions

Provisions interact through override relations and cross-references.

Patterns:
```
"Except that _____" → exception clause (override)
"Notwithstanding _____" → explicit override
"Subject to _____" → constraint/subordination
"See also ______" → related provision
"Incorporating by reference ______" → incorporation
```

**Action:**
1. Extract all cross-references (CitationReference objects).
2. Identify override relationships (OverridingRule objects).
3. Note defeasibility: is this rule strict, defeasible, or a defeater?

### Step 9: Check for Judicial Interpretations

Research whether courts have interpreted this provision:

- Supreme Court holdings → authority = SupremeLawOfLand
- Circuit Court holdings → authority = BindingPrecedent (circuit-specific)
- District Court holdings → authority = PersuasivePrecedent

**Action:**
1. If you have access to case law, create JudicialInterpretation objects.
2. Note whether the judicial interpretation overrides the plain text (overridesStatutoryText).
3. Link judicial interpretations to the positions they create/modify.

### Step 10: Assemble the Complete NormativeExtraction

Combine all the above into a single NormativeExtraction object:

```
NormativeExtraction {
  sourceProvision: [URI of statute]
  sourceText: [exact text]
  sourceOffsets: [character range]

  normativeStatements: [all ConstitutiveStatement, PrescriptiveStatement, PenaltyStatement]
  createdPositions: [all LegalRelator objects]
  domainEntities: [all DomainEntity objects]

  interpretations: [all JudicialInterpretation objects, if any]
  currentValidInterpretation: [most authoritative interpretation]

  effectiveDate: [when does this provision take effect?]
  expirationDate: [if temporary]

  ambiguities: [any ambiguous passages]
  parsingNotes: [notes for human reviewers]
  requiresHumanReview: [true if complex or uncertain]
  confidenceScore: [0.0-1.0]
}
```

### Step 11: Confidence Scoring

Assign a confidenceScore based on:

| Scenario | Score |
|----------|-------|
| Plain statute, no ambiguity, no contrary case law | 0.95-1.0 |
| Plain statute with minor ambiguities | 0.85-0.94 |
| Statute with some ambiguity; courts agree | 0.75-0.84 |
| Statute with multiple interpretations, slight circuit split | 0.65-0.74 |
| Statute with significant judicial disagreement | 0.50-0.64 |
| Statute extremely ambiguous or conflicting | <0.50 |

### Step 12: Flag for Human Review

Set `requiresHumanReview = true` if:

- Confidence score < 0.70
- Provision has been changed by amendment recently
- Judicial interpretation conflicts with plain text
- Multiple circuit splits exist
- Provision language is archaic or ambiguous
- Domain entity mapping is uncertain

---

## Summary: How the Layers Fit Together

When a parser reads a statute:

1. **Layer 4 (Document)** provides structure: where in the code hierarchy is this provision?
2. **Layer 3 (Domain)** provides meaning: what real-world things does it regulate?
3. **Layer 2 (Rules)** provides logic: what commands (obligations, prohibitions, permissions) does it impose?
4. **Layer 1 (Positions)** provides legal semantics: what correlative legal positions does it create?

All four are unified in a **NormativeExtraction** object that serves as the output.

Parsing flow:

```
Statutory Text
    ↓ (identify structure)
DocumentNode (where am I in the hierarchy?)
    ↓ (recognize rules)
NormativeStatement (what is being prescribed/defined/penalized?)
    ↓ (map to positions)
LegalRelator (what Hohfeldian positions are created?)
    ↓ (identify referents)
DomainEntity (what real-world things are involved?)
    ↓ (assemble)
NormativeExtraction (complete structured representation)
    ↓
Knowledge Graph (stored, queryable, reasoned over)
```

Interpretation handling:

```
Statutory Text
    ↓
Plain Text NormativeExtraction (v1.0)
    ↓ (discover case law)
Court Decision
    ↓
Modified NormativeExtraction (v2.0, with JudicialInterpretation)
    ↓ (if conflicting decisions)
Multiple NormativeExtraction versions, with authorityLevel tracking
```

---

## Implementation Notes for Downstream Systems

### For Knowledge Graph Storage

Store each NormativeExtraction as a node in a graph database:

```
Node: NormativeExtraction
  Properties: extractionId, sourceProvision, confidenceScore, ...
  Edges:
    CONTAINS_STATEMENT -> NormativeStatement
    CREATES_POSITION -> LegalRelator
    CONCERNS_ENTITY -> DomainEntity
    INTERPRETED_BY -> JudicialInterpretation
    OVERRIDDEN_BY -> NormativeExtraction (if superseded by later interpretation)
    OVERRIDES -> NormativeExtraction (if this overrides another)
```

### For Querying

Users should be able to ask:
- "What are all legal positions created by 42 USC § 1983?" → Traverse CREATES_POSITION edges
- "What is the controlling interpretation of § 1983 in the Second Circuit?" → Find NormativeExtraction with authority=BindingPrecedent, jurisdiction=SecondCircuit
- "What obligations apply to federal agencies?" → Find PrescriptiveStatement with deonticOperator=Obligation, targetAgent=GovernmentEntity
- "How has the definition of 'person' under § 1983 changed?" → Track all ConstitutiveStatement objects with definedTerm='person', ordered by effectiveDate

### For Reasoning

A rule engine should be able to:
- Apply override relations (lex specialis, lex posterior, defeasibility)
- Resolve conflicting provisions (OverridingRule objects tell you which provision wins)
- Track legal positions through their lifecycle (created → active → suspended → extinguished)
- Apply conditions and temporal constraints
- Distinguish statutory text from judicial interpretation

---

## Final Notes

This schema is designed to be:

1. **Complete**: Every statutory provision can be represented.
2. **Precise**: The ontology captures legal semantics faithfully.
3. **Computable**: A parser can automatically extract NormativeExtraction objects.
4. **Scalable**: The modular domain ontology allows for unlimited domain-specific extensions.
5. **Auditable**: Every position, rule, and interpretation is traceable to source text (via OffsetRange) and authority (via JudicialInterpretation).
6. **Interpretable**: The structure is sufficiently fine-grained that an LLM or rule engine can reason over it.

The schema is intentionally not serialized to any specific format (JSON, RDF, XML) in this document, as it is intended as a conceptual specification. Implementations may serialize it in JSON-LD (for Semantic Web integration), RDF (for standard ontology tools), custom JSON (for databases), or any other format — but the underlying structure remains constant.

The most important invariant is the **Hohfeldian correlative structure**: every legal position must have a correlative counterpart in another agent. This ensures that the ontology cannot represent incoherent legal states.

