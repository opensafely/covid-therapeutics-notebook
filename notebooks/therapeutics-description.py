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
# # COVID therapeutics dataset in OpenSAFELY-TPP
#
# This notebook displays information about the Therapeutics dataset within the OpenSAFELY-TPP database. It is part of the technical documentation of the OpenSAFELY platform to help users understand the underlying data and guide analyses. 
#
# If you want to see the Python code used to create this notebook, you can [view it on GitHub](https://github.com/opensafely/covid-therapeutics-notebooks/blob/master/notebooks/therapeuticss-description.ipynb).
#
# **Note: all row/patient counts are rounded to the nearest 5 and counts <=7 removed**


# +
## Import libraries

# %load_ext autoreload
# %autoreload 2

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
    multiple_records
)

pd.set_option('display.max_colwidth', 250)


# get the server credentials from environ.txt
dbconn = os.environ.get('FULL_DATABASE_URL', None).strip('"')
# -


# ### Notebook run date

display(Markdown(f"""This notebook was run on {date.today().strftime('%Y-%m-%d')}. The information below reflects the state of this dataset in OpenSAFELY-TPP as at this date. The last final update of the data was on 28/6/2023."""))


# ## Import schema

# +
table = "Therapeutics"
where = {"": None,
         "_non_hospitalised": "where COVID_indication='non_hospitalised'"}

get_schema(dbconn, table, where)

# -

# ## Description of General Fields

# +
columns = ["Diagnosis", "FormName", "Region", "Der_LoadDate", "AgeAtReceivedDate"]
threshold = 50

counts_of_distinct_values(dbconn, table, columns, threshold=threshold, include_counts=False)
counts_of_distinct_values(dbconn, table, columns, threshold=threshold, where="COVID_indication='non_hospitalised'", include_counts=False)

columns = ["COVID_indication", "Intervention", "CurrentStatus", "Count"]

counts_of_distinct_values(dbconn, table, columns, threshold=threshold)
counts_of_distinct_values(dbconn, table, columns, threshold=threshold, where="COVID_indication='non_hospitalised'")

# -

# ## Description of Dates

# +
columns = ["Received", "TreatmentStartDate"]

counts_of_distinct_values(dbconn, table, columns=columns, threshold=threshold, sort_values=True)
counts_of_distinct_values(dbconn, table, columns=columns, threshold=threshold, where="COVID_indication='non_hospitalised'", sort_values=True)

# -

# ### Dates outside expected range

# +
display(Markdown("## Past and future dates"))
for i in [0,1]:
    counts_of_distinct_values(dbconn, table, columns=[columns[i]], threshold=3, where=f"CAST({columns[i]} AS DATE) >'2023-06-28'", sort_values=True) 
    counts_of_distinct_values(dbconn, table, columns=[columns[i]], threshold=3, where=f"COVID_indication='non_hospitalised' AND CAST({columns[i]} AS DATE) >'2023-06-28'", sort_values=True)
    counts_of_distinct_values(dbconn, table, columns=[columns[i]], threshold=3, where=f"CAST({columns[i]} AS DATE) <'2021-12-16'", sort_values=True)
    counts_of_distinct_values(dbconn, table, columns=[columns[i]], threshold=3, where=f"COVID_indication='non_hospitalised' AND CAST({columns[i]} AS DATE) <'2021-12-16'", sort_values=True)

# -

# ### Date comparisons

# +
compare_two_values(dbconn, table, columns=columns, include_counts=True)
compare_two_values(dbconn, table, columns=columns, where="COVID_indication='non_hospitalised'", include_counts=True)

# -

# ## Symptom onset dates and At-Risk groups

# +
columns = ["MOL1_onset_of_symptoms", "SOT02_onset_of_symptoms", "CASIM05_date_of_symptom_onset"]
interventions = ['Molnupiravir', 'Sotrovimab', 'Casirivimab and imdevimab']
thresholds = [50, 50, 1]

for c, i, t in zip(columns, interventions, thresholds):
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=t,)
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=t, where=f"Intervention='{i}'")
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=t, where="COVID_indication='non_hospitalised'")
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=t, where=f"COVID_indication='non_hospitalised' AND Intervention='{i}'")

columns = ["MOL1_high_risk_cohort", "SOT02_risk_cohorts", "CASIM05_risk_cohort"]

for c, i in zip(columns, interventions):
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=50, where=f"Intervention='{i}'")
    counts_of_distinct_values(dbconn, table, columns=[c], threshold=50, where=f"COVID_indication='non_hospitalised' AND Intervention='{i}'")

# -

# ## Distinct risk groups
    
# +
columns = ["MOL1_high_risk_cohort", "SOT02_risk_cohorts", "CASIM05_risk_cohort"]
replacement = "Patients with a "
split_string = ' and '
merge_all = True

identify_distinct_strings(dbconn, table, columns, replacement=replacement, split_string=split_string, merge_all=merge_all)
identify_distinct_strings(dbconn, table, columns, where=f"COVID_indication='non_hospitalised'", replacement=replacement, split_string=split_string, merge_all=merge_all)

# -

# ## Patients with multiple records

# +
counts_of_distinct_values(dbconn, table, columns=["patient_id"], threshold=50)
counts_of_distinct_values(dbconn, table, columns=["patient_id"], threshold=50, where=f"COVID_indication='non_hospitalised'")

# -

# ## Further investigation into patients with multiple records - which fields differ in each record?

# +
fields_of_interest = ["AgeAtReceivedDate", "Received", "Intervention", "CurrentStatus", "TreatmentStartDate", "Region", "MOL1_high_risk_cohort", "SOT02_risk_cohorts", "CASIM05_risk_cohort"]
combinations = {1: ["Intervention", "Received"],
                2: ["Intervention", "TreatmentStartDate"],}

multiple_records(dbconn, table, fields_of_interest, combinations)
multiple_records(dbconn, table, fields_of_interest, combinations, where=f"COVID_indication='non_hospitalised'")

# -
