from setuptools import setup, find_packages

setup(
    name="threadly-sdk",
    version="0.1.0",
    description="Memory-based journaling and reflection SDK",
    author="Tanay Bhalerao",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "openai",
        "faiss-cpu",
        "numpy",
        "sqlalchemy",
        "python-dotenv",
        "tenacity"
    ],
    python_requires=">=3.8"
)
