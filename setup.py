from glob import glob
from setuptools import setup, find_packages

version = '0.1.0'
long_desc = 'Simple Python image captioning'
dist_name = 'pycaptioner'

setup(
    name=dist_name,
    packages=['pycaptioner'],
    package_dir={'pycaptioner': 'pycaptioner'},
    package_data={'pycaptioner':  ['data/borders/*']},
    version=version,
    install_requires=['pillow'],
    extras_require={},
    scripts=glob('scripts/*'),
    author="Dan Gunter",
    author_email="dkgunter@lbl.gov",
    maintainer="Dan Gunter",
    url="https://github.com/dangunter/cpt/",
    license="MIT",
    description="Simple Python image captioning library and CLI",
    long_description=long_desc,
    keywords=["caption", "image"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
)
