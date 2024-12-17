from setuptools import setup, find_packages
import pyjabber


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    with open(filename) as f:
        lineiter = [line.strip() for line in f]
    return [line for line in lineiter if line and not line.startswith("#")]


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
    install_requires=parse_requirements('requirements.txt'),
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
