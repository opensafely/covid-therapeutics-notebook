# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# + [markdown]
# # COVID therapeutics dataset in OpenSAFELY-TPP, filtered on Hospitalised patients.
#
# This notebook displays information about the Therapeutics dataset within the OpenSAFELY-TPP database. It is part of the technical documentation of the OpenSAFELY platform to help users understand the underlying data and guide analyses. 
#
# If you want to see the Python code used to create this notebook, you can [view it on GitHub](https://github.com/opensafely/covid-therapeutics-notebook/blob/main/notebooks/therapeutics-description-inpatients.py).
#
# **Note: all row/patient counts are rounded to the nearest 5 and counts 1-7 and in some cases <=7 removed**


# +
import pyodbc
import os
import pandas as pd
import numpy as np
from datetime import date, datetime
from IPython.display import display, Markdown

import sys
sys.path.append('../lib/')
from sense_checking import (
    compare_two_values,
    counts_of_distinct_values,
    get_schema,
    identify_distinct_strings,
    multiple_records,
)

pd.set_option('display.max_colwidth', 250)


# get the server credentials from environ.txt
dbconn = os.environ.get('FULL_DATABASE_URL', None).strip('"')
# -


# ### Notebook run date

display(Markdown(f"""This notebook was run on {date.today().strftime('%Y-%m-%d')}. The information below reflects the state of this dataset in OpenSAFELY-TPP as at this date. The last final update of the data was on 28/6/2023."""))

# +
## Import schema

table = "Therapeutics"
where = {"_hospitalised": "where COVID_indication IN ('hospitalised_with','hospital_onset')"}

get_schema(dbconn, table, where)
# -

# ## Description of General Fields

# +
columns = ["Diagnosis", "FormName", "Region", "Der_LoadDate", "AgeAtReceivedDate"]
threshold = 50

counts_of_distinct_values(dbconn, table, columns, threshold=threshold, where="COVID_indication IN ('hospitalised_with','hospital_onset')", include_counts=False)

columns = ["COVID_indication", "Intervention", "CurrentStatus", "Count"]

counts_of_distinct_values(dbconn, table, columns, threshold=threshold, where="COVID_indication IN ('hospitalised_with','hospital_onset')")
# -

# ## Description of Dates

# +
columns = ["Received", "TreatmentStartDate"]

counts_of_distinct_values(dbconn, table, columns=columns, threshold=threshold, where="COVID_indication IN ('hospitalised_with','hospital_onset')", sort_values=True)

# -

# ### Dates outside expected range

# +
display(Markdown("## Past and future dates"))
for i in [0,1]:
    counts_of_distinct_values(dbconn, table, columns=[columns[i]], threshold=3, where=f"COVID_indication IN ('hospitalised_with','hospital_onset') AND CAST({columns[i]} AS DATE) >'2023-06-28'", sort_values=True)

# -


# ### Date comparisons

# +
columns = ["Received", "TreatmentStartDate"]

compare_two_values(dbconn, [table], columns=columns, where="COVID_indication IN ('hospitalised_with','hospital_onset')", include_counts=True)
# -

# ## Symptom onset dates and At-Risk groups
#
# Not populated as indicated above

# # Patients with multiple records

counts_of_distinct_values(dbconn, table, columns=["patient_id"], threshold=50, where=f"COVID_indication IN ('hospitalised_with','hospital_onset')", frequency_count=True)

# ## Further investigation into patients with multiple records - which fields differ in each record?

# +
fields_of_interest = ["AgeAtReceivedDate", "Received", "Intervention", "CurrentStatus", "TreatmentStartDate", "Region", "MOL1_high_risk_cohort", "SOT02_risk_cohorts", "CASIM05_risk_cohort"]
combinations = {1: ["Intervention", "Received"],
                2: ["Intervention", "TreatmentStartDate"],}

multiple_records(dbconn, table, fields_of_interest, combinations, where=f"COVID_indication IN ('hospitalised_with','hospital_onset')")
