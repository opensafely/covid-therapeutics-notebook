import pandas as pd
import numpy as np
import pyodbc
import os
from contextlib import contextmanager


# use this to open connection
@contextmanager
def closing_connection(dbconn):
    cnxn = pyodbc.connect(dbconn)
    try:
        yield cnxn
    finally:
        cnxn.close()


def suppress_and_round(df, field="row_count", keep=False):
    ''' In dataframe df with a row_count column, extract values with a row_count <=7 into a separate table, and round remaining values to neareast 5.
    Return df with low values suppressed and all remaining values rounded. Or if keep==True, retain the low value items in the table (but will appear with zero counts)
    '''
    # extract values with low counts into a seperate df
    suppressed = df.loc[df[field] <= 7]
    if keep==False:
        df = df.copy().loc[df[field] > 7]
    else:
        df = df.copy()
    # round counts to nearest 5
    df[field] = (5*((df[field]/5).round(0))).astype(int)
    return df, suppressed


def  simple_sql(dbconn, table, col, where):
    ''' extract data from sql'''
    where_clause = ""
    if where:
        where_clause = f"where {where}"
    
    with closing_connection(dbconn) as cnxn:
        out = pd.read_sql(f"select {col}, count(*) as row_count from {table} {where_clause} group by {col}", cnxn)
    return out