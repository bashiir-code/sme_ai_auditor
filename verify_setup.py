import os
import sys
from importlib import metadata
from packaging import version
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

def check_python():
    print("🔍 Checking Python Environment...")
    if sys.version_info >= (3, 9):
        print(f"  ✅ Python version is {sys.version_info.major}.{sys.version_info.minor}")
    else:
        print(f"  ❌ Python version must be 3.9 or higher. Found: {sys.version_info.major}.{sys.version_info.minor}")
        return False
    return True

def check_env_vars():
    print("\n🔍 Checking Environment Variables (API-Optimized)...")
    # Emphasizing API keys since local LLMs are not being used
    required_vars = {
        "MISTRAL_API_KEY": "Required for the Mistral AI API Auditor Brain",
        "QDRANT_URL": "Required for the Vector Database",
        "LANGFUSE_PUBLIC_KEY": "Required for Observability & Auditability",
        "DOCLING_PDF_BACKEND": "Required to prevent 16GB RAM OOM crashes"
    }
    
    all_passed = True
    for var, reason in required_vars.items():
        if os.getenv(var):
            print(f"  ✅ {var} is set.")
        else:
            print(f"  ❌ {var} is MISSING. ({reason})")
            all_passed = False

    # Check if local configs are mistakenly left over
    if os.getenv("OLLAMA_BASE_URL"):
        print("  ⚠️  Notice: OLLAMA_BASE_URL is present, but system is designed for API-based inference.")

    return all_passed

def check_packages():
    print("\n🔍 Checking Required Packages & Security Patches...")
    
    # Core packages and their required versions based on the 2026 Sovereign Stack
    packages = {
        "haystack-ai": "2.10.0",
        "qdrant-client": None,
        "mistralai": None,
        "langfuse": None,
        "pydantic": "2.10.0",
        "docling": "2.84.0", # Critical to patch CVE-2026-24009
        "weasyprint": None,
        "jinja2": None
    }

    all_passed = True
    for pkg, min_version in packages.items():
        try:
            pkg_version = metadata.version(pkg)
            if min_version:
                if version.parse(pkg_version) >= version.parse(min_version):
                    print(f"  ✅ {pkg} (v{pkg_version}) - Meets requirement >= {min_version}")
                else:
                    print(f"  ❌ {pkg} (v{pkg_version}) - Update required! Must be >= {min_version}")
                    all_passed = False
            else:
                print(f"  ✅ {pkg} (v{pkg_version}) is installed.")
        except metadata.PackageNotFoundError:
            print(f"  ❌ {pkg} is NOT installed.")
            all_passed = False

    return all_passed

def main():
    print("=======================================================")
    print("🚀 SME AI Auditor - API Stack Verification (2026)")
    print("=======================================================")
    
    py_ok = check_python()
    env_ok = check_env_vars()
    pkg_ok = check_packages()

    print("\n=======================================================")
    if py_ok and env_ok and pkg_ok:
        print("🎉 ALL CHECKS PASSED!")
        print("Your Sovereign Tech Stack is secure, API-ready, and optimized.")
    else:
        print("⚠️  SOME CHECKS FAILED. Please review the errors above.")
        print("💡 Tip: Make sure you ran 'source .venv/bin/activate' and loaded your .env file.")
    print("=======================================================")

if __name__ == "__main__":
    main()