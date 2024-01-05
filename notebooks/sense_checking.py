import pandas as pd
import numpy as np
import os
from datetime import date, datetime
from IPython.display import display, Markdown

import sys
sys.path.append('../lib/')
from utilities import *


def get_schema(dbconn, table, where, supplementary_table_separator=None, export=False):
    '''Import schema (filtered on 'where') and calculate counts of distinct values and nulls for each column.
    Includes all supplementary tables if specified (additional tables related to the given table with specified separator e.g. `table_der`)
    
    Inputs:
    dbconn (str) 
    table (str)
    where (dict): dict of strings (e.g. "", "WHERE XXX") with keys also strings (e.g. "", "_covid"). 
                    When each where clause is applied, key is appended to column name in output table. 
    supplementary_table_separator (str)
    export (bool): save to csv
    '''
    
    # extract schema for specified table from schema table
    with closing_connection(dbconn) as cnxn:
        table_schema = pd.read_sql("""select * from OpenSAFELYSchemaInformation""", cnxn)
        if supplementary_table_separator:
            schema = pd.read_sql(f"select TableName, ColumnName, ColumnType, MaxLength, IsNullable \
                                  from OpenSAFELYSchemaInformation where TableName = '{table}' OR TableName LIKE '{table}{supplementary_table_separator}%'", cnxn)
        else:
            schema = pd.read_sql(f"select TableName, ColumnName, ColumnType, MaxLength, IsNullable \
                                  from OpenSAFELYSchemaInformation where TableName = '{table}'", cnxn)
   
    # identify tables
    tables = schema["TableName"].unique()
    
    # set up a dict of dataframes to hold results for each table and each 'where' clause
    value_counts = {}
    for t in tables:
        value_counts[t] = {}
        for w in where:
            value_counts[t][w] = pd.DataFrame(columns=[f"Distinct_Values{w}", f"Missing_Values{w}"]) 

    # extract counts of distinct values and nulls for each column and for each 'where' clause
    with closing_connection(dbconn) as cnxn:
        for t in tables:
            for c in schema.loc[schema["TableName"]==t]["ColumnName"]:
                
                for w in where:
                    try: # where looking at supplementary tables, where clause may not work
                        counts = pd.read_sql(f"""select '{t}' as TableName, count(distinct {c}) as Distinct_Values{w},
                                            sum(case when {c} is NULL THEN 1 ELSE 0 END) AS Missing_Values{w},
                                            count(*) as total_rows
                                            from {t}
                                            {where[w]}
                                            """,
                                        cnxn)
                    except: ## if where clause fails, select top 10000 rows as a sample
                        counts = pd.read_sql(f"""with a as (select top 10000 {c}, 
                                                case when {c} is NULL THEN 1 ELSE 0 END AS Missing_Values{w},
                                                count(*) as total_rows
                                                from {t})
                                            select '{t}' as TableName,
                                                count(distinct {c}) as Distinct_Values{w},
                                                sum(Missing_Values{w}) AS Missing_Values{w}
                                                from a
                                            """, 
                                         cnxn)                                            

                    counts = counts.rename(index={0:c})                    
                    value_counts[t][w] = value_counts[t][w].append(counts)

            # compile into one output table per table containing schema + counts
            out = schema.copy().loc[schema["TableName"]==t] 
            
            for w in where:
                out_counts = value_counts[t][w].reset_index().rename(columns={"index":"ColumnName"})
                total_rows = out_counts["total_rows"][0]
                display(Markdown(f"Total rows in {t} {where[w]}: {int(total_rows)}"))
                out_counts = out_counts.drop(columns=["total_rows"])
                out = out.merge(out_counts, on=["TableName","ColumnName"])

            display(out.set_index(["TableName","ColumnName"]))
            
            # save table
            if export:
                try: # replace empty string keys with useful text for filename
                    where["_unfiltered"] = where.pop("")
                except:
                    pass
                where_string =  "_"+("".join(where.keys())) # note keys should start with underscore already
                
                out.to_csv(f"schema_{t}{where_string}.csv", index=False)

    
