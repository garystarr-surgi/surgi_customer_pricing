from setuptools import setup, find_packages

setup(
    name='surgi_customer_pricing',
    version='0.0.1',
    description='Customer Pricing Sheet',
    author='SurgiShop',
    author_email='gary.starr@surgishop.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['frappe']
)
