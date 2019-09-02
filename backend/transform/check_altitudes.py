import pdb
import pandas as pd
import dask
from .utils import fill_col
from ..wrappers import checker


def check_alt_min_max(min_val, max_val):
    try:
        if pd.isnull(min_val) or pd.isnull(max_val):
            return True
        else:
            if int(min_val) > int(max_val):
                return False
            else:
                return True
    except Exception:
        return True


@checker('Data cleaning : altitudes checked')
def check_altitudes(df, selected_columns, synthese_info, calcul):

    """
    A FAIRE QUAND DATA CLEANING DONNEES GEO :
    - if user want to calculate altitudes (checked in front):
        -> if only altitude max column provided, calculates altitude min column
        -> if only altitude min column provided, calculates altitude max column
        -> if both alt_min and max columns provided, calculate missing values
        -> if no altitude column provided, calculates altitude min and max
    """

    """
    - if user doesn't want to calculate altitudes (not checked in front):
        -> if only altitude min column provided, altitude max column = altitude min column
        -> if only altitude max column provided, altitude min column = 0
        -> if both alt_min and max columns provided :
            . does nothing except check if altitude min <= max if min != NA and max!= NA

    replace alt min = 0 if alt min = NA ?
    """

    try:

        user_error = []

        altitudes = []

        for element in list(selected_columns.keys()):
            if element == 'altitude_min' or element == 'altitude_max':
                altitudes.append(element)

        if calcul is False:

            if len(altitudes) == 2:
        
                # check max >= min
                df['temp'] = ''
                df['temp'] = df.apply(lambda x: check_alt_min_max(x[selected_columns['altitude_min']], x[selected_columns['altitude_max']]), axis=1, meta=False)
                df['gn_is_valid'] = df['gn_is_valid'].where(cond=df['temp'].apply(lambda x: fill_col(x), meta=False), other=False)
                df['gn_invalid_reason'] = df['gn_invalid_reason'].where(
                    cond=df['temp'].apply(lambda x: fill_col(x), meta=False),
                    other=df['gn_invalid_reason'] + 'altitude_min ({}) > altitude_max ({}) -- '.format(selected_columns['altitude_min'],selected_columns['altitude_max']))

                n_alt_min_sup = df['temp'].astype(str).str.contains('False').sum()

                if n_alt_min_sup > 0:
                    user_error.append({
                        'code': 'altitude error',
                        'message': 'Des altitude min sont supérieurs à altitude max',
                        'message_data': 'nombre de lignes avec erreurs : {}'.format(n_alt_min_sup)
                    })

        if len(user_error) == 0:
            user_error = ''

        return user_error

    except Exception:
        raise