# Tasks: HashiCorp Vault PKI MCP Tools

**Input**: Design documents from `/specs/001-vault-pki-mcp-tools/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Test tasks are included but OPTIONAL. Only implement if explicitly requested or TDD approach is desired.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure: vault-mcp-server/src/{tools,services,models}, vault-mcp-server/tests/{unit,integration}
- [x] T002 Initialize Python project with pyproject.toml (dependencies: fastmcp>=0.1.0, hvac>=2.0.0, cryptography>=41.0.0, pydantic>=2.0.0)
- [x] T003 [P] Configure development tools: pytest, pytest-asyncio, pytest-mock, black, ruff
- [x] T004 [P] Create vault-mcp-server/README.md with setup instructions and environment variable documentation
- [x] T005 [P] Create vault-mcp-server/src/__init__.py, vault-mcp-server/src/tools/__init__.py, vault-mcp-server/src/services/__init__.py, vault-mcp-server/src/models/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement VaultClient wrapper in vault-mcp-server/src/services/vault_client.py (hvac client initialization, environment variable auth, connection validation)
- [x] T007 [P] Create base Pydantic models: PKISecretsEngine in vault-mcp-server/src/models/pki_engine.py
- [x] T008 [P] Create base Pydantic models: Certificate in vault-mcp-server/src/models/certificate.py with field validators
- [x] T009 [P] Create base Pydantic models: Issuer, Warning, HierarchyMetadata in vault-mcp-server/src/models/certificate.py
- [x] T010 Setup MCP server entry point in vault-mcp-server/main.py with FastMCP initialization and environment validation
- [x] T011 [P] Implement error handling utilities and MCP error response formatting in vault-mcp-server/src/services/vault_client.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View All PKI Secrets Engines (Priority: P1) 🎯 MVP

**Goal**: Enable users to discover all PKI mount points in their Vault instance, excluding non-PKI secrets engines

**Independent Test**: Call the list_pki_secrets_engines tool and verify it returns only mount points with type "pki" and excludes all other secrets engine types (kv, transit, etc.). Test with empty results (no PKI engines), single PKI engine, and multiple PKI engines.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T012 [P] [US1] Unit test for VaultClient.list_pki_engines() with mocked hvac responses in vault-mcp-server/tests/unit/test_vault_client.py
- [ ] T013 [P] [US1] Integration test for list_pki_secrets_engines tool in vault-mcp-server/tests/integration/test_list_pki_engines.py (requires running Vault instance)

### Implementation for User Story 1

- [x] T014 [US1] Implement VaultClient.list_mounted_secrets_engines() method in vault-mcp-server/src/services/vault_client.py
- [x] T015 [US1] Implement VaultClient.list_pki_engines() method to filter PKI mounts in vault-mcp-server/src/services/vault_client.py
- [x] T016 [US1] Create list_pki_secrets_engines tool function in vault-mcp-server/src/tools/list_pki_engines.py with @mcp.tool() decorator
- [x] T017 [US1] Register list_pki_secrets_engines tool in vault-mcp-server/main.py
- [x] T018 [US1] Add error handling for Vault connection errors (VAULT_CONNECTION_ERROR, AUTHENTICATION_ERROR, PERMISSION_ERROR)
- [x] T019 [US1] Add validation for VAULT_ADDR and VAULT_TOKEN environment variables

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can list all PKI secrets engines.

---

## Phase 4: User Story 2 - View Certificates Grouped by Issuer Hierarchy (Priority: P1)

**Goal**: Enable users to view all certificates from a PKI engine organized by root and intermediate CA hierarchy, with expiration and revocation status

**Independent Test**: Call the list_certificates tool for a known PKI secrets engine path and verify results are correctly grouped by root issuer CN and intermediate issuer CN, with each certificate showing subject CN, expiration status (Yes/No), and revocation status (Yes/No). Test with direct root issuance (no intermediate), multi-level intermediate chains, inactive issuers, and permission errors.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T020 [P] [US2] Unit test for CertificateParser.parse_pem() in vault-mcp-server/tests/unit/test_certificate_parser.py (test valid, expired, revoked certificates)
- [ ] T021 [P] [US2] Unit test for CertificateHierarchy.build_hierarchy() in vault-mcp-server/tests/unit/test_certificate_hierarchy.py (test root/intermediate grouping)
- [ ] T022 [P] [US2] Integration test for list_certificates tool in vault-mcp-server/tests/integration/test_list_certificates.py (requires PKI engine with issued certificates)

### Implementation for User Story 2

- [x] T023 [P] [US2] Implement CertificateParser service in vault-mcp-server/src/services/certificate_parser.py (PEM parsing, expiration check, revocation check)
- [x] T024 [P] [US2] Create CertificateHierarchy, RootIssuerGroup, IntermediateIssuerGroup Pydantic models in vault-mcp-server/src/models/certificate.py
- [x] T025 [US2] Implement VaultClient.list_certificates() method in vault-mcp-server/src/services/vault_client.py (list serials for PKI mount)
- [x] T026 [US2] Implement VaultClient.read_certificate() method in vault-mcp-server/src/services/vault_client.py (read cert details by serial)
- [x] T027 [US2] Implement VaultClient.read_issuer() method in vault-mcp-server/src/services/vault_client.py (read CA chain by issuer_id)
- [x] T028 [US2] Implement HierarchyBuilder service in vault-mcp-server/src/services/certificate_hierarchy.py (build nested structure from certificates)
- [x] T029 [US2] Add logic to parse ca_chain and identify root CA (last cert in chain) in vault-mcp-server/src/services/certificate_hierarchy.py
- [x] T030 [US2] Add logic to handle direct root issuance (no intermediate) in vault-mcp-server/src/services/certificate_hierarchy.py
- [x] T031 [US2] Add logic to handle inactive issuers with "(issuer inactive)" notation in vault-mcp-server/src/services/certificate_hierarchy.py
- [x] T032 [US2] Implement partial success with warnings for permission errors in vault-mcp-server/src/services/certificate_hierarchy.py
- [x] T033 [US2] Implement graceful degradation for malformed certificate data (mark fields as "N/A" or "Unknown") in vault-mcp-server/src/services/certificate_parser.py
- [x] T034 [US2] Implement concurrent certificate fetching using asyncio.gather() for performance in vault-mcp-server/src/services/certificate_hierarchy.py
- [x] T035 [US2] Create list_certificates tool function in vault-mcp-server/src/tools/list_certificates.py with @mcp.tool() decorator
- [x] T036 [US2] Add input validation for pki_mount_path parameter (alphanumeric, underscore, hyphen only) in vault-mcp-server/src/tools/list_certificates.py
- [x] T037 [US2] Register list_certificates tool in vault-mcp-server/main.py
- [x] T038 [US2] Add error handling for PKI_MOUNT_NOT_FOUND, PERMISSION_ERROR, INVALID_MOUNT_PATH in vault-mcp-server/src/tools/list_certificates.py
- [x] T039 [US2] Calculate and populate HierarchyMetadata (total_certificates, expired_count, revoked_count, root_ca_count, intermediate_ca_count) in vault-mcp-server/src/services/certificate_hierarchy.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can list PKI engines and view complete certificate hierarchies.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T040 [P] Add comprehensive docstrings to all modules, classes, and functions following Google Python style guide
- [ ] T041 [P] Run black formatter on all Python files in vault-mcp-server/
- [ ] T042 [P] Run ruff linter and fix all issues in vault-mcp-server/
- [ ] T043 [P] Add logging statements for debugging (Vault API calls, certificate parsing, hierarchy construction) using Python logging module
- [ ] T044 [P] Optimize performance: implement connection pooling and caching for repeated issuer lookups in vault-mcp-server/src/services/vault_client.py
- [ ] T045 [P] Add unit tests for edge cases: orphaned certificates, multi-level intermediate chains, empty certificate lists in vault-mcp-server/tests/unit/
- [ ] T046 Update vault-mcp-server/README.md with usage examples, troubleshooting section, and security best practices from quickstart.md
- [ ] T047 Create example MCP client scripts for testing tools in vault-mcp-server/examples/
- [ ] T048 Validate all quickstart.md scenarios manually or with automated scripts
- [ ] T049 Add type hints throughout codebase and run mypy type checker
- [ ] T050 Security review: ensure no VAULT_TOKEN logging, validate input sanitization, confirm TLS verification enabled by default

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T005) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion (T006-T011)
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (T006-T011)
  - User Story 2 is INDEPENDENT of User Story 1 (can be implemented in parallel)
- **Polish (Phase 5)**: Depends on User Stories 1 and 2 completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (T006-T011) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (T006-T011) - INDEPENDENT of User Story 1 (can run in parallel)

Both user stories have P1 priority and are independently testable. Either can be the MVP, but User Story 1 is simpler and recommended as initial MVP.

### Within User Story 1

1. Tests (T012-T013) can run in parallel if included
2. T014 must complete before T015 (list all mounts before filtering)
3. T015 must complete before T016 (service logic before tool wrapper)
4. T016 must complete before T017 (tool implementation before registration)
5. T018-T019 can be done after T017 (error handling enhancement)

### Within User Story 2

1. Tests (T020-T022) can run in parallel if included
2. Models (T024) can run in parallel with services (T023)
3. T023-T024 must complete before hierarchy building (T025-T034)
4. VaultClient methods (T025-T027) can run in parallel (different methods)
5. T028 must complete before T029-T033 (hierarchy builder before edge case logic)
6. T034 can be done in parallel with T029-T033 (performance optimization)
7. T035-T039 are sequential (tool creation → validation → registration → error handling → metadata)

### Parallel Opportunities

**Setup Phase**:
- T003, T004, T005 can all run in parallel (independent files)

**Foundational Phase**:
- T007, T008, T009 can all run in parallel (different model files)
- T011 can run in parallel with T007-T009 (error utilities separate from models)

**User Story 1**:
- T012-T013 (tests) can run in parallel
- T018-T019 can run in parallel

**User Story 2**:
- T020-T022 (tests) can run in parallel
- T023-T024 can run in parallel
- T025-T027 can run in parallel
- T029-T033 can run in parallel (different edge cases)
- T034 can run in parallel with T029-T033

**Polish Phase**:
- T040, T041, T042, T043, T044, T045, T049 can all run in parallel (different concerns)

**Cross-Phase Parallel Execution**:
- Once Foundational (T006-T011) completes, User Story 1 (T014-T019) and User Story 2 (T023-T039) can proceed in parallel

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together (if tests requested):
Task T020: "Unit test for CertificateParser.parse_pem()"
Task T021: "Unit test for CertificateHierarchy.build_hierarchy()"
Task T022: "Integration test for list_certificates tool"

# Launch service and model creation together:
Task T023: "Implement CertificateParser service"
Task T024: "Create CertificateHierarchy Pydantic models"

# Launch VaultClient methods together:
Task T025: "Implement VaultClient.list_certificates()"
Task T026: "Implement VaultClient.read_certificate()"
Task T027: "Implement VaultClient.read_issuer()"

# Launch edge case handling together:
Task T029: "Parse ca_chain and identify root CA"
Task T030: "Handle direct root issuance"
Task T031: "Handle inactive issuers"
Task T032: "Implement partial success with warnings"
Task T033: "Graceful degradation for malformed data"
Task T034: "Concurrent certificate fetching"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) - RECOMMENDED

**Why User Story 1 as MVP**: Simpler implementation, foundational capability required before certificate operations, demonstrates MCP integration without complex hierarchy logic.

1. **Phase 1**: Complete T001-T005 (Setup)
2. **Phase 2**: Complete T006-T011 (Foundational) ⚠️ CRITICAL BLOCKER
3. **Phase 3**: Complete T014-T019 (User Story 1 only)
4. **STOP and VALIDATE**: 
   - Test list_pki_secrets_engines tool with multiple Vault configurations
   - Verify filtering works correctly (only PKI engines returned)
   - Test error handling (invalid token, connection failures)
5. **Deploy/Demo**: MVP ready for production use!

**Estimated Task Count**: 5 (Setup) + 6 (Foundational) + 6 (US1) = **17 tasks**

### Incremental Delivery

1. **Foundation**: Complete T001-T011 → MCP server structure ready
2. **MVP (US1)**: Add T014-T019 → List PKI engines tool functional → **Deploy/Demo**
3. **Full Feature (US2)**: Add T023-T039 → Certificate hierarchy tool functional → **Deploy/Demo**
4. **Polish**: Add T040-T050 → Production-ready quality → **Final Deploy**

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With 2-3 developers:

**Week 1**:
- Developer A: T001-T005 (Setup)
- Developer B: Help with setup, prepare test Vault environment

**Week 2**:
- All developers: T006-T011 (Foundational - collaborate)

**Week 3**:
- Developer A: T014-T019 (User Story 1)
- Developer B: T023-T027 (User Story 2 - VaultClient methods)
- Developer C: T023-T024 (User Story 2 - Parser and Models)

**Week 4**:
- Developer A: T040-T046 (Polish - documentation)
- Developer B: T028-T039 (User Story 2 - Hierarchy builder and tool)
- Developer C: T047-T050 (Polish - testing and security)

Stories complete and integrate independently.

---

## Task Summary

### Total Task Count: 50 tasks

**By Phase**:
- Phase 1 (Setup): 5 tasks (T001-T005)
- Phase 2 (Foundational): 6 tasks (T006-T011)
- Phase 3 (User Story 1): 8 tasks (T012-T019, including 2 optional tests)
- Phase 4 (User Story 2): 20 tasks (T020-T039, including 3 optional tests)
- Phase 5 (Polish): 11 tasks (T040-T050)

**By User Story**:
- User Story 1: 8 tasks (6 implementation + 2 optional tests)
- User Story 2: 20 tasks (17 implementation + 3 optional tests)

**Parallel Opportunities Identified**: 25 tasks marked with [P] can run in parallel within their phases

**Independent Test Criteria**:
- **User Story 1**: Successfully lists all PKI secrets engines, filters out non-PKI types, handles errors gracefully
- **User Story 2**: Successfully retrieves and organizes certificates by hierarchy, displays correct expiration/revocation status, handles edge cases (inactive issuers, direct root issuance, permission errors)

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = **17 tasks** (excluding optional tests)

---

## Format Validation ✅

All tasks follow the required checklist format:
- ✅ Checkbox: `- [ ]` prefix
- ✅ Task ID: Sequential T001-T050
- ✅ [P] marker: Present on 25 parallelizable tasks
- ✅ [Story] label: Present on all User Story 1 (US1) and User Story 2 (US2) tasks
- ✅ Description: Clear action with exact file path
- ✅ Setup/Foundational/Polish phases: NO story label (correct)
- ✅ User Story phases: Story label present (correct)

---

## Notes

- Tests are OPTIONAL - only implement if explicitly requested or TDD approach desired
- [P] tasks target different files with no dependencies (true parallelism)
- [Story] labels enable traceability to user stories in spec.md
- Each user story is independently completable and testable
- Foundational phase (T006-T011) is CRITICAL BLOCKER for all user stories
- User Stories 1 and 2 can be implemented in parallel after Foundational phase
- Stop at Phase 3 checkpoint to validate MVP (User Story 1 only) before proceeding
- Commit after each task or logical group for easy rollback
- All file paths are absolute from repository root
