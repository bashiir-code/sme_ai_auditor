# SME AI Auditor - Quick Reference

## Installation
1. Prepare Environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure `.env` with MISTRAL_API_KEY, QDRANT_URL, and LANGFUSE metadata.

## Standard Audit Run
To execute a full compliance audit:
```bash
python src/main.py --docs ./data/sme_docs_examples --system "Our recruitment facial scanner."
```

## System Entry Points
- `src/main.py`: Final orchestrator script.
- `reports/`: Target directory for Markdown and PDF audit reports.
- `data/`: Regulatory knowledge store (EU AI Act, Data Act).

## Common Verification Commands
- `pytest tests/unit/ -v`: Confirm individual logic components.
- `pytest tests/integration/ -v`: Confirm full orchestrator flow.

## Compliance Tiers
| Tier | SME Obligations |
|---|---|
| **Prohibited** | Immediate decommissioning required. |
| **High** | Full QMS (ISO 42001), Data Gov, Human Oversight. |
| **Limited** | Transparency disclosures, user flagging. |
| **Minimal** | Voluntary code of conduct adherence. |
