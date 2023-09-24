# pymfm

Python package pymfm is a framework for ..

## Contribution

1. Clone repository via SSH (`git clone git@github.com:erdemgumrukcu/datafev.git`) or clone repository via HTTPS (`git clone https://github.com/erdemgumrukcu/datafev.git`)
2. Open an issue at [https://github.com/erdemgumrukcu/datafev/issues](https://github.com/erdemgumrukcu/datafev/issues)
3. Checkout the development branch: `git checkout development` 
4. Update your local development branch (if necessary): `git pull origin development`
5. Create your feature/issue branch: `git checkout -b issueXY_explanation`
6. Commit your changes: `git commit -m "Add feature #XY"`
7. Push to the branch: `git push origin issueXY_explanation`
8. Submit a pull request from issueXY_explanation to development branch via [https://github.com/erdemgumrukcu/datafev/pulls](https://github.com/erdemgumrukcu/datafev/pulls)
9. Wait for approval or revision of the new implementations.

## Installation

datafev requires at least the following Python packages:
- matplotlib>=3.7.1
- scipy>=1.11.0
- astral>=3.2
- pandas>=1.5.3
- pyomo>=6.5.0
- xlsxwriter >= 3.1.2
- pydantic >= 1.10.9

as well as the installation of at least one mathematical programming solver for convex and/or non-convex problems, which is supported by the [Pyomo](http://www.pyomo.org/) optimisation modelling library.
We recommend one of the following solvers:

- [Gurobi (gurobipy)](https://www.gurobi.com/products/gurobi-optimizer/) (default)
- [SCIP (Solving Constraint Integer Programs)](https://scipopt.org/)

If all the above-mentioned dependencies are installed, you should be able to install package datafev via [PyPI](https://pypi.org/) (using Python 3.X) as follows:

`pip install pymfm`

or:

`pip install -e '<your_path_to_pymfm_git_folder>/src'`

or:

`<path_to_your_python_binary> -m pip install -e '<your_path_to_pymfm_git_folder>/src'`

Another option rather than installing via PyPI would be installing via setup.py:

`py <your_path_to_pymfm_git_folder>/setup.py install`

or:

`pyton <your_path_to_pymfm_git_folder>/setup.py install`


You can check if the installation has been successful by trying to import package datafev into your Python environment.
This import should be possible without any errors.

`import pymfm`


## Documentation

The documentation for the latest datafev release can be found in folder ./docs and on [this](https://datafev.fein-aachen.org//) GitHub page.

For further information, please also visit the [FEIN Aachen association website](https://fein-aachen.org/en/projects/datafev/).


## License

The datafev package is released by the Institute for Automation of Complex Power Systems (ACS), E.ON Energy Research Center (E.ON ERC), RWTH Aachen University under the [MIT License](https://opensource.org/licenses/MIT).


## Contact

- Amir Ahmadifar, M.Sc. <aahmadifar@eonerc.rwth-aachen.de>
- Erdem Gumrukcu, M.Sc. <erdem.guemruekcue@eonerc.rwth-aachen.de>
- Aytug Yavuzer, B.Sc. <aytug.yavuzer@rwth-aachen.de>
- Univ.-Prof. Antonello Monti, Ph.D. <post_acs@eonerc.rwth-aachen.de>

[Institute for Automation of Complex Power Systems (ACS)](http://www.acs.eonerc.rwth-aachen.de) \
[E.ON Energy Research Center (E.ON ERC)](http://www.eonerc.rwth-aachen.de) \
[RWTH Aachen University, Germany](http://www.rwth-aachen.de)


<img src="https://www.eonerc.rwth-aachen.de/global/show_picture.asp?id=aaaaaaaaaakevlz"/>

