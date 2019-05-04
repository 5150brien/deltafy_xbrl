import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="deltafy_xbrl",
    version="1.0.0",
    author="Devlin O'Brien",
    author_email="dobrien@my.ccsu.edu",
    license="MIT",
    keywords="xbrl financial filings 10-k 10-q sec",
    description="Python library for working with XBRL 10-K/10-Q filings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/5150brien/deltafy_xbrl",
    packages=setuptools.find_packages(),
    install_requires=['lxml'],
    python_requires=">=3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
