# Contributing to Carrot

Thanks for your interest in contributing to Carrot

#### Table Of Contents


[Code of Conduct](#code-of-conduct)

[Testing](#testing)

[Submitting Changes](#submitting-changes)

[Issues](#issues)

[Coding Conventions](#coding-conventions)

## Code of Conduct

This project and everyone participating in it is governed by the [Carrot Code of Conduct](CODE_OF_CONDUCT.md). 
By participating, you are expected to uphold this code. Please report unacceptable behavior to [christopherdavies553@gmail.com](mailto:christopherdavies553@gmail.com).

## Testing

Carrot unit tests are located [here](carrot/tests.py), and the test runner is located [here](run_tests.py). We use [coverage](https://coverage.readthedocs.io) to 
ensure sufficient test coverage. Use the below line to run the unit tests:

```
coverage run run_tests.py
coverage html
```

Please ensure that your contributions do not break the tests and that you update the unit tests as required to cover any new functionality 
you have added


Submitting Changes
---

Please send a GitHub Pull Request to django-carrot with the summary of changes you have made.


## Issues

All issue should be logged in the [Issue tracker](https://github.com/chris104957/django-carrot/issues).


Coding conventions
---

Carrot uses the [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).


