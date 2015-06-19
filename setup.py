from setuptools import setup

setup(
    name='consul_locks',
    version='0.1',
    description='Distributed locking built on top of Consul.',
    url='http://github.com/oysterbooks/consul_locks',
    license='MIT',
    packages=['python_consul_locks'],
    tests_requires=['mock'],
    install_requires=['python-consul'],
    zip_safe=False
)
