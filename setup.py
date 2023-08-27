from setuptools import setup

setup(
    name='slideshow-framework',
    version='0.1',
    packages=['slideshow', 'slideshow.shells'],
    url='https://github.com/jonhare/slideshow-framework',
    license='MIT',
    author='Jonathon Hare',
    author_email='jsh2@soton.ac.uk',
    description='Python framework for building interactive slide presentations',
    install_requires=[
        'pillow>=10',
        'kivy>=2.2',
        'pygments>=2',
        'opencv-python>=4.8',
        'gestures4kivy>=0.1.3'
    ]
)
