"""This module contains helper functions.

Functions:\n
    Funk_Drucken -- Print with timestamp.\n
    Funk_Drucken_Streamlit -- Print with timestamp in streamlit.\n
    Funk_Schlafen -- Sleep for random seconds between the two boundaries
    given in the arguments.\n
    Funk_Nested_Dict_zu_Frame -- Converts nested dictionary to pandas
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
def Funk_Drucken(*ZudruckenderText):
    """Print with timestamp."""
    print('##########', str(datetime.datetime.now()), ':', *ZudruckenderText)


def Funk_Drucken_Streamlit(*ZudruckenderText):
    """Print with timestamp in streamlit."""
    streamlit.write('##########', str(datetime.datetime.now()), ':', *ZudruckenderText)


def Funk_Schlafen(
        Arg_Grenze_unten,
        Arg_Grenze_oben
        ):
    """Sleep for random seconds between the two boundaries given in the
    arguments.
    
    Keyword arguments:\n
        Arg_Grenze_unten -- Lower boundary in seconds\n
        Arg_Grenze_oben: Upper boundary in seconds
    """
    time.sleep(round(random.uniform(Arg_Grenze_unten, Arg_Grenze_oben), 2))


def Funk_Nested_Dict_zu_Frame(
        Arg_Dict: dict,
        Arg_Schluessel: str
        ):
    """Converts nested dictionary to pandas dataframe and returns it.
    
    Keyword arguments:
        Arg_Dict -- Nested dictionary\n
        Arg_Schluessel -- Name for first column which is created with
        the keys of the outer dictionary as cell values
    """
    Daten = {}
    
    for Key_aussen_x, Value_aussen_x in Arg_Dict.items():
        for Key_innen_x, Value_innen_x in Value_aussen_x.items():
            Daten.setdefault(Key_innen_x, []).append(Value_innen_x)
    Frame = pandas.DataFrame(Daten)
    Frame.insert(0, Arg_Schluessel, list(Arg_Dict.keys()))
    
    return(Frame)
