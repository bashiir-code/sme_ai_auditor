# The SME AI Auditor: Compliance-as-a-Service for the EU AI & Data Act (2026)

![SME AI Auditor Architecture]![alt text](image.png)

## 🚀 Project Overview

"The SME AI Auditor" is an automated **Compliance-as-a-Service** tool designed to assist Small and Medium-sized Enterprises (SMEs) in navigating the complex regulatory landscape of Artificial Intelligence in the European Union. By analyzing an SME's AI technical documentation, the tool generates a professional readiness report, identifying risk levels (Prohibited, High, Limited, Minimal) and pinpointing specific legal "gaps" against the **EU AI Act** and the **EU Data Act**.

This project is built upon a **Default Sovereign Tech Stack (2026)**, meticulously selected for its commitment to Data Sovereignty, Scalability, and Zero Licensing Fees (Open Source principles), with a strong emphasis on Finnish GDPR and Trust standards.

## 🎯 Mission & Vision

Our mission is to democratize AI compliance, making it accessible and manageable for SMEs. We envision a future where businesses can innovate with AI confidently, knowing their systems adhere to the highest ethical and legal standards set by the European Union, without incurring prohibitive costs or requiring specialized legal teams.

## ✨ Key Features

*   **Automated Compliance Audits**: Rapid analysis of AI technical specifications against EU regulations.
*   **Risk Level Classification**: Categorization of AI systems into Prohibited, High-Risk, Limited Risk, or Minimal Risk based on the EU AI Act.
*   **Legal Gap Detection**: Identification of specific non-compliance areas and actionable recommendations.
*   **Structured Reporting**: Generation of professional, auditable PDF reports with detailed findings, evidence, and legal reasoning.
*   **Data Sovereignty**: Built on an EU-centric, open-source technology stack ensuring data residency and compliance with GDPR.
*   **Dual-Act Compliance**: Comprehensive assessment against both the EU AI Act and the EU Data Act.

## 🛠️ Sovereign Tech Stack (2026)

Our technology stack is chosen to meet stringent requirements for data sovereignty, performance, and cost-effectiveness in the 2026 European context. The table below outlines the core components:

| Component | Default Choice | Why it's the "Best" for Finland / SME AI Auditor |
| :-------- | :------------- | :------------------------------------------------- |
| **Orchestrator** | Haystack 2.x | German-engineered. Best for modular, production-ready legal pipelines. Provides robust RAG capabilities. |
| **Vector DB** | Qdrant | Berlin-based. Optimized for EU data residency and complex metadata filtering. High-performance vector storage. |
| **Inference Model (Auditor Brain)** | Mistral AI API (Mistral Small 3.1) | French-made. Top-tier reasoning for legal analysis, cost-efficient via API, maintaining EU sovereignty. [1] |
| **Inference Model (Goose Brain)** | Qwen API (Qwen 2.5-Coder) | Optimized for agentic workflows and tool-calling via API, complementing Mistral for orchestration tasks. [2] |
| **Document Parser** | Docling (IBM Research) | Exceptional at reading complex tables found in EU AI Act Annexes and technical specs. Critical for accurate ingestion. [3] |
| **Serving Engine** | vLLM (for self-hosted models) | The industry standard for high-throughput, self-hosted model serving. (Note: API usage for Mistral/Qwen reduces local vLLM dependency for inference). |
| **Hosting** | Hetzner (Helsinki) | Keeps data physically on Finnish soil to satisfy Finnish GDPR/Trust standards. |
| **Observability** | LangFuse | Open-source tracing to prove how the AI reached its legal conclusions, crucial for auditability. |
| **Reporting** | WeasyPrint + Jinja2 | Industrial-grade HTML/MD to PDF conversion with professional templating for high-quality, customizable reports. [4] |

## ⚙️ Operational Workflow

The SME AI Auditor operates through a refined multi-step process to ensure accurate and auditable compliance assessments:

1.  **Ingestion**: The user uploads technical specifications or 
Y-tunnus information. **Docling** parses the text, meticulously preserving table structures, which is critical for accurate analysis of EU AI Act Annexes and technical documentation.

2.  **Retrieval**: **Haystack 2.x** queries a **Qdrant** vector index, which contains the latest 2026 EU AI Office guidelines, the EU AI Act, the EU Data Act, and relevant CEN/CENELEC harmonized standards.

3.  **Analysis (Mistral AI API)**: **Mistral Small 3.1** (via API) performs a multi-step reasoning task:
    *   **Step 1: Classification**: Determines the AI system's risk level (Prohibited, High-Risk, Limited, Minimal) based on the EU AI Act, including a preliminary **Article 5 (Prohibited Practices) check**.
    *   **Step 2: Requirement Mapping**: Identifies applicable Articles from the EU AI Act and EU Data Act, and relevant CEN/CENELEC harmonized standards.
    *   **Step 3: Gap Detection**: Compares the SME's documentation against mapped requirements to identify specific legal "gaps." This step leverages the structured output from **Pydantic models** for robust and auditable findings.

