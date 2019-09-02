import datetime

from ..db.query import (
    get_synthese_info
)

from .check_cd_nom import check_cd_nom
from .check_dates import check_dates
from .check_missing import format_missing, check_missing
from .check_id_sinp import check_uuid
from .check_types import check_types
from .check_other_fields import check_entity_source
from .check_counts import check_counts
from .check_altitudes import check_altitudes
from ..logs import logger


def data_cleaning(df, data, missing_val, def_count_val):

    try:

        user_error = []

        # get synthese fields filled in the user form:
        selected_columns = {key:value for key, value in data.items() if value}
        logger.debug('selected columns in correspondance mapping = %s', selected_columns)

        # set gn_is_valid and gn_invalid_reason:
        df['gn_is_valid'] = True
        df['gn_invalid_reason'] = ''

        # get synthese column info:
        selected_synthese_cols = [*list(selected_columns.keys())]
        synthese_info = get_synthese_info(selected_synthese_cols)
        synthese_info['cd_nom']['is_nullable'] = 'NO' # mettre en conf?

        # Check data:
        error_missing = check_missing(df, selected_columns, synthese_info, missing_val)
        error_types = check_types(df, selected_columns, synthese_info, missing_val)
        error_cd_nom = check_cd_nom(df, selected_columns, missing_val)
        error_dates = check_dates(df, selected_columns, synthese_info)
        error_uuid = check_uuid(df,selected_columns,synthese_info)
        error_check_counts = check_counts(df, selected_columns, synthese_info, def_count_val)
        error_altitudes = check_altitudes(df, selected_columns, synthese_info, calcul=False)
        check_entity_source(df, selected_columns, synthese_info)

        # User error to front interface:
        if error_missing != '':
            for error in error_missing:
                user_error.append(error)
        if error_types != '':
            for error in error_types:
                user_error.append(error)
        if error_cd_nom != '':
            user_error.append(error_cd_nom)
        if error_dates != '':
            for error in error_dates:
                user_error.append(error)
        if error_uuid != '':
            for error in error_uuid:
                user_error.append(error)
        if error_check_counts != '':
            for error in error_check_counts:
                user_error.append(error)
        
        return user_error

    except Exception:
        raise
