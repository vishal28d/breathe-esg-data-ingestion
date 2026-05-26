# Sources

## 1. SAP: Fuel and Procurement
*   **Real-world Format Researched**: SAP IS-Oil & Gas, standard ALV grid exports, and IDoc flat-file conversions.
*   **What we learned**: While IDocs (XML/EDI) are standard for system-to-system, legacy clients often use transaction `WE19` or custom ABAP reports to dump CSVs. These CSVs frequently use localized formatting (e.g., German `1.234,50` instead of `1234.50`) and internal SAP aliases (`MENGE` for quantity, `MEINS` for unit, `WERKS` for plant).
*   **Sample Data**: `sap_fuel_export.csv`. We used realistic headers (`MATNR`, `WERKS`, `MENGE`). We included comma-as-decimal values, German dates (`DD.MM.YYYY`), an unknown material code, and a missing value to trigger our validation logic.
*   **What would break in prod**: Custom SAP configurations. Every SAP deployment is heavily customized. If a client maps plant codes to profit centers rather than physical facilities, our `Facility` mapping logic would fail.

## 2. Utility Data: Electricity
*   **Real-world Format Researched**: Green Button standard and typical PDF/Portal spreadsheet scrapes (e.g., ENERGY STAR Portfolio Manager templates).
*   **What we learned**: Billing periods almost never span exact calendar months. They run from meter read to meter read (e.g., 14th to 13th). Units can vary drastically (kWh, MWh, Therms) based on the tariff. Bills also frequently contain negative consumption values for solar net-metering.
*   **Sample Data**: `utility_electricity.csv`. We included non-calendar periods, mixed units (kWh and MWh), and a negative consumption row representing a solar credit.
*   **What would break in prod**: PDF scraping. If the client cannot provide a CSV and relies on scraping utility PDFs, the ingestion layer requires an OCR/LLM extraction pipeline before it hits our CSV parser.

## 3. Corporate Travel
*   **Real-world Format Researched**: Navan (TripActions) API (`/v1/bookings`) and SAP Concur Travel Profile API.
*   **What we learned**: Flight APIs rarely give you carbon emissions out of the box. They give you origin and destination IATA codes (e.g., `LHR` to `JFK`) and cabin class.
*   **Sample Data**: `api/sample_travel.py`. Simulated JSON payload. Contains real IATA codes so our Haversine distance calculator can actually work. Contains an unknown IATA code (`XYZ`) and a missing ground transport distance to trigger warning flags.
*   **What would break in prod**: Multi-leg flights. A booking from `DEL` to `SFO` might route through `FRA`. If the API only provides origin and final destination, calculating the great-circle distance will underestimate the emissions because it ignores the layover routing inefficiency.