def counts_of_distinct_values(dbconn, table, columns, threshold=1, where=None, include_counts=True, 
                              sort_values=False, frequency_count=False):
    ''' Return distinct values of a column. 
    Also (optionally) return how many times each value appears, unless there are more distinct values than threshold given, then return no. of values, max and min. 
    Optionally filter using a where clause.
    Row counts are rounded to nearest 5 and any values which appear <=7 times not shown.
    '''
        
    for col in columns:
        display(Markdown(f"### Summary of values in '{col}'"))
        if where:
            display(Markdown(f" **filtered on {where}**"))
        
        # Extract data
        out = simple_sql(dbconn, table, col, where)
            
        
        # convert datetimes to dates
        try:
            out[col] = out[col].dt.date
        except:
            pass
        
        # count nulls
        try:
            missing = out.copy().loc[pd.isnull(out[col])]["row_count"].replace([1,2,3,4,5,6,7],"1-7").reset_index(drop=True)[0]
        except:
            missing = 0
            
        # now exclude nulls
        no_nulls = out.loc[~pd.isnull(out[col])]
        if len(no_nulls)==0:
            display(Markdown("There were no non-null values."))
            continue
        else:
            value_count = len(no_nulls[col])
            
        # suppress and round
        no_nulls, suppressed = suppress_and_round(no_nulls) 
        
           
        
        # For fields with a small range of possible values, list all possible values, with optional counts    
        if (len(no_nulls[col]) <= threshold) or (frequency_count==True):
            display(Markdown(f"There were **{value_count}** different non-missing values"),
                   Markdown(f"and **{missing}** missing values."))
            
            # If all counts are <=7 and therefore suppressed:
            if (len(no_nulls) == 0) or (frequency_count==True):
                # find frequency of each count
                counts = out.groupby('row_count').count()
                counts = (5*((counts/5).round(0))).astype(int)
                counts = counts.reset_index()
                counts = counts.rename(columns={col:"Frequency", "row_count":f"No.of rows per {col}"})
                # suppress unusual counts
                counts = counts.loc[counts["Frequency"]>0]
                display(counts, Markdown("Note: counts with frequencies <=7 are not shown"))    
                
            else:
                if include_counts==True:
                    if sort_values==True:
                        no_nulls = no_nulls.sort_values(by=col, ascending=True).reset_index(drop=True)
                    else:
                        no_nulls = no_nulls.sort_values(by="row_count", ascending=False).reset_index(drop=True)
                    display(no_nulls)
                else:
                    display (no_nulls[[col]].sort_values(by=col).reset_index(drop=True))
                
                # export table to csv
                where_string = ""
                if where:
                    where_string = where.replace(" ", "_")
                no_nulls.to_csv(f"distinct_values_{table}_{col}_{where_string}.csv", index=False)

                # also list how many values were suppressed (if any)
                if suppressed.shape[0] > 0:
                    display(Markdown(f"There were {suppressed.shape[0]} value(s) with <=7 occurrences (each), not shown above."))
        
        
        else: # if lots of values, display a sensible summary of the range and the most common value
            
            # find max and min
            try: # try with native dtype
                minv, maxv = no_nulls[col].min(), no_nulls[col].max()
            except: # if that fails, convert to strings
                minv, maxv = no_nulls[col].astype(str).min(), no_nulls[col].astype(str).max()   
            
            display(Markdown(f"There were **{value_count}** different values, between '{minv}' and '{maxv}' (after removing uncommon values)"),
                   Markdown(f"and **{missing}** missing values."))
            # find most common value (excluding nulls)
            max_count = no_nulls['row_count'].max()
            most_common = no_nulls.loc[no_nulls["row_count"]==max_count][col].reset_index(drop=True)[0] # return one value, even if 2 or more are tied
            display(Markdown(f"The most common value was '{most_common}' with **{max_count}** occurrences"))
    

