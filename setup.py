from setuptools import setup, find_packages

setup(
    name="nba-stats-db",
    version="1.0.0",
    description="A relational NBA statistics database and analytics platform using nba-api, SQLite, and curl_cffi.",
    author="NBA Stats DB Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "nba_stats_db": ["static/*"],
    },
    install_requires=[
        "nba-api>=1.4.1",
        "curl_cffi>=0.7.0",
        "pandas>=1.5.0",
        "tabulate>=0.9.0",
        "Flask>=1.1.2",
    ],
    entry_points={
        "console_scripts": [
            "nba-stats-db=nba_stats_db.cli:main",
        ],
    },
    python_requires=">=3.8",
)
