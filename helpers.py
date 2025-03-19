"""This module contains helper functions.

Functions:\n
    funk_drucken -- Print with timestamp.\n
    funk_drucken_streamlit -- Print with timestamp in streamlit.\n
    funk_schlafen -- Sleep for random seconds between the two boundaries
    given in the arguments.\n
    funk_nested_dict_zu_frame -- Converts nested dictionary to pandas
    dataframe and returns it.
"""

# %%
###################################################################################################
import streamlit

import datetime
import time
import random
import pandas


# %%
###################################################################################################
def funk_drucken(*arg_zu_druckender_text):
    """Print with timestamp."""
    print('##########', str(datetime.datetime.now()), ':', *arg_zu_druckender_text)


def funk_drucken_streamlit(*arg_zu_druckender_text):
    """Print with timestamp in streamlit."""
    streamlit.write('##########', str(datetime.datetime.now()), ':', *arg_zu_druckender_text)


def funk_schlafen(
        arg_grenze_unten,
        arg_grenze_oben
        ):
    """Sleep for random seconds between the two boundaries given in the
    arguments.
    
    Keyword arguments:\n
        arg_grenze_unten -- Lower boundary in seconds\n
        arg_grenze_oben: Upper boundary in seconds
    """
    time.sleep(round(random.uniform(arg_grenze_unten, arg_grenze_oben), 2))


def funk_nested_dict_zu_frame(
        arg_dict: dict,
        arg_schluessel: str
        ):
    """Converts nested dictionary to pandas dataframe and returns it.
    
    Keyword arguments:
        arg_dict -- Nested dictionary\n
        arg_schluessel -- Name for first column which is created with
        the keys of the outer dictionary as cell values
    """
    daten = {}
    
    for key_aussen_x, value_aussen_x in arg_dict.items():
        for key_innen_x, value_innen_x in value_aussen_x.items():
            daten.setdefault(key_innen_x, []).append(value_innen_x)
    frame = pandas.DataFrame(daten)
    frame.insert(0, arg_schluessel, list(arg_dict.keys()))
    
    return(frame)
