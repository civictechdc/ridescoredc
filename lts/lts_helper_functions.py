import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns


def is_float(element):
    """
    Set speedlimit with min and max speedlimit to take the more human-readable 
    version of the table and make it more machine-readable   
    """
    try:
        float(element)
        return True
    except ValueError:
        return False
        

def level_rules(df):
    """
    This function takes a dataframe that comes from the human-readable 
    excel version of the 2022 LTS level criteria and returns a version
    of the dataframe that can now be used to classify dc roads according
    to traffic stress.
    """

    max_speedlimit = [x for x in df.columns if is_float(x)]
    non_speedlimit = [x for x in df.columns if not is_float(x)]

    # Build lower bounds for each speedlimit bin
    min_speedlimit = [0.0] + max_speedlimit[:-1]

    # pivot so each row is a critera
    df = (
        df.set_index(non_speedlimit)
          .stack(future_stack=True)
          .rename_axis(index={None: 'maxspeed'})
          .reset_index(name='level')
    )
    df['minspeed'] = df['maxspeed'].apply(
        lambda x: min_speedlimit[max_speedlimit.index(x)]
    )
    
    # Swap last two columns so last column is the level
    cols = list(df.columns)
    cols[-1], cols[-2] = cols[-2], cols[-1]

    df = df[cols]
    return df


def get_levels(
    curr_df,
    curr_roads,
    road_levels,
    value_col=None,
    min_col=None,
    max_col=None,
    ignore_value=False,
    handle_nan_value=False,
    assign_leftovers=False,
    assign_no_speed=True,
):
    """
    This function goes through each ADT, PERBIKELANEWIDTH, or ADJPLREACH and 
    speedlimit option for the general criteria outlined in the next section.
    Given the general criteria, the limiting factor, and speelimit, 
    the LTS is assigned to any road segment matching all the necessary elements
    """
    print(len(curr_roads))
    print('-----')
    for _, row in curr_df.iterrows():
        print(f"{row.get(min_col, 'NA')} --- {row['minspeed']}")

        # Base speed filter
        mask = ((curr_roads['SPEEDLIMITS_OB'] >= row['minspeed']) & (curr_roads['SPEEDLIMITS_OB'] < row['maxspeed']))

        #some general criteria don't break down by ADT, just by speedlimit
        if not ignore_value and value_col is not None:
            if handle_nan_value and pd.isna(row[max_col]):
                mask &= curr_roads[value_col].isna()
            else:
                mask &= ((curr_roads[value_col] >= row[min_col]) & (curr_roads[value_col] < row[max_col]))
        sel = curr_roads[mask]
        print(len(sel))
        # Assign levels
        road_levels.update(dict.fromkeys(sel['index'].values, row['level']))

    # Assign roads with missing speed limits
    if assign_no_speed:
        sel = curr_roads[curr_roads['SPEEDLIMITS_OB'].isna()]
        print('no speedlimit')
        print(len(sel))
        road_levels.update(dict.fromkeys(sel['index'].values, row['level']))

    # Assign leftover roads (better to air on the side of caution than saying a road is safer than it really is)
    if assign_leftovers:
        inds = np.setdiff1d(curr_roads['index'].values, list(road_levels.keys()))
        print('left over')
        print(len(inds))
        sel = curr_roads[curr_roads['index'].isin(inds)]
        road_levels.update(dict.fromkeys(sel['index'].values, row['level']))

    return road_levels