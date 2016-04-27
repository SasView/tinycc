import os
from setuptools import setup,find_packages

from tinycc import __version__

packages = find_packages(exclude=['docs', 'tests*'])
includes = ['include/*.h'] + [
    os.path.join(path[7:], d, '*.h')
    for path, dirs, _  in os.walk('tinycc/include')
    for d in dirs
    ]
package_data = {
    'tinycc': ['*.exe','*.dll', 'lib/*', 'libtcc/*'] + includes,
}
required = []

setup(
    name="tinycc",
    version = __version__,
    description = "TinyCC compiler bundle for windows",
    long_description=open('README.md').read(),
    author = "SasView Collaboration",
    author_email = "management@sasview.org",
    url = "http://www.sasview.org",
    keywords = "ctypes compiler",
    download_url = "https://github.com/SasView/tinycc",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Topic :: Software Development :: Compilers',
    ],
    packages=packages,
    package_data=package_data,
    install_requires = required,
    )
