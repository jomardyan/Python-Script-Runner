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
    - python setup.py py2app (create macOS app bundle)
"""

from setuptools import setup
import os
import re
import sys

# Ensure we're in a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Warning: Not running in a virtual environment. It's recommended to use a virtual environment.")
    print("You can create one with: python -m venv .venv && source .venv/bin/activate")

# Check if py2app is available
try:
    import py2app
    HAS_PY2APP = True
except ImportError:
    HAS_PY2APP = False

# Read version from runner.py
with open(os.path.join(os.path.dirname(__file__), "runner.py")) as f:
    version_match = re.search(r'__version__ = ["\']([^"\']*)["\']', f.read())
    version = version_match.group(1) if version_match else "6.1.0"

# Read README for long description
readme_file = os.path.join(os.path.dirname(__file__), "README.md")
with open(readme_file, encoding="utf-8") as f:
    long_description = f.read()

# py2app options for macOS app bundle
APP = ['__main__.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,  # Disable for command-line apps to avoid Carbon framework dependency
    'packages': [
        'psutil', 'yaml', 'requests', 'pkg_resources', 'setuptools',
        'sqlite3', 'json', 'logging', 'collections', 'functools'
    ],
    'includes': [
        'jaraco.text', 'pkg_resources.py2_warn', 'setuptools._vendor.jaraco.text'
    ],
    'excludes': ['tkinter', 'unittest', 'pdb', 'pydoc', 'test', 'tests', 'jaraco'],
    'iconfile': None,  # Could add an icon later
    'plist': {
        'CFBundleName': 'Python Script Runner',
        'CFBundleDisplayName': 'Python Script Runner',
        'CFBundleGetInfoString': "Python Script Runner",
        'CFBundleIdentifier': "com.python-script-runner.app",
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'NSHumanReadableCopyright': u"Copyright © 2025, Hayk Jomardyan, MIT License"
    }
}

setup(
    name="python-script-runner",
    version=version,
    description="Production-grade Python script execution engine with comprehensive monitoring, alerting, analytics, and enterprise integrations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hayk Jomardyan",
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
    # py2app configuration
    app=APP if HAS_PY2APP else None,
    data_files=DATA_FILES if HAS_PY2APP else [],
    options={'py2app': OPTIONS} if HAS_PY2APP else {},
    setup_requires=['py2app'] if HAS_PY2APP else [],
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
