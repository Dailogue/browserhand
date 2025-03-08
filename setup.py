from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="browserhand",
    version="0.1.2",
    author="BrowserHand Team",
    author_email="hangerneil43@gmail.com",
    description="AI-powered browser automation with natural language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Dailogue/browserhand",
    project_urls={
        "Bug Tracker": "https://github.com/Dailogue/browserhand/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "playwright>=1.20.0",
        "langchain-core>=0.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=22.1.0",
            "flake8>=4.0.1",
        ],
        "azure": [
            "langchain-openai>=0.0.1",
        ],
        "openai": [
            "langchain-openai>=0.0.1",
        ],
        "anthropic": [
            "langchain-anthropic>=0.0.1",
        ],
        "all": [
            "langchain-openai>=0.0.1",
            "langchain-anthropic>=0.0.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "browserhand=browserhand.cli:main",
        ],
    },
)