def compare_two_values(dbconn, tables, columns, join_on=None, threshold=1, where=None, include_counts=True):
    ''' Compare two columns (e.g ints, dates) based on their values
    Optionally filter using a where clause. 
    Row counts are rounded to nearest 5 and any values which appear <=5 times not shown.
    
    Inputs:
    dbconn (str): database connection details
    tables (list): table name(s) to query
    columns (list): name of 2 columns
    join_on (str): name of column to join tables if multiple tables are supplied 
    where (str): where clause e.g. "field_x in('value_1', 'value_2')"
    include_counts (bool): return list of fields without counts if False
    
    Returns: For field_1, field_2 in 'columns', counts how many rows in which each of the following are true: field_1 < field_2,  field_1 == field_2, field_1 > field_2.
    '''                

    if len(tables)>2 or len(columns)>2:
        print("Reduce number of tables/columns to 2 each")
        return
    
    columns_str = ",".join(columns)
    table_str = ",".join(tables)
    
    display(Markdown(f"### Comparison of column values"))
    
    where_clause = ""
    if where:
        where_clause = f"where {where}"
        display(Markdown(f" **filtered on {where}**"))
        
    with closing_connection(dbconn) as cnxn:
        # extract all combinations of dates with counts of their occurrences
        if len(tables)==1:
            out = pd.read_sql(f"select {columns_str}, count(*) as row_count from {table_str} {where_clause} group by {columns_str}", cnxn)
        elif len(tables)==2:
            if join_on == None:
                display("Must supply 'join_on' field for multiple tables")
                return
            out = pd.read_sql(f"""select t1.{columns[0]} as {columns[0]}, t2.{columns[1]} as {columns[1]}, count(*) as row_count 
                          from {tables[0]} t1 LEFT JOIN {tables[1]} t2 ON t1.{join_on} = t2.{join_on}
                          {where_clause} group by {columns_str}
                          """, cnxn)
        else:
            display("Too many tables")
            return
        
    # compare values between the columns
    a = columns[0]
    b = columns[1]
    if out[a].dtype.kind != out[b].dtype.kind:
        # if mixture of int/float and string/object, convert string/object to float
        if (out[a].dtype.kind in 'if') and (out[b].dtype.kind in 'SO'):
            out[b] = out[b].fillna(0).astype(float)
        elif (out[b].dtype.kind in 'if') and (out[a].dtype.kind in 'SO'):
            out[a] = out[a].fillna(0).astype(float)
    
    out["comparison"] = "couldn't compare"
    out["difference"] = 0
    out.loc[out[a] < out[b], "comparison"] = f"{a} < {b}"
    out.loc[out[a] == out[b], "comparison"] = f"{a} = {b}"
    out.loc[out[a] > out[b], "comparison"] = f"{a} > {b}"
    # create new values to show where values were missing and couldn't be compared
    out.loc[pd.isnull(out[a]), "comparison"] = f"{a} is missing"
    out.loc[pd.isnull(out[b]), "comparison"] = f"{b} is missing"
    
    # Calculate median difference where values differ
    # Note need to do slightly differently for dates vs numeric. Currently returns date differences as days.
    # Can also handle dates that are supplied as strings
    days_flag=False
    if (out[a].dtype.kind in 'iuUf') and (out[b].dtype.kind in 'iuUf'):
        # for numeric dtypes:
        out.loc[out[a] < out[b], "difference"] = out[b]-out[a]
        out.loc[out[a] > out[b], "difference"] = out[a]-out[b]
    elif (out[a].dtype.kind in 'SOM') and (out[b].dtype.kind in 'SOM'): 
        # dates or date-like strings 
        try: 
            # coerce strings to dates
            out[a] = pd.to_datetime(out[a], errors="coerce")
            out[b] = pd.to_datetime(out[b], errors="coerce")

            out.loc[(out[a] < out[b]) & (pd.notnull(out[a])) & (pd.notnull(out[b])), "difference"] = (out[b]-out[a]).dt.days
            out.loc[(out[a] > out[b]) & (pd.notnull(out[a])) & (pd.notnull(out[b])), "difference"] = (out[a]-out[b]).dt.days
            out["difference"] = out["difference"].astype(int)
            days_flag = True
        except:
            # if strings are not date-like
            display ("Check dtypes")
            return
    else: 
        display ("Check dtypes")
        return

    # summarise results    
    compared = out.copy().groupby("comparison").agg({"difference":"median", "row_count":"sum"}).reset_index()
    
    # rename column
    if days_flag==True:
        compared = compared.rename(columns={"difference":"median difference (days)"})
    else:
        compared = compared.rename(columns={"difference":"median difference"})
    
    # suppress and round row counts
    compared[["row_count"]], suppressed = suppress_and_round(compared[["row_count"]])
    compared["row_count"] = compared["row_count"].fillna(0).astype(int)
    
    # calculate percentages
    compared["%"] = round(100*compared["row_count"]/compared["row_count"].sum(),1)
    compared["row_count"] = compared["row_count"].replace([0,1,2,3,4,5],"<=5")
    display(compared)
    
    
    
    
