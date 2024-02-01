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
# # COVID therapeutics dataset in OpenSAFELY-TPP.
#
# This notebook displays information about the Therapeutics dataset within the OpenSAFELY-TPP database. It is part of the technical documentation of the OpenSAFELY platform to help users understand the underlying data and guide analyses. 
#
# This notebook gives a brief overview of the dataset. There are two additional notebooks looking in more detail at outpatients and inpatients. 
#
# If you want to see the Python code used to create this notebook, you can [view it on GitHub](https://github.com/opensafely/covid-therapeutics-notebook/blob/main/notebooks/therapeutics-description.py).
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
where = {"_total": ""}

get_schema(dbconn, table, where)
# -

# ## Description of General Fields

# +
columns = ["Diagnosis", "FormName", "Region", "Der_LoadDate", "AgeAtReceivedDate"]
threshold = 50

counts_of_distinct_values(dbconn, table, columns, threshold=threshold, include_counts=False)

columns = ["COVID_indication", "Intervention", "CurrentStatus", "Count"]

counts_of_distinct_values(dbconn, table, columns, threshold=threshold)
# -

# ## Description of Dates

# +
columns = ["Received", "TreatmentStartDate"]

counts_of_distinct_values(dbconn, table, columns=columns, threshold=threshold, sort_values=True)
