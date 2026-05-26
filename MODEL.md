# Breathe ESG Data Model

## Core Philosophy
We designed a system that preserves the **raw source of truth** while surfacing a clean, validated layer for analysts. The data model explicitly separates ingestion lineage from business logic.

## Entity-Relationship Breakdown

### 1. Multi-Tenancy & Context
*   **Tenant**: Represents a client company (e.g., "Acme Corp"). Every data row is strictly isolated by a `tenant_id` foreign key.
*   **Facility**: Represents physical sites (e.g., "Pune Plant"). Critical for resolving internal SAP codes (`WERK_001`) into human-readable locations.

### 2. Lineage & Audit Trail
*   **DataImport**: Tracks a specific ingestion event. Contains `source_type` (SAP, Utility, Travel), `imported_at`, and `status`. It answers the question: *"Which file/API call generated these rows?"*
*   **RawDataRecord**: An immutable store. We save the original parsed row (from CSV/JSON) as a serialized JSON string. **This is never edited.** If an auditor questions a value, this proves exactly what the client system provided.

### 3. Normalization & Review (Analyst Layer)
*   **NormalizedRecord**: The core business entity. A one-to-one mapping with `RawDataRecord`, but parsed into strict data types:
    *   **Categorization**: `scope` (1, 2, 3), `category` (diesel, electricity, flight).
    *   **Values**: `original_value`/`original_unit` vs `normalized_value`/`normalized_unit` (always SI units like kWh, km, litres).
    *   **Emissions**: Computed `co2e_kg` via lookup.
    *   **Workflow**: `status` (PENDING, APPROVED, FLAGGED, ERROR).
    *   **Auditability**: If an analyst edits the row (e.g., fixing a typo), it is tracked via `edited_by` and `edit_note`. The `RawDataRecord` remains untouched.

### 4. Computation
*   **EmissionFactor**: A lookup table keyed by `(category, unit)` mapping to `kg_co2e_per_unit`. Sourced from DEFRA, EPA, etc.

## Handling the Requirements
*   **Multi-tenancy**: Handled via `Tenant` FK on `DataImport`, `Facility`, and `NormalizedRecord`.
*   **Scope Categorization**: Hard-coded into the normalizer parsers (e.g., SAP Fuel = Scope 1, Travel = Scope 3) to prevent logic drift.
*   **Source-of-truth**: The `RawDataRecord` handles this immutably.
*   **Unit Normalization**: Handled dynamically during parsing using conversion dicts in `parsers.py`.
*   **Audit Trail**: The `status` state machine, combined with `approved_by`, `edited_by`, and the `RawDataRecord` link, ensures total traceability.
