from setuptools import setup, find_packages

setup(
    name="agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic==0.3.11",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-dotenv",
        "gitpython",
        "pytest",
    ],
    entry_points={
        "console_scripts": [
            "agent=src.cli:main",
        ],
    },
) 