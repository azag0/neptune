from setuptools import setup, find_packages


setup(
    name='knitj',
    version='0.1',
    description='Alternative Jupyter front-end',
    author='Jan Hermann',
    author_email='dev@janhermann.cz',
    url='https://github.com/azag0/knitj',
    packages=find_packages(),
    package_data={'knitj': [
        'client/static/*',
        'client/templates/*',
    ]},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: IPython',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
    ],
    license='Mozilla Public License 2.0',
    install_requires=[
        'watchdog',
        'jupyter-client',
        'ansi2html',
        'misaka',
        'aiohttp',
        'pygments',
        'Jinja2',
        'beautifulsoup4',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': ['knitj = knitj.cli:main']
    },
)
