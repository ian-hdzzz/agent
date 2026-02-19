# Implementation Gaps Analysis
# Gobierno de Queretaro AI Communication Platform

**Document Version:** 1.0
**Date:** 2026-02-04
**Status:** Wave 4 Synthesis
**Average Domain Completeness:** 6.04/10

---

## Executive Summary

This document identifies all remaining gaps that must be resolved before implementation can begin. Based on Wave 1 analysis of 13 domains (average completeness 6/10), we have categorized gaps by type, prioritized by implementation phase, and provided resolution strategies.

### Gap Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| API Integration | 14 | 9 | 6 | 3 | 32 |
| Data Schema | 8 | 12 | 7 | 4 | 31 |
| Business Logic | 6 | 11 | 9 | 5 | 31 |
| External Dependencies | 5 | 8 | 4 | 2 | 19 |
| **Total** | **33** | **40** | **26** | **14** | **113** |

### Key Blockers

1. **Portal Tributario API Access** - No documented API, blocks Phase 2 high-volume services
2. **QROBUS API Authentication** - Undocumented authentication mechanism
3. **SAID System Integration** - Critical for February enrollment (TIME-SENSITIVE)
4. **Payment Gateway Contracts** - Legal/procurement not initiated
5. **Crisis Protocol Approval** - Safety-critical protocols need government sign-off

---

## 1. API Integration Gaps

### 1.1 Phase 1 Blockers (Must Resolve Before Development)

#### GAP-API-001: CURP Validation Service (RENAPO)
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | No documented API access |
| **Required** | Federal RENAPO API credentials and rate limits |
| **Resolution Strategy** | External research - Government IT coordination |
| **Owner** | Government IT Liaison |
| **Effort** | 2-4 weeks (procurement/legal) |
| **Dependency** | None |

#### GAP-API-002: Chatwoot Integration Extensions
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Basic integration exists in MARIA |
| **Required** | Custom fields for domain-specific context, crisis flags |
| **Resolution Strategy** | Internal - Extend existing Chatwoot implementation |
| **Owner** | Development Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-API-003: Notification Service Selection
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Twilio/OneSignal mentioned but not decided |
| **Required** | WhatsApp Business API template approval process |
| **Resolution Strategy** | Internal decision + Meta Business verification |
| **Owner** | Product Manager |
| **Effort** | 2-3 weeks |
| **Dependency** | None |

---

### 1.2 Phase 2 Critical (High-Volume Services)

#### GAP-API-004: Portal Tributario API (Vehiculos)
| Attribute | Value |
|-----------|-------|
| **Domain** | 05-Tramites Vehiculares (Priority 1) |
| **Current State** | No documented API; web scraping not viable |
| **Required Endpoints** | |
| | `GET /vehicles/{plate}/debt` |
| | `POST /vehicles/{plate}/payment-reference` |
| | `GET /vehicles/{plate}/receipt/{folio}` |
| | `GET /vehicles/{plate}/verification-status` |
| **Resolution Strategy** | External research - Contact Secretaria de Finanzas IT |
| **Owner** | Government IT Liaison |
| **Effort** | 4-6 weeks |
| **Dependency** | GAP-EXT-001 (Government IT Access) |
| **Fallback** | Deep links to existing web portal |

#### GAP-API-005: QROBUS System API (Transporte)
| Attribute | Value |
|-----------|-------|
| **Domain** | 02-Transporte AMEQ (Priority 2) |
| **Current State** | Mobile app exists but no public API |
| **Required Endpoints** | |
| | `GET /cards/{card_number}/balance` |
| | `GET /cards/{card_number}/history` |
| | `POST /cards/{card_number}/block` |
| | `GET /routes/search?from={loc}&to={loc}` |
| **Resolution Strategy** | External research - Contact AMEQ/IQT IT department |
| **Owner** | Government IT Liaison |
| **Effort** | 4-6 weeks |
| **Dependency** | GAP-EXT-002 (IQT Coordination) |
| **Fallback** | Redirect to QROBUS app with deep links |

#### GAP-API-006: CEA SOAP API Extensions
| Attribute | Value |
|-----------|-------|
| **Domain** | 03-Agua CEA (Priority 3) |
| **Current State** | Basic SOAP API functional in MARIA |
| **Required Extensions** | |
| | Geolocation-enhanced leak reporting |
| | Payment link generation endpoint |
| | Proactive consumption alerts webhook |
| **Resolution Strategy** | Internal + External - Extend existing integration |
| **Owner** | Development Team + CEA IT |
| **Effort** | 2-3 weeks |
| **Dependency** | None (existing API works) |

#### GAP-API-007: SAID System API (Educacion)
| Attribute | Value |
|-----------|-------|
| **Domain** | 04-Educacion USEBEQ (Priority 4) |
| **Current State** | CURP lookup exists but limited |
| **Required Endpoints** | |
| | `GET /enrollment/{curp}/vinculacion-status` |
| | `GET /enrollment/{curp}/preasignacion` |
| | `GET /schools/search?location={coords}` |
| | `GET /schools/{cct}/capacity` |
| **Resolution Strategy** | External research - Contact USEBEQ IT |
| **Owner** | Government IT Liaison |
| **Effort** | 3-4 weeks |
| **Dependency** | GAP-EXT-003 (USEBEQ Coordination) |
| **Time-Critical** | YES - February 3-13 enrollment period |

