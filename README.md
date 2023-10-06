# pymfm

Python package pymfm is a framework for microgrid flexibility management. The framework allows to develop scenario-oriented management strategies for community microgrids based on optimization and rule-based algorithms in both (near) real-time and scheduling operation modes by coordinating battery storage and photovoltaic units. Furthermore, this framework can be used to create realistic forecast profiles based on standard load and PV generation profiles. Its target users are researchers in the field of smart grid applications and the deployment of operational flexibility for renewable energy communities.

## Contribution

1. Clone repository via SSH (`git@git.rwth-aachen.de:acs/public/automation/pymfm.git`) or clone repository via HTTPS (`https://git.rwth-aachen.de/acs/public/automation/pymfm.git`)
2. Open an issue at [https://git.rwth-aachen.de/acs/public/automation/pymfm/-/issues](https://git.rwth-aachen.de/acs/public/automation/pymfm/-/issues)
3. Checkout the development branch: `git checkout dev` 
4. Update your local development branch: `git pull origin dev`
5. Create your feature/issue branch: `git checkout -b issueXY_explanation`
6. Commit your changes: `git commit -m "Add feature #XY"`
7. Push to the branch: `git push origin issueXY_explanation`
8. Submit a merge request from issueXY_explanation to development branch via [https://git.rwth-aachen.de/acs/public/automation/pymfm/-/merge_requests](https://git.rwth-aachen.de/acs/public/automation/pymfm/-/merge_requests)
9. Wait for approval or revision of the new implementations.

## Installation

pymfm requires at least the following Python packages:
- matplotlib>=3.7.1
- scipy>=1.11.0
- astral>=3.2
- pandas>=1.5.3
- pyomo>=6.5.0
- xlsxwriter >= 3.1.2
- pydantic >= 1.10.9, < 2.0

as well as the installation of at least one mathematical programming solver for convex and/or non-convex problems, which is supported by the [Pyomo](http://www.pyomo.org/) optimisation modelling library.
We recommend one of the following solvers:

- [Gurobi (gurobipy)](https://www.gurobi.com/products/gurobi-optimizer/) (default)
- [SCIP (Solving Constraint Integer Programs)](https://scipopt.org/)

To install pymfm and all its python dependencies, you can:

`pip install pymfm`

or:

`<path_to_your_python_binary> -m pip install -e '<your_path_to_pymfm_git_folder>'`


You can check if the installation has been successful by trying to import package datafev into your Python environment.
This import should be possible without any errors.

`import pymfm`


## Documentation

The documentation for the latest datafev release can be found in folder ./docs and on [this](https://pymfm.fein-aachen.org//) GitHub page.

For further information, please also visit the [FEIN Aachen association website](https://fein-aachen.org/en/projects/pymfm/).


## License

The pymfm package is released by the Institute for Automation of Complex Power Systems (ACS), E.ON Energy Research Center (E.ON ERC), RWTH Aachen University under the [MIT License](https://opensource.org/licenses/MIT).


## Contact

- Amir Ahmadifar, M.Sc. <aahmadifar@eonerc.rwth-aachen.de>
- Erdem Gumrukcu, M.Sc. <erdem.guemruekcue@eonerc.rwth-aachen.de>
- Florian Oppermann, M.Sc. <florian.oppermann@eonerc.rwth-aachen.de>
- Aytug Yavuzer, B.Sc. <aytug.yavuzer@eonerc.rwth-aachen.de>
- Univ.-Prof. Antonello Monti, Ph.D. <post_acs@eonerc.rwth-aachen.de>

[Institute for Automation of Complex Power Systems (ACS)](http://www.acs.eonerc.rwth-aachen.de) \
[E.ON Energy Research Center (E.ON ERC)](http://www.eonerc.rwth-aachen.de) \
[RWTH Aachen University, Germany](http://www.rwth-aachen.de)


<img src="https://www.eonerc.rwth-aachen.de/global/show_picture.asp?id=aaaaaaaaaakevlz"/>

