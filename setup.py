from setuptools import setup, find_packages

setup(
    name='pyjabber',
    version='0.1.5',
    author='Aarón Raya  ',
    author_email='aaron.raya.lopez@gmail.com',
    description='A Python XMPP server',
    long_description=open('README.rst').read(),
    long_description_content_type='text/x-rst',
    url='https://github.com/DinoThor/PyJabber',
    packages=find_packages(),
    install_requires=[
        "aiohttp==3.9.5",
        "loguru==0.7.2",
        "xmlschema==3.3.0"
    ],
    include_package_data=True,

    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'pyjabber=pyjabber:main',
        ],
    },
)