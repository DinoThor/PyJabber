import sys

from setuptools import setup, find_packages
import pyjabber

requires=[
    "aiohttp==3.10.4",
    "click==8.1.7",
    "cryptography==43.0.1",
    "loguru==0.7.2",
    "pyyaml~=6.0.2",
]
if sys.platform in ("win32", "cygwin"):
    requires.append("winloop^=0.1.7")
else:
    requires.append("uvloop^=0.21.0")

setup(
    name="pyjabber",
    version=pyjabber.__version__,
    author="Aarón Raya Lopez, Manel Soler Sanz",
    author_email="aaron.raya.lopez@gmail.com",
    description="A Python XMPP server",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/DinoThor/PyJabber",
    packages=find_packages(),
    install_requires=requires,
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "pyjabber=pyjabber.__main__:main",
        ],
    },
)