---

### 1.3 Phase 3-4 Dependencies

#### GAP-API-008: CERLIN/SIRE API (Registro Publico)
| Attribute | Value |
|-----------|-------|
| **Domain** | 09-Registro Publico RPP (Priority 5) |
| **Current State** | No API documentation |
| **Required Endpoints** | |
| | `GET /properties/search` (by folio, catastral, address) |
| | `GET /certificates/{id}/status` |
| | `POST /certificates/request` |
| | `POST /alerts/register` |
| **Resolution Strategy** | External research - Contact RPP IT |
| **Owner** | Government IT Liaison |
| **Effort** | 4-6 weeks |
| **Dependency** | None |

#### GAP-API-009: CENCOLAB API (Conciliacion Laboral)
| Attribute | Value |
|-----------|-------|
| **Domain** | 10-Conciliacion Laboral CCLQ (Priority 8) |
| **Current State** | Web portal only, no documented API |
| **Required Endpoints** | |
| | `POST /cases` |
| | `GET /cases/{id}/status` |
| | `POST /appointments` |
| | `GET /appointments/availability` |
| **Resolution Strategy** | External research - Contact CCLQ IT |
| **Owner** | Government IT Liaison |
| **Effort** | 4-6 weeks |
| **Dependency** | None |

#### GAP-API-010: IVEQ Case Management (Vivienda)
| Attribute | Value |
|-----------|-------|
| **Domain** | 11-Vivienda IVEQ (Priority 7) |
| **Current State** | Appointment system exists (citas.iveq.gob.mx) |
| **Required Endpoints** | |
| | `GET /properties/{id}/debt-status` |
| | `POST /appointments` |
| | `GET /programs/eligibility` |
| | `GET /applications/{id}/status` |
| **Resolution Strategy** | External research - Contact IVEQ IT |
| **Owner** | Government IT Liaison |
| **Effort** | 3-4 weeks |
| **Dependency** | None |

#### GAP-API-011: Tarjeta Contigo API (SEDESOQ)
| Attribute | Value |
|-----------|-------|
| **Domain** | 13-SEDESOQ (Priority 9) |
| **Current State** | WhatsApp line exists but no API |
| **Required Endpoints** | |
| | `GET /cards/{id}/balance` |
| | `GET /cards/{id}/transactions` |
| | `GET /beneficiaries/{curp}/programs` |
| | `GET /programs/eligibility` |
| **Resolution Strategy** | External research - Contact SEDESOQ IT |
| **Owner** | Government IT Liaison |
| **Effort** | 4-6 weeks |
| **Dependency** | None |

#### GAP-API-012: IQM Case Management (Mujeres)
| Attribute | Value |
|-----------|-------|
| **Domain** | 07-Mujeres IQM (Priority 10) |
| **Current State** | No digital case management API |
| **Required Endpoints** | |
| | `POST /cases/crisis` (immediate) |
| | `POST /appointments` |
| | `GET /shelters/availability` (RESTRICTED) |
| **Resolution Strategy** | External research + Security review |
| **Owner** | Government IT Liaison + Security |
| **Effort** | 6-8 weeks (includes security audit) |
| **Dependency** | GAP-SEC-001 (Privacy Framework) |
| **CRITICAL** | Shelter locations NEVER stored client-side |

#### GAP-API-013: SEJUVE Appointment System (Psicologia)
| Attribute | Value |
|-----------|-------|
| **Domain** | 06-Psicologia SEJUVE (Priority 11) |
| **Current State** | No API documentation |
| **Required Endpoints** | |
| | `GET /appointments/availability` |
| | `POST /appointments` |
| | `POST /crisis/alert` (to staff) |
| **Resolution Strategy** | External research - Contact SEJUVE IT |
| **Owner** | Government IT Liaison |
| **Effort** | 3-4 weeks |
| **Dependency** | GAP-BL-015 (Crisis Protocol Approval) |

#### GAP-API-014: Event Calendar API (Cultura)
| Attribute | Value |
|-----------|-------|
| **Domain** | 08-Cultura (Priority 12) |
| **Current State** | External website only |
| **Required Endpoints** | |
| | `GET /events/search` |
| | `GET /events/{id}` |
| | `GET /venues/{id}` |
| | `POST /workshops/{id}/enroll` |
| **Resolution Strategy** | External research - Contact Cultura IT |
| **Owner** | Government IT Liaison |
| **Effort** | 2-3 weeks |
| **Dependency** | None |

---

## 2. Data Schema Gaps

### 2.1 Phase 1 Blockers

#### GAP-DS-001: Unified Citizen Profile Schema
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | No unified schema defined |
| **Required Fields** | |
| | `curp` (primary key) |
| | `linked_services[]` |
| | `contact_preferences` |
| | `language` |
| | `accessibility_needs` |
| | `consent_history[]` |
| **Resolution Strategy** | Internal - Define schema with privacy team |
| **Owner** | Data Architect |
| **Effort** | 1-2 weeks |
| **Dependency** | GAP-SEC-002 (Data Governance) |

