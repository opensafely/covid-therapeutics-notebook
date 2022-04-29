import numpy as np
import pandas as pd

def redact_small_numbers(df, n, rate_column):
    """Takes counts df as input and suppresses low numbers.  Sequentially redacts
    low numbers from numerator and denominator until count of redcted values >=n.
    Rates corresponding to redacted values are also redacted.
    
    Args:
        df: measures dataframe
        n: threshold for low number suppression
        numerator: column name for numerator
        denominator: column name for denominator
        rate_column: column name for rate
    
    Returns:
        Input dataframe with low numbers suppressed
    """
    
    def suppress_column(column):   
        suppressed_count = column[column<=n].sum()
        
        #if 0 dont need to suppress anything
        if suppressed_count == 0:
            pass
        
        else:
            column = column.replace([0, 1, 2, 3, 4, 5],np.nan)

            #while suppressed_count <=n:
                #suppressed_count += column.min()
                #column.iloc[column.idxmin()] = np.nan   
        return column
    
    
    for column in df.columns.drop(rate_column):
        df[column] = suppress_column(df[column])
    
        df.loc[(df[column].isna()), rate_column] = np.nan
    
    return df    