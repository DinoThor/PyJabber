import os

from setuptools import setup, find_packages
import pyjabber


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    with open(filename) as f:
        lineiter = [line.strip() for line in f]
    return [line for line in lineiter if line and not line.startswith("#")]


setup(
    name="pyjabber",
    version=os.environ.get("VERSION") or pyjabber.__version__,
    author="Aarón Raya Lopez, Manel Soler Sanz",
    author_email="aaron.raya.lopez@gmail.com",
    description="Modern, High-Performance Asyncio XMPP Server, with minimal dependencies.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/DinoThor/PyJabber",
    project_urls={
        "Documentation": "https://pyjabber.readthedocs.io/",
        "Source": "https://github.com/DinoThor/PyJabber",
        "Tracker": "https://github.com/DinoThor/PyJabber/issues",
    },
    keywords=[
        "xmpp", "jabber", "server", "asyncio", 
        "python", "chat", "messaging",
    ],
    packages=find_packages(),
    install_requires=parse_requirements('requirements.txt'),
    include_package_data=True,
    classifiers=[
        "Development Status :: O 5 - Production/Stable",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: XMPP",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "pyjabber=pyjabber.__main__:main",
        ],
    },
)