#### GAP-DS-002: Conversation Context Schema
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Basic context in MARIA |
| **Required Extensions** | |
| | Cross-domain context transfer |
| | Emotional state tracking |
| | Crisis indicators |
| | Handoff context package |
| **Resolution Strategy** | Internal - Extend MARIA context |
| **Owner** | Development Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-DS-003: Error Response Schema
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Defined in ERROR_HANDLING_FRAMEWORK.md |
| **Gap** | Spanish error messages not finalized |
| **Resolution Strategy** | Internal - Content team review |
| **Owner** | Content Team |
| **Effort** | 3-5 days |
| **Dependency** | None |

---

### 2.2 Domain-Specific Schemas

#### GAP-DS-004: Vehicle Debt Response Schema
| Attribute | Value |
|-----------|-------|
| **Domain** | 05-Tramites Vehiculares |
| **Required Fields** | |
| | `plate_number` |
| | `tenencia_amount` |
| | `verification_status` |
| | `discount_available` |
| | `discount_deadline` |
| | `infractions[]` |
| **Resolution Strategy** | Prototype-based discovery |
| **Owner** | Development Team |
| **Effort** | Depends on GAP-API-004 |
| **Dependency** | GAP-API-004 |

#### GAP-DS-005: Enrollment Status Schema (SAID)
| Attribute | Value |
|-----------|-------|
| **Domain** | 04-Educacion USEBEQ |
| **Required Fields** | |
| | `curp_aspirante` |
| | `vinculacion_status` |
| | `preasignacion` |
| | `school_assigned` |
| | `enrollment_period` |
| | `documents_status[]` |
| **Resolution Strategy** | Prototype-based discovery |
| **Owner** | Development Team |
| **Effort** | Depends on GAP-API-007 |
| **Dependency** | GAP-API-007 |

#### GAP-DS-006: Certificate Types Schema (RPP)
| Attribute | Value |
|-----------|-------|
| **Domain** | 09-Registro Publico |
| **Current State** | 8 types documented but schema undefined |
| **Required** | Decision tree mapping + cost calculations |
| **Resolution Strategy** | Internal - Extract from existing docs |
| **Owner** | Content Team |
| **Effort** | 3-5 days |
| **Dependency** | None |

#### GAP-DS-007: Labor Rights Calculator Schema
| Attribute | Value |
|-----------|-------|
| **Domain** | 10-Conciliacion Laboral |
| **Required Fields** | |
| | `termination_date` |
| | `years_employed` |
| | `daily_integrated_salary` |
| | `indemnizacion_3meses` |
| | `20_dias_por_ano` |
| | `aguinaldo_proporcional` |
| | `prima_antiguedad` |
| | `deadline_days_remaining` |
| **Resolution Strategy** | Internal - LFT Article extraction |
| **Owner** | Legal/Content Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-DS-008: Crisis Assessment Schema
| Attribute | Value |
|-----------|-------|
| **Domains** | 06-Psicologia, 07-Mujeres, 10-Laboral, 13-SEDESOQ |
| **Required Fields** | |
| | `alert_level` (RED/ORANGE/YELLOW) |
| | `keywords_detected[]` |
| | `risk_indicators[]` |
| | `immediate_action` |
| | `escalation_target` |
| | `timestamp` |
| **Resolution Strategy** | Internal - Extract from SENSITIVE_SERVICES_BEST_PRACTICES.md |
| **Owner** | Safety Team |
| **Effort** | 3-5 days |
| **Dependency** | GAP-BL-015 (Crisis Protocol Approval) |

---

## 3. Business Logic Gaps

### 3.1 Phase 1 Blockers

#### GAP-BL-001: Intent Classification Thresholds
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Threshold of 0.85/0.60 mentioned but not validated |
| **Required** | Validated confidence thresholds per domain |
| **Resolution Strategy** | Prototype-based discovery with test data |
| **Owner** | AI/ML Team |
| **Effort** | 2-3 weeks (after deployment) |
| **Dependency** | Initial deployment |

#### GAP-BL-002: Human Handoff Triggers
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | General triggers defined |
| **Required** | Domain-specific trigger matrix with SLAs |
| **Resolution Strategy** | Internal - Consolidate from domain analyses |
| **Owner** | Product Manager |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-BL-003: Queue Priority Rules
| Attribute | Value |
|-----------|-------|
| **Domains Affected** | ALL 13 domains |
| **Current State** | Crisis bypass mentioned but not formalized |
| **Required** | Priority levels, bypass rules, SLAs per level |
| **Resolution Strategy** | Internal decision |
| **Owner** | Operations Lead |
| **Effort** | 3-5 days |
| **Dependency** | None |

---

### 3.2 Domain-Specific Business Logic

#### GAP-BL-004: Tenencia Discount Calculation
| Attribute | Value |
|-----------|-------|
| **Domain** | 05-Tramites Vehiculares |
| **Current State** | January 10%, February 5% documented |
| **Gap** | Exemption rules (disabled, seniors, hybrids) not codified |
| **Resolution Strategy** | External research - Secretaria de Finanzas |
| **Owner** | Content Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-BL-005: Verification Calendar Logic
| Attribute | Value |
|-----------|-------|
| **Domain** | 05-Tramites Vehiculares |
| **Current State** | Plate ending -> Month mapping exists |
| **Gap** | Edge cases (new vehicles, transfers, exemptions) |
| **Resolution Strategy** | Internal - Extract from Secretaria documentation |
| **Owner** | Content Team |
| **Effort** | 3-5 days |
| **Dependency** | None |

