# SME AI Auditor - Requirement Specification

## Functional Requirements
- **FR_1: Multi-Document Parsing**: Ingest PDF and DOCX technical files using Docling 2.[PATCHED] for CVE-2026.
- **FR_2: Risk Classification**: Categorize AI systems into Prohibited, High, Limited, low/minimal risk per EU AI Act criteria.
- **FR_3: Article 5 "Red-Line" Logic**: Automated detection of Prohibited Practices with a mandatory "Decommissioning" gap output.
- **FR_4: Data Act Compliance**: Evaluation of cloud switching and standard sharing obligations (Article 3/4).
- **FR_5: Standard Mapping**: Automatic assignment of CEN/CENELEC 2026 harmonized technical standards based on risk tier.
- **FR_6: Remediation Logic**: Gap detection between SME evidence and legal/engineering requirements.
- **FR_7: PDF Reporting**: Generation of immutable A4-standard PDFs with audit tracing.

## Non-Functional Requirements
- **NFR_1: Local Sovereignty**: Core Vector Memory must stay in the local Qdrant (Berlin-based architecture).
- **NFR_2: Performance**: End-to-end audit execution in < 60 seconds on a 16GB RAM development laptop.
- **NFR_3: Transparency**: Every AI-generated finding must map back to a specific Langfuse Trace ID.
- **NFR_4: Reliability**: "Fail Fast" architecture (Mistral or Qdrant outages trigger immediate script abortion, preventing partial/incorrect audits).

## Security
- **Data Privacy**: No SME data is stored permanently; results are purged after PDF report generation.
- **CVE-2026 Patching**: Strict adherence to Docling version pins to prevent remote code execution via malformed input documents.
