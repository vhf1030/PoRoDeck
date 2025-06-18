from setuptools import setup, find_packages

setup(
    name="porodeck",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "requests",
        "beautifulsoup4", 
        "pandas",
        "tqdm"
    ]
) 