#### GAP-BL-006: School Enrollment Age Rules
| Attribute | Value |
|-----------|-------|
| **Domain** | 04-Educacion USEBEQ |
| **Current State** | Basic age ranges known |
| **Gap** | Cutoff dates, exceptions, USAER eligibility |
| **Resolution Strategy** | External research - USEBEQ |
| **Owner** | Content Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-BL-007: Water Payment Plan Eligibility
| Attribute | Value |
|-----------|-------|
| **Domain** | 03-Agua CEA |
| **Current State** | CVN category exists but rules unclear |
| **Gap** | Eligibility criteria for seniors, disabled, pensioners |
| **Resolution Strategy** | External research - CEA |
| **Owner** | Content Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-BL-008: Housing Program Eligibility Matrix
| Attribute | Value |
|-----------|-------|
| **Domain** | 11-Vivienda IVEQ |
| **Current State** | 3 programs listed |
| **Gap** | Income ranges, employment requirements, property restrictions |
| **Resolution Strategy** | External research - IVEQ |
| **Owner** | Content Team |
| **Effort** | 1-2 weeks |
| **Dependency** | None |

#### GAP-BL-009: Social Program Eligibility Rules
| Attribute | Value |
|-----------|-------|
| **Domain** | 13-SEDESOQ |
| **Current State** | Only Tarjeta Contigo visible |
| **Gap** | 10+ programs need eligibility rules documented |
| **Resolution Strategy** | External research - SEDESOQ |
| **Owner** | Content Team |
| **Effort** | 2-3 weeks |
| **Dependency** | None |

#### GAP-BL-010: Labor Deadline Calculator
| Attribute | Value |
|-----------|-------|
| **Domain** | 10-Conciliacion Laboral |
| **Current State** | 60-day rule documented |
| **Gap** | Calendar vs business days, holiday handling, suspension rules |
| **Resolution Strategy** | Internal - LFT Article 518 interpretation |
| **Owner** | Legal Team |
| **Effort** | 1 week |
| **Dependency** | None |

#### GAP-BL-011: Certificate Selection Logic (RPP)
| Attribute | Value |
|-----------|-------|
| **Domain** | 09-Registro Publico |
| **Current State** | Decision tree outlined in analysis |
| **Gap** | Complete mapping of use cases to certificate types |
| **Resolution Strategy** | Internal - Formalize decision tree |
| **Owner** | Content Team |
| **Effort** | 1 week |
| **Dependency** | None |

---

### 3.3 Safety-Critical Business Logic

#### GAP-BL-012: Crisis Detection Keywords (Spanish)
| Attribute | Value |
|-----------|-------|
| **Domains** | 06-Psicologia, 07-Mujeres, 10-Laboral, 13-SEDESOQ |
| **Current State** | Lists in SENSITIVE_SERVICES_BEST_PRACTICES.md |
| **Gap** | Not validated with mental health professionals |
| **Resolution Strategy** | External validation - Clinical psychologist review |
| **Owner** | Safety Team |
| **Effort** | 2-3 weeks |
| **Dependency** | None |
| **CRITICAL** | Must be 99%+ accurate |

#### GAP-BL-013: Danger Assessment Protocol (IQM)
| Attribute | Value |
|-----------|-------|
| **Domain** | 07-Mujeres IQM |
| **Current State** | 4-level system outlined |
| **Gap** | Response timing, escalation thresholds, staff allocation |
| **Resolution Strategy** | External validation - IQM specialists |
| **Owner** | Safety Team + IQM |
| **Effort** | 3-4 weeks |
| **Dependency** | GAP-EXT-005 (IQM Coordination) |
| **CRITICAL** | Safety above efficiency |

#### GAP-BL-014: Code Word System Implementation
| Attribute | Value |
|-----------|-------|
| **Domain** | 07-Mujeres IQM |
| **Current State** | Words suggested (pizza, llueve, farmacia) |
| **Gap** | Technical implementation, staff training, testing |
| **Resolution Strategy** | Internal + External |
| **Owner** | Development + IQM |
| **Effort** | 2-3 weeks |
| **Dependency** | None |

#### GAP-BL-015: Crisis Protocol Approval
| Attribute | Value |
|-----------|-------|
| **Domains** | 06-Psicologia, 07-Mujeres |
| **Current State** | Protocols drafted |
| **Gap** | Government approval, legal review, liability framework |
| **Resolution Strategy** | External - Government legal/policy team |
| **Owner** | Project Sponsor |
| **Effort** | 4-6 weeks |
| **Dependency** | None |
| **BLOCKER** | Cannot deploy sensitive services without approval |

---

## 4. External Dependency Gaps

### 4.1 Government IT Coordination

#### GAP-EXT-001: Secretaria de Finanzas IT Access
| Attribute | Value |
|-----------|-------|
| **Required For** | Portal Tributario API (Vehicles) |
| **Current State** | No contact established |
| **Action** | Schedule meeting with IT director |
| **Owner** | Government IT Liaison |
| **Effort** | 2 weeks to establish contact |
| **Risk** | API may not exist; may need to build |

#### GAP-EXT-002: IQT/AMEQ IT Coordination
| Attribute | Value |
|-----------|-------|
| **Required For** | QROBUS API, GTFS data |
| **Current State** | No contact established |
| **Action** | Schedule meeting with AMEQ IT |
| **Owner** | Government IT Liaison |
| **Effort** | 2 weeks to establish contact |
| **Risk** | May require formal data sharing agreement |

