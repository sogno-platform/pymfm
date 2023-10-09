## pymfm examples
pmfm allows you to run multiple examples under three main use cases:

- UC1: (near) real-time operation mode with Rule-Based (RB) control logic
- UC2: scheduling operation mode with Rule_Based (RB) control logic
- UC3: scheduling operation mode with Optimization-Based (OptB) control logic

With the help of scenario_forecast_kit, a wide variety of UC scenarios can be generated. 
Additionally, json samples for the above-mnentioned UCs are already provided under src/exapmples/control/inputs for the comfort of the users.
With the combination of different input paramaters and profiles, it is possible to run multiple UC scenarios as listed below:
> UC1 can be acompanied by a (near) real-time power delivery/reception request acting as a power boundary for the microgrid.
> UC1 and UC2 can handle only a single Community Battery Energy Storage (cbes) unit.
> UC3 can handle multiple storage units including Household Battery Energy Stoarge (hbes) units, ensure a target Final SoC for cbes, deliver/receipt bulk energy from flexible storage units, curtail PV generation output, and limit the net power exchange of the microgrid according to a predefined upper and lower bound profile.



| | | | | | | | | | | |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
|UC|Control logic| |Operation mode| |BES| | |Bulk|PV curtail|Power boundary |
| | | | | | | | | | | |
| |OptB|RB|Real time|Scheduling|Single cbes|cbes&hbes|Final SoC| | | |
|1_1| |x|x| | | | | | | |
|1_2| |x|x| | | | | | |x|
|2| |x| |x|x| | | | | |
|3_1|x| | |x|x| | | | | |
|3_2|x| | |x|x| | | |x| |
|3_3|x| | |x|x| | | | |x|
|3_4|x| | |x|x| | | |x|x|
|3_5|x| | |x|x| |x| | | |
|3_6|x| | |x|x| |x| |x| |
|3_7|x| | |x|x| |x| | |x|
|3_8|x| | |x|x| |x| |x|x|
|3_9|x| | |x|x| | |x| |x|
|3_10|x| | |x|x| | |x|x| |
|3_11|x| | |x|x| | |x| |x|
|3_12|x| | |x|x| | |x|x|x|
|3_13|x| | |x|x| |x|x| | |
|3_14|x| | |x|x| |x|x|x| |
|3_15|x| | |x|x| |x|x| |x|
|3_16|x| | |x|x| |x|x|x|x|
|3_17|x| | |x| |x| | | | |
|3_18|x| | |x| |x| | |x| |
|3_19|x| | |x| |x| | | |x|
|3_20|x| | |x| |x| | |x|x|
|3_21|x| | |x| | |x| | | |
|3_22|x| | |x| | |x| |x| |
|3_23|x| | |x| | |x| | |x|
|3_24|x| | |x| | |x| |x|x|
|3_25|x| | |x| | | |x| | |
|3_26|x| | |x| | | |x|x| |
|3_27|x| | |x| | | |x| |x|
|3_28|x| | |x| | | |x|x|x|
|3_29|x| | |x| | |x|x| | |
|3_30|x| | |x| | |x|x|x| |
|3_31|x| | |x| | |x|x| |x|
|3_32|x| | |x| | |x|x|x|x|






