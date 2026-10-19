# My custom Static Site Generator

This project contains the command line utility I use to generate my personal
blog.

## Setup (why would you?)

In case someone wants to try this out for themselves, here are the instructions:

- You will need a working installation of Python 3 (Tested on 3.11, probably
won't run on anything below 3.10).
- The easiest way to install the program is by invoking [the Just task
runner](https://github.com/casey/just) in the project directory: `just install`.
    - If you don't want to do that, you can look inside `Justfile` and perform
    the `install` recipe by hand.
- Assuming a conventional Unix-like environment, this should create an `ssg`
command for you.

### Dependencies

The `requirements.txt` file should contain all required python packages with
their tested versions. You will also need a working
[Pandoc](https://pandoc.org/index.html) installation at runtime.

## Features, usage and more

- Aditional information will be available elsewhere later.