#### GAP-EXT-003: USEBEQ IT Coordination
| Attribute | Value |
|-----------|-------|
| **Required For** | SAID System API |
| **Current State** | No contact established |
| **Action** | URGENT - Schedule meeting before February enrollment |
| **Owner** | Government IT Liaison |
| **Effort** | 1 week (URGENT) |
| **Risk** | System may be frozen during enrollment period |
| **TIME-CRITICAL** | Must resolve before February 3 |

#### GAP-EXT-004: RPP IT Coordination
| Attribute | Value |
|-----------|-------|
| **Required For** | CERLIN/SIRE API |
| **Current State** | No contact established |
| **Action** | Schedule meeting with RPP IT |
| **Owner** | Government IT Liaison |
| **Effort** | 2 weeks |
| **Risk** | Legacy systems may have limited API capability |

#### GAP-EXT-005: IQM Coordination
| Attribute | Value |
|-----------|-------|
| **Required For** | Crisis protocols, case management |
| **Current State** | No contact established |
| **Action** | Schedule meeting with IQM director |
| **Owner** | Government IT Liaison + Safety Team |
| **Effort** | 2-3 weeks |
| **Risk** | Sensitive service; requires executive sponsorship |

---

### 4.2 Third-Party Services

#### GAP-EXT-006: Payment Gateway Contract
| Attribute | Value |
|-----------|-------|
| **Required For** | Vehicles, Water, Culture, RPP, Housing |
| **Current State** | OpenPay/Conekta recommended but no contract |
| **Action** | Initiate procurement process |
| **Owner** | Procurement + Finance |
| **Effort** | 4-8 weeks (government procurement) |
| **Risk** | Procurement delays common in government |

#### GAP-EXT-007: STP/SPEI Integration
| Attribute | Value |
|-----------|-------|
| **Required For** | All payment-enabled domains |
| **Current State** | Not initiated |
| **Action** | Apply for STP account, CLABE generation |
| **Owner** | Finance Team |
| **Effort** | 4-6 weeks |
| **Dependency** | GAP-EXT-006 |

#### GAP-EXT-008: Meta WhatsApp Business Verification
| Attribute | Value |
|-----------|-------|
| **Required For** | ALL 13 domains |
| **Current State** | Existing WhatsApp line for MARIA |
| **Action** | Verify template approval process for new domains |
| **Owner** | Marketing/Communications |
| **Effort** | 2-4 weeks per template batch |
| **Risk** | Template rejection can delay launches |

#### GAP-EXT-009: GTFS Data Access (IQT)
| Attribute | Value |
|-----------|-------|
| **Required For** | Transporte route planning |
| **Current State** | Unknown if GTFS feed exists |
| **Action** | Contact IQT for GTFS/GTFS-RT availability |
| **Owner** | Government IT Liaison |
| **Effort** | 2 weeks to assess |
| **Fallback** | Manual route data entry |

---

### 4.3 Federal System Dependencies

#### GAP-EXT-010: RENAPO CURP API
| Attribute | Value |
|-----------|-------|
| **Required For** | ALL 13 domains (identity validation) |
| **Current State** | Federal API; state access unknown |
| **Action** | Determine state's existing access or apply |
| **Owner** | Government IT Liaison |
| **Effort** | 4-8 weeks if new application required |
| **Risk** | Federal bureaucracy delays |

#### GAP-EXT-011: SAT RFC Validation (Optional)
| Attribute | Value |
|-----------|-------|
| **Required For** | Conciliacion Laboral (employer verification) |
| **Current State** | Not researched |
| **Action** | Assess need and feasibility |
| **Owner** | Government IT Liaison |
| **Effort** | TBD |
| **Priority** | LOW - nice to have |

---

## 5. Priority Resolution Matrix

### 5.1 Phase 1 Blockers (Must Resolve Before Development)

| Gap ID | Description | Owner | Target Date | Dependencies |
|--------|-------------|-------|-------------|--------------|
| GAP-API-001 | CURP Validation Service | Gov IT Liaison | Week 4 | - |
| GAP-API-002 | Chatwoot Extensions | Dev Team | Week 2 | - |
| GAP-API-003 | Notification Service | Product Manager | Week 3 | - |
| GAP-DS-001 | Citizen Profile Schema | Data Architect | Week 2 | GAP-SEC-002 |
| GAP-DS-002 | Conversation Context Schema | Dev Team | Week 2 | - |
| GAP-DS-003 | Error Response Schema | Content Team | Week 1 | - |
| GAP-BL-001 | Intent Classification Thresholds | AI/ML Team | Week 6+ | Deployment |
| GAP-BL-002 | Human Handoff Triggers | Product Manager | Week 2 | - |
| GAP-BL-003 | Queue Priority Rules | Operations Lead | Week 2 | - |
| GAP-BL-015 | Crisis Protocol Approval | Project Sponsor | Week 8 | - |
| GAP-EXT-006 | Payment Gateway Contract | Procurement | Week 8 | - |
| GAP-EXT-008 | WhatsApp Template Approval | Marketing | Week 4 | - |
| GAP-EXT-010 | RENAPO CURP API | Gov IT Liaison | Week 6 | - |