def multiple_records(dbconn, table, columns, combinations, where, key_field="patient_id"):
    '''
    For items (e.g. patient_id) appearing multiple times in the data, count how many have multiple different values for each of the given columns or none of the given columns,
    and how many have a different value for fields x and y for each of the (x,y) combinations given in `combinations`.
    
    Inputs:
    dbconn (str): database connection details
    table (str): table name to query
    columns (list): list of fields (strings) in which to count multiple different values appearing for the same key_field value
    combinations (dict): dict of lists where each list has two strings which are looked at together e.g. to identify where a patient has a different value for both of each field.
    where (str): where clause e.g. "field_x in('value_1', 'value_2')
    key_field (str): field to count multiple records (e.g. "patient_id")"
    '''
    
    # create strings for SQL query based on lists of fields provided
    counts = {}
    sums = {}
    for n, c in enumerate(columns):
        counts[n] = f"count(distinct {c}) as {c}"
        sums[n] = f"sum(case when {c}>1 then 1 else 0 end) as {c}"

    text_1 = ", ".join(counts.values())
    text_2 = ", ".join(sums.values())
    text_3 = "<2 AND ".join(columns)

    combos = {}
    for n, c in enumerate(combinations):
        text = ">1 AND ".join(combinations[c])
        name = "_AND_".join(combinations[c])
        text = text + ">1 then 1 else 0 end) AS " + name
        combos[n] = text

    text_4 =  ", SUM(CASE WHEN ".join(combos.values())

    where_clause = ""
    if where:
        where_clause = f"where {where}"
    

    sql = f'''with a as (
        select 
        {key_field} 
        from {table}
        {where_clause}
        group by 
        {key_field} 
        having count(*)>1),

    b as (
        select {key_field} ,
        {text_1}
         from {table}
        where {key_field} in (Select {key_field} from a)
        group by {key_field} 
        )

    select
        count(*) as {key_field}s_with_multiple_records,
        {text_2},
        sum(case when {text_3} <2 then 1 else 0 end) as none_of_these,
        sum(case when {text_4}
        from b 
        '''


    with closing_connection(dbconn) as cnxn:
        out = pd.read_sql(sql, cnxn)
    
    df, suppressed = suppress_and_round(df=out.transpose(), field=0)
    display(Markdown("## Patients appearing multiple times, and the fields in which they have different values in each appearance"))
    if where:
        display(Markdown(f" **filtered on {where}**"))
    display(df.rename(columns={0:"Patient count"}).sort_values(by="Patient count", ascending=False))
    display(Markdown("#### Fields with counts <=5:"),
                     Markdown(", ".join(suppressed.index)))
    
    
def identify_distinct_strings(dbconn, table, columns, where=None, replacement="", split_string='', merge_all=True):
    '''
    List all the different string values in a specified column or columns. 
    Allows splitting up of multiple values within cells e.g. comma-separated
    Can also optionally combine all values across each of the columns supplied.
    
    Inputs:
    dbconn (str): database connection details
    table (str): table name to query
    columns (list): list of fields in table (strings) 
    replacement (str): substring to remove if present in any of the columns specified
    split_string (str): string to use to split strings (e.g " and " or ", ") 
    merge_all (bool): if True, combine distinct strings from all supplied columns, otherwise keep separate
    '''
    cols = ','.join(columns)
    out = simple_sql(dbconn, table, cols, where=where)
    
    results3 = pd.Series(dtype=str)
    for c in columns:
        results = out[[c]].loc[pd.notnull(out[c])]

        results = results[c].str.replace(replacement,"")
        results = results.str.split(split_string, expand=True).drop_duplicates()
        results2 = pd.Series(dtype=str)
        for col in results.columns:
            results2 = results2.append(results[col].drop_duplicates())
        if merge_all == False:
            # display results for each column seperately
            display(results2.drop_duplicates().sort_values())

        else:
            results3 = results3.append(results2, ignore_index=True).drop_duplicates()

    if merge_all == True:    
        display(results3.sort_values().reset_index(drop=True))
        

    

