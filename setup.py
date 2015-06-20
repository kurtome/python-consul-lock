from setuptools import setup

setup(
    name='consul-lock',
    version='0.1.3',
    description='Distributed locking built on top of Consul.',
    url='http://github.com/oysterbooks/python-consul-lock',
    packages=['consul_lock'],
    tests_requires=['mock'],
    install_requires=['python-consul'],
    zip_safe=True
)
