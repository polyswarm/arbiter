from setuptools import setup


def parse_requirements():
    with open('requirements.txt', 'r') as f:
        return f.read().splitlines()


setup(
    name='arbiter',
    version='0.1',
    description='Collection of sample arbiter implementations and a basic arbiter framework',
    author='PolySwarm Developers',
    author_email='info@polyswarm.io',
    url='https://github.com/polyswarm/arbiter',
    license='MIT',
    install_requires=parse_requirements(),
    include_package_data=True,
    packages=['arbiter', 'backends'],
    package_dir={
        'arbiter': 'src/arbiter',
        'backends': 'src/backends',
    },
    entry_points={
        'console_scripts': ['arbiter=arbiter.__main__:main'],
    },
)
