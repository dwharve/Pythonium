"""
Setup script for Pythonium.

This script is kept for backward compatibility and uses setuptools.
The preferred way to install the package is using pip with pyproject.toml.
"""

from setuptools import setup, find_packages

# Read the contents of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pythonium",
    version="0.1.0",
    author="David Harvey",
    author_email="david@ex.is",
    description="A comprehensive static analysis tool for Python code quality and health",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dwharve/pythonium",
    packages=find_packages(include=["pythonium", "pythonium.*"]),
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "networkx>=2.6.0",
        "radon>=5.1.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=0.900",
        ],
        "mcp": [
            "mcp>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pythonium=pythonium.cli:main",
            "pythonium-mcp=pythonium.mcp_server:main_stdio",
            "pythonium-mcp-sse=pythonium.mcp_server:main_sse",
        ],
        # Register built-in detectors
        "pythonium.detectors": [
            "dead_code=pythonium.detectors.dead_code:DeadCodeDetector",
            "clone=pythonium.detectors.clone:CloneDetector",
            "inconsistent_api=pythonium.detectors.consistency:InconsistentApiDetector",
            "alt_implementation=pythonium.detectors.alternatives:AltImplementationDetector",
            "circular_deps=pythonium.detectors.circular:CircularDependencyDetector",
            "complexity_hotspot=pythonium.detectors.complexity:ComplexityDetector",
            "security_smell=pythonium.detectors.security:SecuritySmellDetector",
            "deprecated_api=pythonium.detectors.deprecated:DeprecatedApiDetector",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
