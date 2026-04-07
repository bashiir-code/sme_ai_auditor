"""
seed_demo_data.py
-----------------
Seeds the Qdrant vector database with representative EU AI Act and
EU Data Act legal text chunks for demo and testing purposes.

Uses the project's own EmbeddingGenerator (Mistral API) and
QdrantClientWrapper to ensure vector consistency.

Usage:
    uv run python seed_demo_data.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.vectordb.embedding_generator import EmbeddingGenerator
from src.vectordb.qdrant_wrapper import QdrantClientWrapper

# ---------------------------------------------------------------
# Demo Legal Chunks — EU AI Act
# ---------------------------------------------------------------
EU_AI_ACT_CHUNKS = [
    {
        "text": "Article 5 — Prohibited AI Practices. The following artificial intelligence practices shall be prohibited: (a) the placing on the market, the putting into service or the use of an AI system that deploys subliminal techniques beyond a person's consciousness or purposefully manipulative or deceptive techniques, with the objective or the effect of materially distorting the behaviour of a person or a group of persons.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 5",
            "parent_section": "Title II — Prohibited AI Practices"
        }
    },
    {
        "text": "Article 5(1)(h) — The use of real-time remote biometric identification systems in publicly accessible spaces for the purposes of law enforcement shall be prohibited, unless and in as far as such use is strictly necessary for one of the following objectives: targeted search for specific victims of abduction, trafficking in human beings or sexual exploitation.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 5",
            "parent_section": "Title II — Prohibited AI Practices"
        }
    },
    {
        "text": "Article 5(1)(c) — AI systems that evaluate or classify natural persons or groups thereof over a certain period of time based on their social behaviour or known, inferred or predicted personal or personality characteristics, with the social score leading to detrimental or unfavourable treatment of certain natural persons or groups (social scoring), shall be prohibited.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 5",
            "parent_section": "Title II — Prohibited AI Practices"
        }
    },
    {
        "text": "Article 6 — Classification Rules for High-Risk AI Systems. An AI system listed in Annex III shall be considered high-risk. A high-risk AI system is an AI system that is intended to be used as a safety component of a product, or the AI system is itself a product covered by the Union harmonisation legislation listed in Annex I.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 6",
            "parent_section": "Title III — High-Risk AI Systems"
        }
    },
    {
        "text": "Article 9 — Risk Management System. A risk management system shall be established and maintained for high-risk AI systems. It shall consist of a continuous iterative process planned and run throughout the entire lifecycle of the high-risk AI system, requiring regular systematic review and updating.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 9",
            "parent_section": "Title III — High-Risk AI Systems"
        }
    },
    {
        "text": "Article 10 — Data and Data Governance. High-risk AI systems which make use of techniques involving the training of AI models with data shall be developed on the basis of training, validation and testing data sets that meet the quality criteria referred to in paragraphs 2 to 5. Training data sets shall be relevant, sufficiently representative, and to the best extent possible, free of errors and complete in view of the intended purpose.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 10",
            "parent_section": "Title III — High-Risk AI Systems"
        }
    },
    {
        "text": "Article 13 — Transparency and Provision of Information to Deployers. High-risk AI systems shall be designed and developed in such a way as to ensure that their operation is sufficiently transparent to enable deployers to interpret a system's output and use it appropriately. Instructions for use shall include the characteristics, capabilities and limitations of performance of the high-risk AI system.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 13",
            "parent_section": "Title III — High-Risk AI Systems"
        }
    },
    {
        "text": "Article 14 — Human Oversight. High-risk AI systems shall be designed and developed in such a way, including with appropriate human-machine interface tools, that they can be effectively overseen by natural persons during the period in which they are in use. Human oversight shall aim to prevent or minimise the risks to health, safety or fundamental rights.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 14",
            "parent_section": "Title III — High-Risk AI Systems"
        }
    },
    {
        "text": "Article 52 — Transparency Obligations for Certain AI Systems. Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural person is informed that they are interacting with an AI system, unless this is obvious from the circumstances and the context of use.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Article 52",
            "parent_section": "Title IV — Transparency Obligations"
        }
    },
    {
        "text": "Annex III — High-Risk AI Systems (Area 1: Biometrics). AI systems intended to be used for biometric identification and categorisation of natural persons. AI systems intended to be used for emotion recognition. AI systems intended for the use of 'real-time' and 'post' remote biometric identification systems.",
        "metadata": {
            "document_source": "eu_ai_act",
            "act_type": "AI_ACT",
            "article_number": "Annex III",
            "parent_section": "Annexes"
        }
    },
]

# ---------------------------------------------------------------
# Demo Legal Chunks — EU Data Act
# ---------------------------------------------------------------
EU_DATA_ACT_CHUNKS = [
    {
        "text": "Article 3 — Obligation to Make Data Accessible. The manufacturer of a connected product shall design and manufacture products in such a way that the data generated by their use are, by default, easily, securely and, where relevant, directly accessible to the user.",
        "metadata": {
            "document_source": "eu_data_act",
            "act_type": "DATA_ACT",
            "article_number": "Article 3",
            "parent_section": "Chapter II — Data Sharing"
        }
    },
    {
        "text": "Article 4 — Right of Users to Access and Use Data. Where data cannot be directly accessed by the user from the product, the data holder shall make available to the user the data generated by its use of a connected product or related service without undue delay, free of charge and, where applicable, continuously and in real-time.",
        "metadata": {
            "document_source": "eu_data_act",
            "act_type": "DATA_ACT",
            "article_number": "Article 4",
            "parent_section": "Chapter II — Data Sharing"
        }
    },
    {
        "text": "Article 23 — Right to Switch Between Data Processing Services. Providers of data processing services shall take all reasonable measures to facilitate the switching process for the customer, enabling them to transition to another data processing service covering the same service type, or to port all data to an on-premise IT infrastructure. The switching period shall not exceed 30 calendar days.",
        "metadata": {
            "document_source": "eu_data_act",
            "act_type": "DATA_ACT",
            "article_number": "Article 23",
            "parent_section": "Chapter VI — Cloud Switching"
        }
    },
    {
        "text": "Article 25 — Interoperability for Data Processing Services. Providers of data processing services shall ensure interoperability with other data processing services. This includes ensuring compatibility of data formats, APIs, and communication protocols in accordance with open standards and specifications.",
        "metadata": {
            "document_source": "eu_data_act",
            "act_type": "DATA_ACT",
            "article_number": "Article 25",
            "parent_section": "Chapter VI — Cloud Switching"
        }
    },
    {
        "text": "Article 31 — Safeguards for Trade Secrets. This Regulation shall not affect the application of Union or national rules on the protection of trade secrets. Any data made available under this Regulation shall be protected where they constitute trade secrets. The data holder may apply appropriate technical and organisational measures to preserve the confidentiality of data constituting trade secrets.",
        "metadata": {
            "document_source": "eu_data_act",
            "act_type": "DATA_ACT",
            "article_number": "Article 31",
            "parent_section": "Chapter X — Safeguards"
        }
    },
]


def main():
    all_chunks = EU_AI_ACT_CHUNKS + EU_DATA_ACT_CHUNKS

    print(f"🚀 Seeding Qdrant with {len(all_chunks)} demo legal chunks...")
    print(f"   AI Act chunks: {len(EU_AI_ACT_CHUNKS)}")
    print(f"   Data Act chunks: {len(EU_DATA_ACT_CHUNKS)}")

    # 1. Initialize components
    print("\n📡 Connecting to Qdrant...")
    qdrant = QdrantClientWrapper()
    qdrant.create_collection_if_not_exists(vector_dimension=1024)
    print("   ✅ Collection ready.")

    # 2. Generate embeddings via Mistral API
    print("\n🧠 Generating embeddings via Mistral API (mistral-embed)...")
    embedder = EmbeddingGenerator()
    texts = [chunk["text"] for chunk in all_chunks]
    vectors = embedder.generate(texts)
    print(f"   ✅ Generated {len(vectors)} vectors (1024-dim each).")

    # 3. Upsert to Qdrant
    print("\n💾 Upserting to Qdrant...")
    qdrant.upsert(chunks=all_chunks, vectors=vectors)
    print(f"   ✅ Upserted {len(all_chunks)} points successfully.")

    # 4. Verify
    print("\n🔍 Verifying with a test search...")
    test_vector = vectors[0]  # Search using Article 5's embedding
    results = qdrant.search(query_vector=test_vector, top_k=3)
    print(f"   ✅ Test search returned {len(results)} results:")
    for r in results:
        article = r.payload.get("article_number", "?")
        score = r.score
        print(f"      • {article} (score: {score:.4f})")

    print("\n🎉 Demo data seeded successfully! The Audit Commander is ready for testing.")


if __name__ == "__main__":
    main()
