#!/usr/bin/env python3
"""Setup script for ai-tools package."""

from setuptools import setup, find_packages
import os

# Read the long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-tools",
    version="1.0.0",
    author="Adam Deleżuch",
    author_email="adamdelezuch89@gmail.com",
    description="Narzędzia AI do dumpowania kodu i implementacji zmian",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-tools",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=5.1",
        "pyperclip>=1.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
            "mypy>=0.990",
        ],
    },
    entry_points={
        "console_scripts": [
            "dump-repo=ai_tools.cli.dump_repo:main",
            "dump-git=ai_tools.cli.dump_git:main",
            "ai-patch=ai_tools.cli.ai_patch:main",
        ],
    },
    include_package_data=True,
)

