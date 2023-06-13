**Rule_based and Optimiser_logics**  

**inputs/balancer_input_offline.json**

*uc_name* 
- If uc_name=UC1_rule_based_offline, Rule based balancer with forecast values (only UC1 and the non-optimal schedule)
- If uc_name=optimiser, Optimisation-based balancer (UC1,3,4--with_final_SoC and bulk can be added with boolean entries)


*uc_start*
- starting time for the balancing mechanism (schedule/setpoint output is calculated from this timestamp onward)

*uc_end*
- ending time for the balancing mechanism (schedule/setpoint output is calculated till this timestamp)

*bulk*
1. with_bulk - boolean value to activate the optimization in presence of bulk energy window 
2. bulk_start - starting time of the bulk window
3. bulk_end - ending time of the bulk window 
4. bulk_energy_kWh - Amount of energy to be delivered/received (Kwh)
    - Negative bulk_energy shows the delivery of energy and therefore bulk export 
    - Positive bulk_energy shows the reception of energy and therefore bulk import
     
- bulk_start and bulk_end should always be in the acceptable range, i.e., between uc_start and uc_end
- Entries 2-4 are mandatory but irrelevant when with_bulk=false

*P_net*
1. time - timestamp of forecast input to the balancer in datetime-timezone format 
2. P_req_kW - requested power exchange in kW (not needed!)
3. P_net_kW  - forecast values 

*battery_specs:*
1. id - the id of the battery
2. bat_type - the type of the battery 
    - If bat_type=cbes, the battery type is comunity battery energy storage
    - If bat_type=hbes, the battery type is household battery energy storage
3. with_final_SoC - boolean value to activate optimization including the constraint for the final state of charge of the battery
4. initial_SoC - initial state of charge of the battery in percentage at UC_start
5. final_SoC - final state of charge of the battery in percentage at UC_end 
6. P_dis_max_kW - max dischargable power in kW
7. P_ch_max_kW - max chargable power in kW
8. min_SoC - minimum state of charge of the battery in percentage
9. max_SoC - maximum state of charge of the battery in percentage
10. bat_capacity - full capacity of battery assets (100% SOF) in kWh
11. ch_efficiency - charging efficiency of the battery (between 0 and 1)
12. dis_efficiency - discharging efficiency of the battery (between 0 and 1)

- initial_SoC and final_SoC should always be in the acceptable range, i.e., between min_SoC and max_SoC
- final_SoC is mandatory but irrelevant when with_final_SoC=false

**Outputs objects (results/output.json) :**

Includes P_bat_n (for every n∈N) -  setpoints for the batteries

*output*
- timestamp - timestamp of P_bat_n output  
- values - P_bat_n (for every n∈N) setpoints in kW