def count_substrings(dbconn, table, columns, where=None, substrings=[], merge_all=True):
    '''
    Count the number of occurrences of substring within specified columns. 
    Can also optionally combine all values across each of the columns supplied.
    
    Inputs:
    dbconn (str): database connection details
    table (str): table name to query
    columns (list): list of fields in table (strings) 
    substring (list): list of strings to count within columns
    merge_all (bool): if True, combine distinct strings from all supplied columns, otherwise keep separate
    '''
    cols = ', '.join(columns)
    out = simple_sql(dbconn, table, cols, where=where)
    
    for substring in substrings:
        results2 = 0
        for c in columns:
            results = out[[c]].loc[pd.notnull(out[c])]
            results = results.loc[results[c].str.contains(substring)]
            results = len(results)
            results = int(10*round(results/10,0))
            
            if merge_all == False:
                # display results for each column seperately
                display(Markdown(f"Number of occurrences of '`{substring}`' in column '{c}': **{results if results>0 else '<=5'}**"))

            else:
                results2 = results2 + results
        
        results2 = 10*round(results2/10,0)
        
        if merge_all == True:    
            display(Markdown(f"Number of occurrences of '{substring}' in columns {cols}: **{results2}**"))
     
    
    
def problem_dates(dbconn, table, columns, where=None, valid_years=['202','21','22'], return_summary_only=False):
    '''
    Takes list of columns in df_in which are date-like strings and indentifies values not resembling dates (e.g. ints, non-numeric strings).
    
    Inputs:
    dbconn (str): database connection details
    table (str): table name to query
    columns (list): list of fields (strings) 
    valid_years (list): list of 2-4-digit years/part-year strings expected in the results e.g. ['21','22','202']
    '''
    # convert lists to strings
    cols = ','.join(columns)
    valid_years = '|'.join(valid_years)  

    # extract data
    df_in = simple_sql(dbconn, table, cols, where=None)
    
    # set up a df for results
    results = pd.DataFrame(columns=["value", "problem", "row_count"])
    
    for n, col in enumerate(columns):
        df = df_in[[col, "row_count"]].copy().fillna("2022-01-01").groupby(col).sum().reset_index()
        df = df.rename(columns={col:"value", "row_count":f"row_count_{str(n)}"})
        
        # contains one or two numeric characters either in isolation or surrounded by non-numeric characters
        df.loc[df["value"].str.contains('^\D*\d?\d?\D*$', regex=True) , "problem"] = "limited numeric characters"      
        
        # doesn't contain a year
        df.loc[~df["value"].str.contains(valid_years, regex=True), "problem"] = "no valid year"

        # starts or ends with something other than a number
        df.loc[df["value"].str.contains('^[^\d]|[^\d]$', regex=True), "problem"] = "starts/ends non-numeric" 
       
        # entirely non-numeric
        df.loc[~df["value"].str.contains('\d', regex=True), "problem"] = "largely or entirely non-numeric"
        
        # starts AND ends with something other than a number
        df.loc[df["value"].str.contains('^[^\d]*[^\d]$', regex=True), "problem"] = "largely or entirely non-numeric" 

        # comprises only a one or two-digit number
        df.loc[df["value"].str.contains('^\d\d?$', regex=True), "problem"] = "entirely numeric"

        temp = df.loc[~pd.isnull(df["problem"])]
        results = results.merge(temp, on=["value", "problem"], how="outer")
    
    results = results.set_index(["problem", "value"])
    results["row_count"] = results.fillna(0).astype(int).sum(axis=1)
    
    
    display(Markdown("### Problem dates across all date-like string fields"))
    if where:
        display(Markdown(f" **filtered on {where}**"))
    display(Markdown(f"In total there were **{len(results)}** problematic date-like values"))
    
    # display counts by type of problem
    summary = results.reset_index().groupby("problem")[["row_count"]].agg({"count","sum"})
    summary.columns = summary.columns.droplevel()
    summary = summary[["count","sum"]].rename(columns={"count":"no_of_different_values", "sum":"row_count"})
    summary,_ = suppress_and_round(summary, field="row_count", keep=True)
    display(summary.replace(0,"<=5"))
    
    if return_summary_only:
        return
    
    else:
        results, _ = suppress_and_round(results[["row_count"]], field="row_count", keep=True)
        results = results.replace(0,"<=5")
        display(results.sort_index())
    
