from setuptools import setup, find_packages

setup(name='vcst',
      version="0.0.11",
      description="VUnit & cocotb smashed Together",
      author="James Price",
      author_email="jpwice100@gmail.com",
      packages=find_packages(),
      install_requires=["vunit-hdl>=4.4.0,<4.7.0", "cocotb>=1.5.1,<2.0","cocotb-bus>=0.2.1"]
     )
