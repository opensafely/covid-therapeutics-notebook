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


def round_and_suppress(df, field):
    """Another function to apply disclosure control to a column in a dataframe.

    This one rounds all values to the nearest 5, and then replaces any values less than
    or equal to 5 with the string "1-7".
    """
    df[field] = (5 * (df[field] / 5).round()).astype(int)
    df.loc[df[field] <= 5, "n"] = "1-7"



def  simple_sql(dbconn, table, col, where):
    ''' extract data from sql'''
    where_clause = ""
    if where:
        where_clause = f"where {where}"
    
    with closing_connection(dbconn) as cnxn:
        out = pd.read_sql(f"select {col}, count(*) as row_count from {table} {where_clause} group by {col}", cnxn)
    return out



if __name__ == "__main__":
    # A quick test of round_and_suppress
    df = pd.DataFrame({"n": range(15)})
    round_and_suppress(df, "n")
    assert dict(df["n"]) == {
        0: "1-7",
        1: "1-7",
        2: "1-7",
        3: "1-7",
        4: "1-7",
        5: "1-7",
        6: "1-7",
        7: "1-7",
        8: 10,
        9: 10,
        10: 10,
        11: 10,
        12: 10,
        13: 15,
        14: 15,
    }
    print("OK")