---

### 5.2 Phase 2 Dependencies (High-Volume Services)

| Gap ID | Description | Owner | Target Date | Dependencies |
|--------|-------------|-------|-------------|--------------|
| GAP-API-004 | Portal Tributario API | Gov IT Liaison | Month 3 | GAP-EXT-001 |
| GAP-API-005 | QROBUS API | Gov IT Liaison | Month 3 | GAP-EXT-002 |
| GAP-API-006 | CEA SOAP Extensions | Dev Team | Month 2 | - |
| GAP-API-007 | SAID System API | Gov IT Liaison | Week 3 (URGENT) | GAP-EXT-003 |
| GAP-DS-004 | Vehicle Debt Schema | Dev Team | Month 3 | GAP-API-004 |
| GAP-DS-005 | Enrollment Status Schema | Dev Team | Week 4 | GAP-API-007 |
| GAP-BL-004 | Tenencia Discount Rules | Content Team | Month 2 | - |
| GAP-BL-005 | Verification Calendar | Content Team | Month 2 | - |
| GAP-BL-006 | School Age Rules | Content Team | Week 2 | - |
| GAP-BL-007 | Water Payment Plans | Content Team | Month 2 | - |
| GAP-EXT-001 | Secretaria Finanzas IT | Gov IT Liaison | Week 4 | - |
| GAP-EXT-002 | IQT/AMEQ IT | Gov IT Liaison | Week 4 | - |
| GAP-EXT-003 | USEBEQ IT | Gov IT Liaison | Week 1 (URGENT) | - |
| GAP-EXT-007 | STP/SPEI Integration | Finance | Month 3 | GAP-EXT-006 |
| GAP-EXT-009 | GTFS Data | Gov IT Liaison | Month 2 | GAP-EXT-002 |

---

### 5.3 Phase 3+ Enhancements (Can Research During Development)

| Gap ID | Description | Owner | Target Phase | Dependencies |
|--------|-------------|-------|--------------|--------------|
| GAP-API-008 | CERLIN/SIRE API | Gov IT Liaison | Phase 3 | GAP-EXT-004 |
| GAP-API-009 | CENCOLAB API | Gov IT Liaison | Phase 4 | - |
| GAP-API-010 | IVEQ Case Management | Gov IT Liaison | Phase 4 | - |
| GAP-API-011 | Tarjeta Contigo API | Gov IT Liaison | Phase 4 | - |
| GAP-API-012 | IQM Case Management | Gov IT Liaison | Phase 4 | GAP-EXT-005 |
| GAP-API-013 | SEJUVE Appointments | Gov IT Liaison | Phase 4 | GAP-BL-015 |
| GAP-API-014 | Event Calendar API | Gov IT Liaison | Phase 5 | - |
| GAP-DS-006 | Certificate Types Schema | Content Team | Phase 3 | - |
| GAP-DS-007 | Labor Rights Calculator | Legal Team | Phase 4 | - |
| GAP-DS-008 | Crisis Assessment Schema | Safety Team | Phase 4 | GAP-BL-015 |
| GAP-BL-008 | Housing Eligibility Matrix | Content Team | Phase 4 | - |
| GAP-BL-009 | Social Program Rules | Content Team | Phase 4 | - |
| GAP-BL-010 | Labor Deadline Calculator | Legal Team | Phase 4 | - |
| GAP-BL-011 | Certificate Selection Logic | Content Team | Phase 3 | - |
| GAP-BL-012 | Crisis Keywords Validation | Safety Team | Phase 4 | - |
| GAP-BL-013 | Danger Assessment Protocol | Safety Team | Phase 4 | GAP-EXT-005 |
| GAP-BL-014 | Code Word System | Dev + IQM | Phase 4 | - |
| GAP-EXT-004 | RPP IT Coordination | Gov IT Liaison | Phase 3 | - |
| GAP-EXT-005 | IQM Coordination | Gov IT Liaison | Phase 4 | - |
| GAP-EXT-011 | SAT RFC Validation | Gov IT Liaison | TBD | - |

---

## 6. Gap Resolution Strategies

### 6.1 Internal Research (Read More Documentation)

**Applicable Gaps:** GAP-DS-003, GAP-DS-006, GAP-BL-005, GAP-BL-006, GAP-BL-007, GAP-BL-010, GAP-BL-011

**Process:**
1. Identify existing documentation sources
2. Extract rules and schemas
3. Validate with domain experts
4. Document in standardized format

**Effort:** 1-2 weeks per gap

---

### 6.2 External Research (Contact Government IT Teams)

**Applicable Gaps:** GAP-API-004 through GAP-API-014, GAP-EXT-001 through GAP-EXT-005

**Process:**
1. Identify IT contact for each agency
2. Schedule introduction meeting
3. Request API documentation or data sharing agreement
4. Assess feasibility and alternatives
5. Document findings

**Effort:** 2-6 weeks per gap (varies by agency responsiveness)

**Escalation Path:**
- Week 1: Initial contact attempt
- Week 2: Follow-up + escalate to supervisor
- Week 3: Executive sponsor involvement
- Week 4+: Alternative approach (deep links, manual integration)

---

### 6.3 Prototype-Based Discovery (Build to Learn)

**Applicable Gaps:** GAP-BL-001, GAP-DS-004, GAP-DS-005

