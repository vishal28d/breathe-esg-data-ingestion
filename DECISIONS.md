# Decisions

## 1. What subset of each source did we handle?
*   **SAP**: We chose to handle **Fuel Procurement (Scope 1/3)** via flat file CSV export. We ignored complex IDoc structures because many legacy/mid-market SAP IS-Oil implementations still rely on standard ABAP ALV CSV exports for external reporting.
*   **Utility Data**: We handled **Purchased Electricity (Scope 2)** via Green Button / Portal CSVs. We ignored complex time-of-use (TOU) interval data (15-min increments) and focused on aggregate billing period consumption, which is standard for Scope 2 location-based reporting.
*   **Corporate Travel**: We handled **Flights, Hotels, and Ground Transport (Scope 3)** simulating a Navan/Concur API JSON payload. We ignored complex multi-leg layover routing where only the final destination is booked, assuming the API provides each leg individually.

## 2. Ingestion Mechanisms
*   **SAP & Utility**: Handled via **File Upload**. Why? Procurement and Facilities teams often do not have IT resources to build API bridges for ESG tools. Uploading a CSV dump is the most realistic day-1 onboarding experience.
*   **Travel**: Handled via **API Pull**. Why? Platforms like Navan and Concur have excellent, modern REST APIs. Travel data is highly structured, and manual CSV exports from these platforms are unnecessary busywork.

## 3. Ambiguities Resolved
*   **SAP German Locale**: We encountered numbers like `12.500,00` and dates like `14.01.2024`. We decided to build a custom `safe_decimal` parser using regex to explicitly detect and convert European number formats, rather than relying on brittle locale settings.
*   **Utility Billing Cycles**: Utility bills rarely align with calendar months (e.g., 14th to 13th). We decided to store explicit `activity_date_start` and `activity_date_end` fields rather than a generic "Month" field. We also decided to flag non-calendar periods with an informational warning rather than marking the row as an error, as this is expected reality.
*   **Travel Distances**: APIs often only provide IATA airport codes, not flown distance. We implemented a great-circle (Haversine) distance calculator as a fallback, adding a 10% uplift factor to account for routing inefficiency.

## 4. What we would ask the PM
1.  **Approval Workflow**: If an analyst rejects a row, should the system notify the client to re-upload, or does the analyst just edit the row manually and add an audit note?
2.  **Emission Factors**: Do clients need to bring their own custom emission factors (e.g., a specific green tariff for a specific utility), or do we strictly enforce a global, system-wide database (DEFRA/EPA)?
3.  **SAP Scope**: Do we need to handle SAP BOMs (Bill of Materials) for Scope 3 Category 1 (Purchased Goods), or are we strictly focusing on direct energy/fuel procurement right now?
