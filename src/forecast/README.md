
# forecasting-module

# SLP-based Forecaster

** SLP forecast
- This module provides forecast of the power exchange (Ptei) based on the standard load profile.  ´
- The forecast inputs are the total aggregated PV forecast of the community (provided by the weather station) as well as the Standrad Load Profile (BDEW).
- level 1 forecast scales up the SLP and calculates the forecasted Ptei.
- level 2 forecast corrects level 1 forecast based on the real measurement values.

** Directories
- Refer to the service directory for the platform integration.
- Refer to the testing directory to test the forecaster with different sets of data.