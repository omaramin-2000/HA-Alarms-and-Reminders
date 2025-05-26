from setuptools import setup, find_namespace_packages

setup(
    name="ha-alarms-and-reminders",
    version="0.1.0",
    packages=find_namespace_packages(include=['custom_components.*']),
    install_requires=[
        'voluptuous>=0.13.1',
        'homeassistant>=2024.3.3',
        'aiofiles>=23.2.1',
    ],
)