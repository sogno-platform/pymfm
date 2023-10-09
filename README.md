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


You can check if the installation has been successful by trying to import package pymfm into your Python environment.
This import should be possible without any errors.

`import pymfm`


## Documentation

The documentation for the latest pymfm release can be found in folder ./docs and on [this](https://pymfm.fein-aachen.org//) documentation page.

For further information, please also visit the [FEIN Aachen association website](https://www.fein-aachen.org/en/).


## Example Usage

```python

import os
from pymfm.control.utils.data_input import InputData, open_json
from pymfm.control.utils.mode_logic_handler import mode_logic_handler
from pymfm.control.utils import data_output


def main():
    """
    Example usage of scheduling optimization based control.

    This function reads input data from "inputs/scheduling_optimization_based.json" JSON file, 
    processes it using the `mode_logic_handler`, prepares output data, 
    saves output JSON files under "outputs/", 
    and saves visualized data through plots under "outputs/" as SVG files.

    :return: None
    """
    # Get the current directory of the script
    fpath = os.path.dirname(os.path.abspath(__file__))

    # Construct the file path for the input JSON file
    filepath = os.path.join(fpath, "inputs/scheduling_optimization_based.json")

    # Open and load the JSON data from the file
    data = open_json(filepath)

    # Create an InputData object from the loaded data
    input_data = InputData(**data)

    # Execute the control logic handler to process the input data
    mode_logic, output_df, status = mode_logic_handler(input_data)

    # Prepare and save control output data as JSON files
    data_output.prepare_json(mode_logic, output_df, output_directory="outputs/")

    # Visualize and save control output data as SVG plots
    data_output.visualize_and_save_plots(
        mode_logic, output_df, output_directory="outputs/"
    )
if __name__ == "__main__":
    main()
```

For an example that can be run out of the box you can download the example folder from the [pymfm repository](https://git.rwth-aachen.de/acs/public/automation/pymfm/-/tree/main/src/examples).

The file `examples/controle/scheduling_rule_based.py` can be run without installing any solver by running 
```bash
python scheduling_rule_based.py
```

from the `examples/control` folder.

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