4.  **Orchestration (Qwen API via Goose)**: **Goose**, powered by **Qwen 2.5-Coder** (via API), orchestrates the entire workflow, including:
    *   Managing data flow between components.
    *   Automating compliance test suites.
    *   Summarizing audit results.
    *   Interacting with the **Model Context Protocol (MCP)** ecosystem for broader tool integration and regulatory database access.

5.  **Reporting**: The system generates a structured report using **Pydantic models** for data validation. This data is then templated with **Jinja2** and converted into a professional, high-quality PDF using **WeasyPrint** for the client.

6.  **Observability**: **LangFuse** provides end-to-end tracing of the AI's decision-making process, proving how it reached its legal conclusions and ensuring full auditability.

## 🧠 Dual-Model AI Strategy

Our approach leverages a dual-model AI strategy to maximize efficiency and accuracy:

*   **Mistral Small 3.1 (API)**: Serves as the primary "Auditor Brain" for nuanced **legal reasoning** and compliance analysis. Its strong performance in understanding complex legal texts makes it ideal for classification, requirement mapping, and gap detection against the EU AI Act and Data Act.
*   **Qwen 2.5-Coder (API)**: Acts as the "Goose Brain" for **agentic workflows** and **orchestration**. Its superior tool-calling capabilities and proficiency in handling multi-step tasks enable Goose to efficiently manage the overall audit process, interact with external tools, and automate compliance tasks.

This separation of concerns ensures that each model is utilized for its optimal strength, leading to a more robust and reliable "Compliance-as-a-Service" solution.

## 💡 Senior Implementation Pro-Tips (2026)

*   **Security Patching**: Always ensure `docling` is pinned to a patched release (`2.15.0+`) to mitigate known vulnerabilities like `CVE-2026-24009` (RCE vulnerability) [3].
*   **Structured Output**: Utilize **Pydantic models** (as defined in `src/models.py`) for all AI outputs. This ensures strict data validation, type safety, and prevents downstream reporting errors, making the system more robust and auditable.
*   **Observability**: Implement **LangFuse `@observe()` decorators** around critical functions (e.g., `DoclingParser` and `DataActChecker` calls) to track the "cost per audit," performance metrics, and the AI's reasoning steps. This is vital for auditability and continuous optimization.
*   **Report Quality**: Replace basic PDF generation with **WeasyPrint** and **Jinja2**. This combination allows for highly customizable, professional-grade PDF reports with complex layouts, dynamic content, and branding, crucial for client-facing deliverables [4].

## 💻 Setup & Installation

This project is designed for an **Ubuntu laptop with 16GB of RAM**, leveraging API-based LLMs to minimize local resource consumption. We use `uv` for fast and robust Python package management.

### Prerequisites

*   Ubuntu Operating System
*   Python 3.9+ (recommended)
*   `curl` (for `uv` installation)

### 1. Install `uv`

`uv` is a modern, high-performance Python package installer and resolver. If you don't have it installed, run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env # Ensure uv is available in your current session
```

### 2. Clone the Repository

```bash
git clone https://github.com/your-repo/sme_ai_auditor.git # Replace with your actual repo URL
cd sme_ai_auditor
```

### 3. Setup AI Companions & Environment

Run the `uv`-optimized setup script. This script will create a virtual environment, install project dependencies, and configure Aider and Goose.

```bash
chmod +x setup_ai_companions_uv.sh
./setup_ai_companions_uv.sh
```

### 4. Configure Environment Variables

Copy the provided `.env.template_api` to `.env` and fill in your API keys for Mistral AI and Qwen. You will need to obtain these from their respective providers.

```bash
cp .env.template_api .env
nano .env # Edit this file with your actual API keys
```

**Example `.env` configuration:**

```dotenv
# SME AI Auditor - Sovereign Tech Stack Configuration (Mistral AI API Optimized)

# 1. Inference Model (Mistral AI API)
MISTRAL_API_KEY=sk-your_mistral_api_key_here
MODEL_NAME=mistral/mistral-small-latest

# 2. Qwen API Configuration for Goose
QWEN_API_KEY=sk-your_qwen_api_key_here
GOOSE_MODEL=qwen/qwen-2.5-coder

# 3. Vector Database (Qdrant - Berlin-based)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION_NAME=sme_ai_auditor_compliance

# 4. Document Parser (Docling - IBM Research)
DOCLING_ENDPOINT=http://localhost:8080 # Or your Docling service endpoint