**Process:**
1. Build minimal integration with available APIs
2. Collect sample data and edge cases
3. Refine schemas and rules based on real responses
4. Iterate until stable

**Effort:** Concurrent with development

---

### 6.4 Deferred (Resolve During Implementation)

**Applicable Gaps:** GAP-API-014 (Cultura), GAP-EXT-011 (SAT)

**Criteria for Deferral:**
- Low priority domain (Priority 12+)
- Nice-to-have functionality
- Alternative workaround exists

**Process:**
1. Document gap in backlog
2. Assign to appropriate phase
3. Revisit at phase boundary
4. Implement if resources available

---

## 7. Action Items Summary

### Immediate Actions (This Week)

| Action | Owner | Due Date | Gap IDs |
|--------|-------|----------|---------|
| Contact USEBEQ IT (URGENT) | Gov IT Liaison | Day 2 | GAP-EXT-003, GAP-API-007 |
| Finalize error messages (Spanish) | Content Team | Day 5 | GAP-DS-003 |
| Define citizen profile schema | Data Architect | Day 5 | GAP-DS-001 |
| Define queue priority rules | Operations Lead | Day 5 | GAP-BL-003 |
| Document handoff triggers | Product Manager | Day 5 | GAP-BL-002 |

### Week 2 Actions

| Action | Owner | Due Date | Gap IDs |
|--------|-------|----------|---------|
| Extend Chatwoot integration | Dev Team | Week 2 | GAP-API-002 |
| Extend conversation context | Dev Team | Week 2 | GAP-DS-002 |
| Document school age rules | Content Team | Week 2 | GAP-BL-006 |
| Select notification provider | Product Manager | Week 2 | GAP-API-003 |

### Week 3-4 Actions

| Action | Owner | Due Date | Gap IDs |
|--------|-------|----------|---------|
| Contact Secretaria de Finanzas | Gov IT Liaison | Week 3 | GAP-EXT-001 |
| Contact IQT/AMEQ | Gov IT Liaison | Week 3 | GAP-EXT-002 |
| Submit WhatsApp templates | Marketing | Week 3 | GAP-EXT-008 |
| Assess RENAPO access | Gov IT Liaison | Week 4 | GAP-EXT-010, GAP-API-001 |

### Month 2-3 Actions

| Action | Owner | Due Date | Gap IDs |
|--------|-------|----------|---------|
| Initiate payment gateway procurement | Procurement | Month 2 | GAP-EXT-006 |
| Document tenencia rules | Content Team | Month 2 | GAP-BL-004, GAP-BL-005 |
| Document water payment plans | Content Team | Month 2 | GAP-BL-007 |
| Apply for STP account | Finance | Month 3 | GAP-EXT-007 |
| Extend CEA SOAP integration | Dev Team | Month 2 | GAP-API-006 |

---

## 8. Risk Assessment

### High-Risk Gaps (Potential Project Impact)

| Gap ID | Risk Description | Mitigation |
|--------|-----------------|------------|
| GAP-API-004 | Portal Tributario API may not exist | Fallback to deep links + web view |
| GAP-API-005 | QROBUS API may be proprietary | Negotiate data sharing or app integration |
| GAP-API-007 | SAID system freeze during enrollment | Implement before Feb 3 or defer to 2027 |
| GAP-BL-015 | Crisis protocol approval delays | Escalate to Governor's office if needed |
| GAP-EXT-006 | Procurement delays | Start immediately; have backup vendors |

### Medium-Risk Gaps

| Gap ID | Risk Description | Mitigation |
|--------|-----------------|------------|
| GAP-EXT-003 | USEBEQ unresponsive | Executive escalation |
| GAP-EXT-008 | WhatsApp template rejection | Pre-review with Meta representative |
| GAP-EXT-010 | RENAPO access denied | Use existing state CURP validation |

### Accepted Risks (Low Impact)

| Gap ID | Risk Description | Acceptance Rationale |
|--------|-----------------|---------------------|
| GAP-API-014 | Culture calendar unavailable | Manual event entry acceptable |
| GAP-EXT-011 | SAT integration complex | Nice-to-have, not essential |

---

## 9. Dependencies Diagram

