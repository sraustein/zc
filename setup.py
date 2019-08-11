from setuptools import setup, find_packages

setup(
    name                                = "zc",
    version                             = "1.0",
    packages                            = find_packages(),
    scripts                             = ["zc", "git-remote-only"],
    install_requires                    = ["dnspython", "GitPython"],

    author                              = "Rob Austein",
    author_email                        = "sra@hactrn.net",

    url                                 = "https://git.hactrn.net/sra/zc",
    description                         = "A DNS zone compiler",
    #long_description                   = open("README.md").read(),
    #long_description_content_type      = "text/markdown",

    classifiers = [
        "License :: OSI Approved :: ISC License"
    ],
)
