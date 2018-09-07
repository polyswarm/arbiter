from setuptools import setup


setup(
    name='arbiter',
    version='0.1',
    description='Collection of sample arbiter implementations and a basic arbiter framework',
    author='PolySwarm Developers',
    author_email='info@polyswarm.io',
    url='https://github.com/polyswarm/arbiter',
    license='MIT',
    include_package_data=True,
    packages=['arbiter', 'db'],
    package_dir={
        'arbiter': 'src/arbiter',
        'db': 'src/db'
    },
    entry_points={
        'console_scripts': [
                'arbiter=arbiter.__main__:main', 'generate_verbatim=db.__main__:main'
            ],
    },
)
