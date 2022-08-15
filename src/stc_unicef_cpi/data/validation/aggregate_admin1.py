from stc_unicef_cpi.data.validation import get_admin1 as ga1
from stc_unicef_cpi.data.validation import mpi_ophi as ophi

# print("Try3")

# path = "C:/Users/vicin/Desktop/DSSG/Validation Data/ne_10m_admin_1_states_provinces"
# data_admin1 = ga1.get_admin1(path, "Nigeria", res=7,)
# print(data_admin1.shape)

# path = "C:/Users/vicin/Desktop/DSSG/Validation Data"  # /Table-5-Subnational-Results-MPI-2021-uncensored.csv
# data_ophi = ophi.get_validation_data(path, country_name="Nigeria")
# print(data_ophi.shape)


# TO DO: groupby data_admin1 wrt region
# TO DO: merge data_admin1 with data_ophi
