import setuptools

setuptools.setup(
    name="cdk_pleiades",
    version="0.0.1",
    description="A CDK Python app for Pleiades",
    author="author",
    package_dir={"": "cdk_pleiades"},
    packages=setuptools.find_packages(where="cdk_pleiades"),
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    python_requires=">=3.6",
)