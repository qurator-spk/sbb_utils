from io import open
from setuptools import find_namespace_packages, setup

with open('requirements.txt') as fp:
    install_requires = fp.read()

setup(
    name="qurator-sbb-utils",
    version="0.0.1",
    author="The Qurator Team",
    author_email="Kai.Labusch@sbb.spk-berlin.de",
    description="Qurator",
    long_description=open("README.md", "r", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    keywords='Qurator',
    license='Apache',
    url="https://github.com/qurator-spk/sbb_utils",
    packages=find_namespace_packages(include=['qurator']),
    install_requires=install_requires,
    entry_points={
      'console_scripts': [
        "find-entities=qurator.utils.entities:find_entities",
        "csv2sqlite=qurator.utils.csv:to_sqlite",
        "df2sqlite=qurator.utils.pickle:to_sqlite",
        "df-concatenate=qurator.utils.pickle:concatenate",
      ]
    },
    python_requires='>=3.6.0',
    tests_require=['pytest'],
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
