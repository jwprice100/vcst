from setuptools import setup, find_packages

setup(name='vcst',
      version="0.0.11",
      description="VUnit & cocotb smashed Together",
      author="James Price",
      author_email="jpwice100@gmail.com",
      packages=find_packages(),
      install_requires=["vunit-hdl>=5.0.0.dev13", "cocotb>=2.1,<3.0"]
     )