# 5. Observability (LangFuse - Open-source)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# 6. Hosting (Hetzner Helsinki) - Placeholder for deployment
HETZNER_REGION=hel1

# 7. AI Companion Configurations
AIDER_MODEL=mistral/mistral-small-latest
AIDER_GIT_COMMIT=true
GOOSE_MCP_SERVER_URL=http://localhost:3000 # Or your MCP server endpoint
```

### 5. Activate Virtual Environment

Before running any project commands, activate your virtual environment:

```bash
source .venv/bin/activate
```

### 6. Install Project Dependencies (if not already done by setup script)

```bash
uv pip install -r requirements.txt
```

## 🚀 Usage

### Running Aider (Coding Companion)

Ensure your virtual environment is active and `MISTRAL_API_KEY` is exported. Then, run Aider from your project root:

```bash
export MISTRAL_API_KEY=sk-your_mistral_api_key_here # If not in .env or not loaded
aider
```

### Running Goose (Workflow Orchestrator)

Ensure your virtual environment is active and `QWEN_API_KEY` is exported. Then, run Goose:

```bash
export QWEN_API_KEY=sk-your_qwen_api_key_here # If not in .env or not loaded
goose session --prompt "Run compliance audit for SME X, summarize findings."
```

## 📂 Project Structure

```
sme_ai_auditor/
├── ARCHITECTURE.md       ← Complete system design
├── REQUIREMENTS.md       ← Detailed specifications
├── QUICK_REFERENCE.md    ← Developer cheat sheet
├── SETUP.md              ← Installation guide
├── README.md             ← Project overview (this file)
├── requirements.txt      ← Python dependencies (managed by uv)
├── .env.template         ← Config template (deprecated, use .env.template_api)
├── .env.template_api     ← API-optimized config template
├── verify_setup.py       ← Setup checker
├── setup_ai_companions_uv.sh ← uv-optimized setup script
│
├── config/               ← Configuration files (e.g., haystack_pipeline.yaml)
├── data/                 ← Regulatory PDFs (EU AI Act, Data Act, CEN/CENELEC standards)
│   ├── cen_cenelec_standards/
│   ├── eu_ai_act/
│   ├── eu_data_act/
│   └── sme_docs_examples/
├── src/                  ← Source code
│   ├── parsers/          # Docling integration
│   ├── vectordb/         # Qdrant client
│   ├── retrieval/        # Haystack components
│   ├── analysis/         # Mistral-powered legal reasoning, Pydantic models
│   ├── observability/    # LangFuse integration
│   └── reporting/        # WeasyPrint/Jinja2 for PDF generation
├── reports/              ← Generated PDF compliance reports
└── tests/                ← Unit, integration, and compliance tests
    ├── unit/
    ├── integration/
    └── compliance/
```

## 🤝 Contributing

We welcome contributions to "The SME AI Auditor" project. Please refer to `CONTRIBUTING.md` for guidelines.

## 🔧 GitHub Collaboration

To collaborate with a friend, follow these steps:

1. Create the GitHub repository and add your friend as a collaborator.
2. Clone the repository:

```bash
git clone https://github.com/<your-org-or-username>/sme_ai_auditor.git
cd sme_ai_auditor
```

3. Create a feature branch:

```bash
git checkout -b feature/<short-description>
```

4. Install dependencies and configure your local `.env` file using `.env.template_api`.
5. Open a pull request against `main` and request a review.
6. GitHub Actions will run the test workflow defined in `.github/workflows/python-app.yml`.

This repo also includes a `CONTRIBUTING.md` document, a standard `.gitignore`, and a PR template in `.github/pull_request_template.md` to make collaboration easier.

## 📄 License

This project is licensed under the [MIT License](LICENSE.md) (to be created).

## 📚 References

[1] Mistral AI. (n.d.). *Pricing*. Retrieved from https://mistral.ai/pricing
[2] PricePerToken. (n.d.). *Best LLM for Coding (2026) — AI Model Rankings*. Retrieved from https://pricepertoken.com/leaderboards/coding
[3] IBM Research. (2026, February). *Docling Security Advisory: CVE-2026-24009*. Retrieved from [Placeholder for actual advisory URL]
[4] WeasyPrint. (n.d.). *Documentation*. Retrieved from https://weasyprint.org/docs/
[5] DeepInfra. (2026, February 2). *Qwen API Pricing Guide 2026: Max Performance on a Budget*. Retrieved from https://deepinfra.com/blog/qwen-api-pricing-2026-guide
[6] Qwen AI. (2024, September 18). *Qwen2.5: A Party of Foundation Models!*. Retrieved from https://qwen.ai/blog?id=qwen2.5
# sme_ai_auditor
