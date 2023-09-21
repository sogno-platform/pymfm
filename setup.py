import setuptools
from pathlib import Path

long_description = (Path(__file__).parent / "README.md").read_text()


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="pymfm",
    description="A Python framework for ...",
    version="1.0.0",
    author="Institute for Automation of Complex Power Systems (ACS),"
    "E.ON Energy Research Center (E.ON ERC),"
    "RWTH Aachen University",
    author_email="post_acs@eonerc.rwth-aachen.de",
    #url="https://github.com/erdemgumrukcu/datafev",
    #license="MIT",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas==1.5.3",
        "pyomo==6.5.0",
        "matplotlib==3.7.1",
        "scipy==1.11.0",
        "xlsxwriter==3.1.2",
        "pydantic==1.10.9",
        "astral==3.2",
        "sphinx",
        "sphinx-rtd-theme",
    ],
    platforms="any",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        #"License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
    ],
    zip_safe=False,
    python_requires=">=3.8",
)
