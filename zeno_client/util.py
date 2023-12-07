"""Utility functions for Zeno client."""

import pandas as pd
import pyarrow as pa
from arrow_json import array_to_utf8_json_array


def df_to_pa(df: pd.DataFrame, id_column: str) -> pa.Table:
    """Convert a Pandas DataFrame to a PyArrow Table with type conversions.

    Args:
        df (pd.DataFrame): DataFrame to convert.
        id_column (str): Name of the column containing the ID.

    Returns:
        pa.Table: PyArrow Table with type conversions.

    Raises:
        ValueError: If id_column contains duplicate values.
    """
    if df[id_column].duplicated().any():
        raise ValueError("ERROR: id_column contains duplicate values")

    # Cast id_column to string to avoid issues with numeric IDs in database
    df.loc[:, id_column] = df[id_column].astype(str)

    pa_table = pa.Table.from_pandas(df, preserve_index=False)

    new_columns = []
    for col_name in pa_table.column_names:
        col_type = pa_table[col_name].type
        data = pa_table[col_name].combine_chunks()

        if pa.types.is_struct(col_type):
            new_column = array_to_utf8_json_array(data)
        elif pa.types.is_list(col_type):
            if pa.types.is_integer(col_type.value_type) or pa.types.is_floating(
                col_type.value_type
            ):
                new_column = data
            else:
                new_column = array_to_utf8_json_array(data)
        elif (
            pa.types.is_integer(col_type)
            or pa.types.is_floating(col_type)
            or pa.types.is_boolean(col_type)
        ):
            new_column = data
        else:
            new_column = data.cast(pa.string())

        new_columns.append((col_name, new_column))

    return pa.table({name: col for name, col in new_columns})
