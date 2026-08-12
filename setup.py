from setuptools import setup
from pathlib import Path

README = Path(__file__).with_name('README.md').read_text(encoding='utf8')

setup(
    name='variation-assigner',
    version='0.1.0',
    description='Deterministic variation assignment SDK',
    long_description=README,
    long_description_content_type='text/markdown',
    packages=['variation_assigner'],
    python_requires='>=3.8',
    author='Marco Aragon',
    author_email='you@example.com',
    url='https://example.com/variation-assigner',
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
