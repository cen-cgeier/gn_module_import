import pdb
import pandas as pd
import dask
from .utils import fill_col
from ..wrappers import checker


def check_count_min_max(min_val, max_val):
    try:
        if int(min_val) > int(max_val):
            return False
        else:
            return True
    except Exception:
        return True


def check_missing_count_max(min_val, max_val):
    try:
        if pd.isnull(max_val):
            if int(min_val) > 0:
                return min_val
        else:
            return max_val
    except Exception:
        return max_val


"""
def check_negative(val):
    try:
        if pd.to_numeric(val) < 0:
            return False
        else:
            return True
    except Exception:
        return True
"""


@checker('Data cleaning : counts checked')
def check_counts(df, selected_columns, synthese_info, def_count_val):

    """
    - in all cases :
        -> count_min = def_count_val if NA
        -> if count_min < 0 or count_max < 0 : send error
    - if only count_min column is provided : count_max column = count_min column
    - if only count_max column is provided : count_min column = default count_min value (defined in parameters)
    - if both count_min and max columns are provided :
        -> if count_max = NA : count_max = count_min if count_min > 0
        -> checks if count_min <= count_max
    """

    try:
            
        user_error = []

        counts = []

        for element in list(selected_columns.keys()):
            if element == 'count_min' or element == 'count_max':
                counts.append(element)


        """
        Removed because negative values are already returned as invalid integer in check_types

        if len(counts) > 0:

            for count in counts:

                # count_min = def_count_val if NA:
                if count == 'count_min':
                    df[selected_columns[count]] = df[selected_columns[count]].replace(pd.np.nan,str(def_count_val))

                # if count_min < 0 or count_max < 0 : send error:
                df['temp'] = ''
                df['temp'] = df[selected_columns[count]].apply(lambda x: check_negative(x))
                df['gn_is_valid'] = df['gn_is_valid'].where(cond=df['temp'].apply(lambda x: fill_col(x)), other=False)
                df['gn_invalid_reason'] = df['gn_invalid_reason'].where(
                    cond=df['temp'].apply(lambda x: fill_col(x)),
                    other=df['gn_invalid_reason'] + 'invalid {} in {} column : value < 0 -- '.format(count, selected_columns[count]))

                n_negative_count = df['temp'].astype(str).str.contains('False').sum()

                if n_negative_count > 0:
                    user_error.append({
                        'code': 'count error',
                        'message': 'Les {} de la colonne {} sont < 0'.format(count, selected_columns[count]),
                        'message_data': 'nombre de lignes avec erreurs : {}'.format(n_negative_count)
                    })
        """

        if 'count_min' in counts:
            df[selected_columns['count_min']] = df[selected_columns['count_min']].replace(pd.np.nan,str(def_count_val))

        if len(counts) == 1:

            if counts[0] == 'count_min':
                # if only count_min is indicated, then set count_max equal to count_min
                selected_columns['count_max'] = selected_columns['count_min']
                df['count_max'] = df[selected_columns['count_min']] # utile?
                synthese_info.update({'count_max': synthese_info['count_min']}) # utile?

            if counts[0] == 'count_max':
                # if only count_max is indicated, then set count_min to defaut count_min value
                df['count_min'] = str(def_count_val)
                synthese_info.update({'count_min': synthese_info['count_max']}) # utile?


        if len(counts) == 2:

            # set count_max equal to count_min if count_max missing
            df['temp'] = ''
            df['temp'] = df.apply(lambda x: check_missing_count_max(x[selected_columns['count_min']], x[selected_columns['count_max']]), axis=1, meta=False)
            df[selected_columns['count_max']] = df['temp']


        # check count_min not > to count_max :

        if len(counts) > 0:

            df['temp'] = ''

            # dask version
            df['temp'] = df.apply(lambda x: check_count_min_max(x[selected_columns['count_min']], x[selected_columns['count_max']]), axis=1, meta=False)
            
            """
            # pandas version
            df['temp'] = pd.to_numeric(df[selected_columns['count_max']], errors='coerce') - pd.to_numeric(df[selected_columns['count_min']], errors='coerce') < 0
            df['temp'] = -df['temp']
            """

            df['gn_is_valid'] = df['gn_is_valid'].where(cond=df['temp'].apply(lambda x: fill_col(x), meta=False), other=False)
            df['gn_invalid_reason'] = df['gn_invalid_reason'].where(
                cond=df['temp'].apply(lambda x: fill_col(x)),
                other=df['gn_invalid_reason'] + 'count_min ({}) > count_max ({}) -- '.format(selected_columns['count_min'],selected_columns['count_max']))

            n_count_min_sup = df['temp'].astype(str).str.contains('False').sum()

            if n_count_min_sup > 0:
                user_error.append({
                    'code': 'count error',
                    'message': 'Des count min sont supérieurs à count max',
                    'message_data': 'nombre de lignes avec erreurs : {}'.format(n_count_min_sup)
                })


        if len(user_error) == 0:
            user_error = ''

        return user_error
    
    except Exception:
        raise
