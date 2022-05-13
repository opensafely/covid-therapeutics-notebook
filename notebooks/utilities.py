import numpy as np
import pandas as pd

def redact_small_numbers(df, n, rate_column):
    """Takes counts df as input and suppresses low numbers.  Sequentially redacts
    low numbers from numerator and denominator until count of redcted values >=n.
    Rates corresponding to redacted values are also redacted.
    
    Args:
        df: measures dataframe
        n: threshold for low number suppression
        rate_column: column name for rate
    
    Returns:
        Input dataframe with low numbers suppressed
    """
    # round to nearest five
    for c in df.columns:
        df[c] = ((df[c]/5).round(0)*5).astype(int)

    def suppress_column(column):   
        suppressed_count = column[column<=n].sum()
        
        #if 0 dont need to suppress anything
        if suppressed_count == 0:
            pass
        
        else:
            
            column = column.replace([0, 5], np.nan)

            #while suppressed_count <=n:
                #suppressed_count += column.min()
                #column.iloc[column.idxmin()] = np.nan   
        return column
    
    if rate_column:
        for column in df.columns.drop(rate_column):
            df[column] = suppress_column(df[column])
        
            df.loc[(df[column].isna()), rate_column] = np.nan
    
    return df    