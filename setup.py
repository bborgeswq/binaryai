"""
AI Day Trader - Setup Script
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="ai-day-trader",
    version="1.0.0",
    author="AI Day Trader",
    description="Autonomous AI-powered day trading system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-day-trader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.10",
    install_requires=[
        "alpaca-trade-api>=3.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "yfinance>=0.2.0",
        "ccxt>=4.0.0",
        "pandas-ta>=0.3.0",
        "scikit-learn>=1.3.0",
        "anthropic>=0.18.0",
        "streamlit>=1.30.0",
        "plotly>=5.18.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "aiohttp>=3.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black",
            "flake8",
            "mypy",
        ],
        "ml": [
            "torch>=2.0.0",
            "xgboost>=2.0.0",
            "lightgbm>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-trader=src.main:main",
        ],
    },
)
