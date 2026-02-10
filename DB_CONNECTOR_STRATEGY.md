# Strategy: Unified Hospital Database Connector

**Challenge**: Connect $N$ hospitals with different database technologies (MySQL, Oracle, PostgreSQL, SQL Server) and different schemas (column names, table structures) to a central Kafka Event Bus.

## Architecture: The "Adapter & Normalize" Pattern

We cannot expect hospitals to change their databases. Instead, we build a **Connector Layer** that sits at the hospital edge.

### 1. The Connector Layer (Ingestion)

We have two main approaches to get data *out* of the hospital DBs:

#### Approach A: Kafka Connect (JDBC Source) - *Recommended*
Use the standard **Kafka Connect** framework. It runs as a process next to the database.
*   **Mechanism**: It periodically runs a SQL query (e.g., `SELECT * FROM patients WHERE updated_at > last_check`).
*   **Pros**: No code to write, just configuration (`.properties` files). Supports almost every DB (MySQL, Oracle, PG, MSSQL).
*   **Cons**: slightly higher latency (polling).

#### Approach B: Change Data Capture (Debezium) - *Advanced*
*   **Mechanism**: Reads the database *transaction log* (binlog) directly.
*   **Pros**: Zero latency, captures deletes.
*   **Cons**: Harder to set up (requires admin privileges on DB).

### 2. The Normalization Layer (Transformation)

Since Hospital A has table `tbl_patient` and Hospital B has `PATIENT_RECORDS`, raw data in Kafka will be messy. We need a **Normalizer**.

**Raw Topics (Heterogeneous)**:
- `raw.hospital_a.patients` -> `{"pat_id": 101, "nm": "John"}`
- `raw.hospital_b.admissions` -> `{"admission_id": "X99", "full_name": "Jane"}`

**Stream Processor (The "Connector" Logic)**:
A Python/Java app consumes these raw topics, applies mapping rules, and produces to a **Unified Topic**.

```python
# Pseudo-code for Normalizer Service
def normalize_hospital_a(raw_msg):
    return {
        "unified_id": f"HOSP_A_{raw_msg['pat_id']}",
        "name": raw_msg['nm'],
        "timestamp": raw_msg['checkin_time']
    }

def normalize_hospital_b(raw_msg):
    return {
        "unified_id": f"HOSP_B_{raw_msg['admission_id']}",
        "name": raw_msg['full_name'],
        "timestamp": raw_msg['admit_date']
    }
```

**Unified Topic (Homogeneous)**:
- `unified.global_arrivals` -> `{"unified_id": "...", "name": "...", "timestamp": ...}`
- *This is the topic your Dashboard/ML Model listens to.*

## 3. Implementation Plan for a "Hospital Connector"

If you want to build a Python-based generic connector (easier for prototyping than Kafka Connect):

### `generic_db_connector.py`
This script would run at each hospital.

1.  **Config**: Takes a `db_config.json` (Host, SQL Query, Column Mapping).
2.  **Poll**: Runs the query every 5 seconds.
3.  **Map**: Renames columns based on config.
4.  **Send**: Pushes to your central Kafka.

```json
// hospital_a_config.json
{
    "db_type": "mysql",
    "query": "SELECT id, name, entered_at FROM local_patients WHERE entered_at > %s",
    "mapping": {
        "id": "patient_id",
        "name": "patient_name",
        "entered_at": "arrival_time"
    }
}
```

## Security Note
Since hospitals are external:
1.  **VPN/Tunnel**: Use 1-way MTLS (Mutual TLS) authentication for Kafka.
2.  **Encryption**: All data transit is SSL encrypted.
