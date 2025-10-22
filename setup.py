#!/usr/bin/env python
"""
Setup script for Python Script Runner

Provides backward compatibility with older build systems and package managers.
For modern Python projects, use: pip install -e .

Supports:
    - python setup.py develop (development mode)
    - python setup.py install (direct installation)
    - python setup.py test (run tests)
    - python setup.py sdist (create source distribution)
    - python setup.py bdist_wheel (create wheel distribution)
"""

from setuptools import setup
import os
import re

# Read version from runner.py
with open(os.path.join(os.path.dirname(__file__), "runner.py")) as f:
    version_match = re.search(r'__version__ = ["\']([^"\']*)["\']', f.read())
    version = version_match.group(1) if version_match else "6.1.0"

# Read README for long description
readme_file = os.path.join(os.path.dirname(__file__), "README.md")
with open(readme_file, encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="python-script-runner",
    version=version,
    description="Production-grade Python script execution engine with comprehensive monitoring, alerting, analytics, and enterprise integrations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Python Script Runner Contributors",
    license="MIT",
    url="https://github.com/jomardyan/Python-Script-Runner",
    project_urls={
        "Documentation": "https://github.com/jomardyan/Python-Script-Runner#readme",
        "Source": "https://github.com/jomardyan/Python-Script-Runner",
        "Bug Tracker": "https://github.com/jomardyan/Python-Script-Runner/issues",
    },
    py_modules=["runner", "__main__"],
    python_requires=">=3.6",
    install_requires=[
        "psutil>=5.9.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dashboard": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "websockets>=12.0",
        ],
        "export": [
            "pyarrow>=13.0.0",
            "scikit-learn>=1.3.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.900",
        ],
        "docs": [
            "mkdocs>=1.4.0",
            "mkdocs-material>=9.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "python-script-runner=runner:main",
        ],
    },
    keywords=[
        "python",
        "script",
        "runner",
        "monitoring",
        "alerting",
        "analytics",
        "performance",
        "ci-cd",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
    ],
)