```
                                    ┌─────────────────────┐
                                    │   Phase 1 Blockers  │
                                    └──────────┬──────────┘
                                               │
          ┌────────────────────────────────────┼────────────────────────────────────┐
          │                                    │                                    │
          ▼                                    ▼                                    ▼
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│    Infrastructure   │          │   External Access   │          │   Safety Protocols  │
├─────────────────────┤          ├─────────────────────┤          ├─────────────────────┤
│ GAP-API-002 Chatwoot│          │ GAP-EXT-010 RENAPO  │          │ GAP-BL-015 Crisis   │
│ GAP-DS-001 Profile  │          │ GAP-EXT-006 Payment │          │   Approval          │
│ GAP-DS-002 Context  │          │ GAP-EXT-008 WhatsApp│          │                     │
│ GAP-DS-003 Errors   │          │                     │          │                     │
└─────────┬───────────┘          └─────────┬───────────┘          └─────────┬───────────┘
          │                                │                                │
          │                                │                                │
          └────────────────────────────────┼────────────────────────────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │   Phase 2 Services  │
                                └──────────┬──────────┘
                                           │
     ┌─────────────────┬───────────────────┼───────────────────┬─────────────────┐
     │                 │                   │                   │                 │
     ▼                 ▼                   ▼                   ▼                 ▼
┌─────────┐      ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐
│Vehiculos│      │Transporte│       │  Agua   │        │Educacion│        │   RPP   │
│Priority1│      │Priority2 │       │Priority3│        │Priority4│        │Priority5│
├─────────┤      ├─────────┤        ├─────────┤        ├─────────┤        ├─────────┤
│GAP-API-4│      │GAP-API-5│        │GAP-API-6│        │GAP-API-7│        │GAP-API-8│
│GAP-EXT-1│      │GAP-EXT-2│        │   ---   │        │GAP-EXT-3│        │GAP-EXT-4│
│GAP-EXT-7│      │GAP-EXT-9│        │         │        │ (URGENT)│        │         │
│GAP-BL-4 │      │         │        │         │        │GAP-BL-6 │        │GAP-DS-6 │
│GAP-BL-5 │      │         │        │GAP-BL-7 │        │GAP-DS-5 │        │GAP-BL-11│
└─────────┘      └─────────┘        └─────────┘        └─────────┘        └─────────┘
```

---

## 10. Completeness Targets

### Current vs Target Completeness by Domain

| Domain | Current | Phase 2 Target | Phase 4 Target | Final Target |
|--------|---------|----------------|----------------|--------------|
| 01-Atencion Ciudadana | 6/10 | 7/10 | 8/10 | 9/10 |
| 02-Transporte AMEQ | 6.5/10 | 8/10 | 9/10 | 9/10 |
| 03-Agua CEA | 6/10 | 8/10 | 9/10 | 9/10 |
| 04-Educacion USEBEQ | 6/10 | 8/10 | 8/10 | 9/10 |
| 05-Tramites Vehiculares | 6/10 | 8/10 | 9/10 | 9/10 |
| 06-Psicologia SEJUVE | 6/10 | 6/10 | 8/10 | 9/10 |
| 07-Mujeres IQM | 7/10 | 7/10 | 9/10 | 9/10 |
| 08-Cultura | 6/10 | 6/10 | 7/10 | 8/10 |
| 09-Registro Publico | 6/10 | 6/10 | 8/10 | 9/10 |
| 10-Conciliacion Laboral | 6/10 | 6/10 | 8/10 | 9/10 |
| 11-Vivienda IVEQ | 5/10 | 5/10 | 7/10 | 8/10 |
| 12-AppQRO | 6/10 | 7/10 | 8/10 | 8/10 |
| 13-SEDESOQ | 6/10 | 6/10 | 8/10 | 9/10 |
| **Average** | **6.04/10** | **6.8/10** | **8.2/10** | **8.8/10** |

### Gap Resolution Impact on Completeness

Resolving all Phase 1 Blockers adds **+0.8** to average completeness.
Resolving all Phase 2 Dependencies adds **+1.4** to average completeness.
Resolving all Phase 3+ gaps adds **+0.8** to average completeness.

---

## Appendix A: Gap ID Reference

| Gap Type | ID Range | Description |
|----------|----------|-------------|
| API Integration | GAP-API-001 to GAP-API-014 | Backend system API gaps |
| Data Schema | GAP-DS-001 to GAP-DS-008 | Data structure definitions |
| Business Logic | GAP-BL-001 to GAP-BL-015 | Rules and calculations |
| External Dependencies | GAP-EXT-001 to GAP-EXT-011 | Third-party and government coordination |
| Security | GAP-SEC-001 to GAP-SEC-002 | Privacy and compliance |

---

## Appendix B: Contact Directory (To Be Filled)

| Agency | IT Contact | Email | Phone | Status |
|--------|------------|-------|-------|--------|
| Secretaria de Finanzas | TBD | | | Not contacted |
| AMEQ/IQT | TBD | | | Not contacted |
| USEBEQ | TBD | | | URGENT - Contact immediately |
| CEA | TBD | | | Existing contact via MARIA |
| RPP | TBD | | | Not contacted |
| IVEQ | TBD | | | Not contacted |
| CCLQ | TBD | | | Not contacted |
| SEDESOQ | TBD | | | Not contacted |
| IQM | TBD | | | Not contacted |
| SEJUVE | TBD | | | Not contacted |
| Cultura | TBD | | | Not contacted |

---

## Appendix C: Related Documents

- `/gobierno-queretaro/research/FINAL_RESEARCH_SYNTHESIS.md`
- `/gobierno-queretaro/research/.swarm-progress.md`
- `/gobierno-queretaro/research/synthesis/INTEGRATION_SPECIFICATIONS.md`
- `/gobierno-queretaro/research/synthesis/PAYMENT_INTEGRATION_PATTERNS.md`
- `/gobierno-queretaro/research/synthesis/SENSITIVE_SERVICES_BEST_PRACTICES.md`
- `/gobierno-queretaro/research/synthesis/ERROR_HANDLING_FRAMEWORK.md`
- `/gobierno-queretaro/research/synthesis/CONVERSATION_FLOW_PATTERNS.md`
- `/gobierno-queretaro/research/synthesis/VOICE_AI_DESIGN_GUIDELINES.md`

---

*Document created: 2026-02-04*
*Wave 4 Synthesis Agent*
*Total gaps identified: 113*
