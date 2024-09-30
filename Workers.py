"""This module contains the classes which do the actual work for
seperate task areas. They communicate via the class Eventmanager which
is in a seperate module.

Classes:\n
    SQL_Worker -- An instance of this class can perform all SQL related
    actions in the web app.\n
    Scraper_Worker -- An instance of this class can perform all scraping
    related actions in the web app.\n
    Analyzer_Worker -- An instance of this class can perform all
    analyzing related actions in the web app.
"""

# %%
###################################################################################################
import streamlit

import datetime
import time
from statistics import mean
import socket
import subprocess
import copy
import os

import psycopg2
from psycopg2.errors import ProgrammingError
from psycopg2.errors import UndefinedTable
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import scipy
import numpy
import folium
from branca.element import Figure
import pandas
import geopandas
import matplotlib.pyplot as plt
import PIL
import seaborn

import requests
from lxml import html

##################################################
# Import modules from folder
import Helpers
import Constants
from SQL_Schema import SQL_Basis
from SQL_Schema import SQL_Klasse_Tracker
from Eventmanager import Eventmanager
from User_Interface import User_Interface


# %%
###################################################################################################
class SQL_Worker:
    """An instance of this class can perform all SQL related actions in
    the web app.
    
    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        Eventmanager -- Instance of Eventmanager to work with\n
        UI -- Instance of User_Interface to work with\n
        Engine_erstellt -- Engine for postgreSQL database\n
        SQL_Session_Macher -- Instance of sessionmaker which works with
        attribute Engine_erstellt\n
        SQL_Session_erstellt -- Active SQL Session of the instance to
        work with\n
        Tracker_Objekt -- Object from database query which holds
        information about the current workload of the web app
        caused by all users
        
    Public methods:\n
        Funk_SQL_Tracker_updaten -- Checks if a scraping order is
        allowed to be executed.

    Private methods:\n
        _Funk_SQL_Engine_erstellen -- Returns a created engine for a
        postgreSQL database.\n
        _Funk_DB_Pfad_erstellen -- Returns the path of the postgreSQL
        database on the local machine.\n
        _Funk_SQL_add_und_commit_all -- Adds and commits all (changed)
        objects from a list to the database.\n
        _Funk_SQL_commit -- Executes a controlled commit to the
        database with rollback if failed.\n
        _Funk_SQL_neue_Session_erstellen -- Renews the SQL Session in
        attribute SQL_Session_erstellt.\n
        _Funk_SQL_Session_schliessen -- Closes the SQL Session in
        attribute SQL_Session_erstellt.\n
        _Funk_SQL_Schema_erstellen -- Creates the SQL database schema.
    """

    def __init__(
            self,
            Init_Eventmanager: Eventmanager,
            Init_UI: User_Interface
            ):
        """Inits SQL_Worker.

        Keyword arguments:\n
        Init_Eventmanager -- Active instance of class Eventmanager\n
        Init_UI -- Active instance of class User_Interface
        """
        self.Eventmanager = Init_Eventmanager
        self.UI = Init_UI
        
        self.Engine_erstellt = SQL_Worker._Funk_SQL_Engine_erstellen()
        self.SQL_Session_Macher = sessionmaker(bind=self.Engine_erstellt)
        self.SQL_Session_erstellt = self.SQL_Session_Macher() 
        self.Tracker_Objekt = None

        self._Funk_SQL_Schema_erstellen()


    @staticmethod
    @streamlit.cache_resource(ttl=3600, show_spinner=False)
    def _Funk_SQL_Engine_erstellen():
        """Returns a created engine for a postgreSQL database."""
        if socket.gethostbyname(socket.gethostname()) == Constants.LOKALE_IP:
            DB_Pfad = SQL_Worker._Funk_DB_Pfad_erstellen()
        else:
            DB_Pfad = str(os.environ['DATABASE_URL']).replace('postgres', 'postgresql')

        SQL_Engine = create_engine(
            DB_Pfad,
            echo=False,
            poolclass=sqlalchemy.pool.NullPool
            )

        return(SQL_Engine)
    

    @staticmethod
    @streamlit.cache_resource(ttl=3600, show_spinner=False)
    def _Funk_DB_Pfad_erstellen():
        """Returns the path of the postgreSQL database on the local
        machine.
        """
        Pfad_aktuell = subprocess.Popen(
            Constants.PFAD_DB_LOKAL,
            shell=True,
            stdout=subprocess.PIPE
        ).stdout.read()
        
        Pfad_aktuell_formatiert = copy.deepcopy(
            Pfad_aktuell.\
                decode().\
                split('\n')[1].\
                split(' ')[1].\
                replace('postgres', 'postgresql')
            )

        return(Pfad_aktuell_formatiert)
        
        
    def Funk_SQL_Tracker_updaten(
            self,
            Arg_Stichprobe: int
            ):
        """Returns True if a scraping order is allowed to be executed,
        otherwise returns False.
        
        Keyword arguments:\n
        Arg_Stichprobe -- Number of offers that should be scraped
        """
        Zeit_jetzt = datetime.datetime.now()
        Zeit_jetzt_stamp = int(Zeit_jetzt.timestamp())
        Flagge_Ausfuehren = True

        # SQL query to get current status of the Tracker_Objekt
        self.Tracker_Objekt = self.SQL_Session_erstellt.query(SQL_Klasse_Tracker).first()
        
        # Create new object Tracker_Objekt if there is none in the database
        if self.Tracker_Objekt == None:
            self.Tracker_Objekt=SQL_Klasse_Tracker(
                Tracker_ID='Tracker_00',
                Letzter_Job_Zeit=str(Zeit_jetzt),
                Letzter_Job_Zeit_stamp=Zeit_jetzt_stamp,
                Summe_n_aktuell_in_Zeitraum=Arg_Stichprobe,
                Letzte_Nullung_stamp=Zeit_jetzt_stamp
                )
        
        # Check if the incoming order suceeds the limit for simultaneously processed orders over
        # all users
        elif self.Tracker_Objekt != None:
            Letzte_Nullung_vor_Sek = Zeit_jetzt_stamp - self.Tracker_Objekt.Letzte_Nullung_stamp
            Naechste_Nullung_in_Sek = Constants.ZEITRAUM_FUER_RATELIMIT - Letzte_Nullung_vor_Sek

            if Letzte_Nullung_vor_Sek > Constants.ZEITRAUM_FUER_RATELIMIT:
                setattr(self.Tracker_Objekt, 'Summe_n_aktuell_in_Zeitraum', 0)
                setattr(self.Tracker_Objekt, 'Letzte_Nullung_stamp', Zeit_jetzt_stamp)
                self._Funk_SQL_add_und_commit_all([self.Tracker_Objekt])

            Zeit_Diff_letzter_Job = Zeit_jetzt_stamp - self.Tracker_Objekt.Letzter_Job_Zeit_stamp

            if Zeit_Diff_letzter_Job <= Constants.ZEITRAUM_FUER_RATELIMIT:
                Kontingent_offen = (Constants.N_FUER_RATELIMIT
                                    - self.Tracker_Objekt.Summe_n_aktuell_in_Zeitraum)
                if Kontingent_offen < Arg_Stichprobe:
                    Flagge_Ausfuehren = False

            # If the rate limit is not reached, allow the processing of the order
            if Flagge_Ausfuehren == True:
                setattr(self.Tracker_Objekt, 'Summe_n_aktuell_in_Zeitraum',
                        self.Tracker_Objekt.Summe_n_aktuell_in_Zeitraum + Arg_Stichprobe)
                setattr(self.Tracker_Objekt, 'Letzter_Job_Zeit', str(Zeit_jetzt))
                setattr(self.Tracker_Objekt, 'Letzter_Job_Zeit_stamp', Zeit_jetzt_stamp)

        self._Funk_SQL_add_und_commit_all([self.Tracker_Objekt])
        
        # If the rate limit is reached, do not allow the processing of the order and stop script
        # from running
        if Flagge_Ausfuehren == False:                    
            Nachricht_Fehler = f'''ACHTUNG!: In den letzten {Constants.ZEITRAUM_FUER_RATELIMIT}
                Sekunden wurden (von möglicherweise verschiedenen Personen) bereits zu viele
                Aufträge an diese Web App gesendet. Bitte versuche es in {Naechste_Nullung_in_Sek}
                Sekunden erneut oder verringere die gesuchte Anzeigenanzahl in den Optionen auf
                höchstens {Kontingent_offen} Anzeigen!
                [Hier](#hinweis-zum-rate-limiting) findest du einen Hinweis zum Rate Limiting.
                '''

            self.Eventmanager.Funk_Event_eingetreten(
                Arg_Event_Name='Vorzeitig_abgebrochen',
                Arg_Argumente_von_Event={
                                        'Arg_Art': 'Fehler',
                                        'Arg_Nachricht': Nachricht_Fehler
                                        }
                )
    
    
    def _Funk_SQL_add_und_commit_all(
            self,
            Arg_Liste_Objekte: list
            ):
        """Adds and commits all (changed) objects in list
        Arg_Liste_Objekte to the database.
        
        Keyword arguments:\n
        Arg_Liste_Objekte -- List of (changed) objects to commit
        """
        self.SQL_Session_erstellt.add_all(Arg_Liste_Objekte)
        self._Funk_SQL_commit()


    def _Funk_SQL_commit(self):
        """Executes a controlled commit to the database with rollback
        if failed.
        """
        try:
            self.SQL_Session_erstellt.commit()
        except IntegrityError as Integrity_Fehler:
            try:
                self.SQL_Session_erstellt.rollback()
                Helpers.Funk_Drucken('BESTAETIGUNG!: Rollback nach IntegrityError erfolgreich')                
            except Exception as Fehler:
                pass
                Helpers.Funk_Drucken('ACHTUNG!: Fehler bei rollback nach IntegrityError')
                
        except Exception as Fehler:
            pass
            Fehler_Name = str(type(Fehler).__name__)
            Helpers.Funk_Drucken(f'BESTAETIGUNG!: Rollback nach {Fehler_Name} erfolgreich')  
            try:
                self.SQL_Session_erstellt.rollback()
                Helpers.Funk_Drucken(f'ACHTUNG!: Fehler bei rollback nach {Fehler_Name}')
            except:
                pass


    def _Funk_SQL_neue_Session_erstellen(self):
        """Renews the SQL Session in attribute SQL_Session_erstellt."""
        self._Funk_SQL_Session_schliessen()
        self.SQL_Session_Macher = sessionmaker(bind=self.Engine_erstellt)
        self.SQL_Session_erstellt = self.SQL_Session_Macher()   

    
    def _Funk_SQL_Session_schliessen(self):
        """Closes the SQL Session in attribute SQL_Session_erstellt."""
        try:
            self.SQL_Session_erstellt.close()
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in SQL_Worker._Funk_SQL_Session_schliessen')
            Helpers.Funk_Drucken('Exception:', str(type(Fehler).__name__))
            Helpers.Funk_Drucken('Fehler:', Fehler)


    def _Funk_SQL_Schema_erstellen(self):
        """Creates the SQL database schema."""
        SQL_Basis.metadata.create_all(self.Engine_erstellt)
    


# %%
###################################################################################################
class Scraper_Worker:
    """An instance of this class can perform all scraping related
    actions in the web app.
    
    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        Eventmanager -- Instance of Eventmanager to work with\n
        SQL_Worker -- Instance of SQL_Worker to work with\n
        UI -- Instance of User_Interface to work with\n
        Suchbegriff -- Current search term\n
        Stichprobe -- Number of offers that should be scraped, i. e.
        expected sample size\n
        Max_Anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample\n
        Buch_Anzeigen -- Current dict of scraped offers with links to
        offers as keys of the dict\n
        Buch_Ergebnisse -- Current dict containing the scraped data and
        external data (e. g. inhabitant numbers) aggregated on the
        level of the 16 states in germann, i. e. the keys of the dict
        are the names of the different states\n
        Antwort_Server_str -- Current response from Kleinanzeigen server
        after sending a request while scraping\n
        Zaehler_Anzeigen -- Counter for scraped offers while scraping\n
        Liste_Elemente_Anzeige -- Temporary list with scraped HTML
        elements while scraping\n
        Baum_HTML -- Temporary HTML tree while scraping\n
        Flagge_fertig_geschuerft -- Flag which becomes True when
        scraping is done\n
        Flagge_letzte_Seite -- Flag which becomes True when the last
        page for the searched article on the Kleinanzeigen website is
        reached\n
        Zeitstempel_heute -- Timestamp for 00:00:00 of the current day\n
        Max_Anzeigenalter_Sekunden -- Attribute Max_Anzeigenalter
        converted to seconds\n
        Sitzung -- Current object for sending requests created by
        calling requests.Session()\n
        Payload -- Payload for the external scraper API
        
    Public methods:\n
        Funk_Auftrag_annehmen -- This function receives the scraping
        order from the Eventmanager.

    Private methods:\n
        _Funk_Arbeiten -- Does the actual work after the order was
        received.\n
        _Funk_Schuerfen -- Scrapes the offers with the help of other
        private methods after receiving the order.\n
        _Funk_HTML_Objekt_erstellen -- Updates attributes Baum_HTML,
        Liste_Elemente_Anzeigen and Antwort_Server_str.\n
        _Funk_HTML_Objekt_erste_Seite_pruefen -- Checks for errors after
        sending the request for the first time to the Kleinanzeigen
        Website.\n
        _Funk_HTML_Objekt_Filter_schuerfen -- Updates attribute
        Buch_Ergebnisse with data found in the filters of the
        Kleinanzeigen website.\n
        _Funk_HTML_Objekt_Anzeigen_schuerfen -- Updates attribute
        Buch_Anzeigen with data from the offers.
    """

    def __init__(
            self,
            Init_Eventmanager: Eventmanager,
            Init_SQL_Worker: SQL_Worker,
            Init_UI: User_Interface
            ):
        """Inits Scraper_Worker.

        Keyword arguments:\n
        Init_Eventmanager -- Active instance of class Eventmanager\n
        Init_SQL_Worker -- Active instance of class SQL_Worker\n
        Init_UI -- Active instance of class User_Interface
        """
        self.Eventmanager = Init_Eventmanager
        self.SQL_Worker = Init_SQL_Worker
        self.UI = Init_UI
        
        self.Suchbegriff = ''
        self.Stichprobe = Constants.N_DEFAULT_STICHPROBE_AUFTRAG
        self.Max_Anzeigenalter = Constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG
        
        self.Buch_Anzeigen = {}
        self.Buch_Ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.Antwort_Server_str = ''  
        
        self.Zaehler_Anzeigen = None
        self.Liste_Elemente_Anzeige = None
        self.Baum_HTML = None
        self.Flagge_fertig_geschuerft = None
        self.Flagge_letzte_Seite = None
        self.Zeitstempel_heute = None
        self.Max_Anzeigenalter_Sekunden = None
        self.Sitzung = None
        self.Payload = None


    def Funk_Auftrag_annehmen(
            self,
            Arg_Auftrag_Suchbegriff: str,
            Arg_Auftrag_Stichprobe: int,
            Arg_Auftrag_Max_Anzeigenalter: int):
        """This function receives the scraping order from the
        Eventmanager.
        
        Keyword arguments:\n
        Arg_Auftrag_Suchbegriff -- Search term of incoming order\n
        Arg_Auftrag_Stichprobe -- Number of offers that should be scraped
        for the incoming order\n
        Arg_Auftrag_Max_Anzeigenalter -- Maximum age of offers (in days)
        which should be included in the scraped sample for the incoming
        order
        """ 
        if Arg_Auftrag_Stichprobe > Constants.N_GRENZE_STICHPROBE_AUFTRAG:
            self.Stichprobe = Constants.N_GRENZE_STICHPROBE_AUFTRAG
        else:
            self.Stichprobe = Arg_Auftrag_Stichprobe
        
        # Check whether the rate limit for all users is not reached
        self.SQL_Worker.Funk_SQL_Tracker_updaten(Arg_Stichprobe=self.Stichprobe)
        
        self.Suchbegriff = Arg_Auftrag_Suchbegriff.lstrip().rstrip().lower()       
        self.Max_Anzeigenalter = Arg_Auftrag_Max_Anzeigenalter

        self.Buch_Anzeigen = {}
        self.Buch_Ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.Antwort_Server_str = ''
        self.Baum_HTML = None
        
        with self.UI.Platzhalter_Ausgabe_Spinner_02:
            with streamlit.spinner('Deine Daten werden gerade gesammelt.'):
                self._Funk_Arbeiten()
                    
        # Tell the Eventmanager that the scraping is done
        self.Eventmanager.Funk_Event_eingetreten(
            Arg_Event_Name='Fertig_geschuerft',
            Arg_Argumente_von_Event={
                'Arg_Auftrag_Suchbegriff': self.Suchbegriff,
                'Arg_Auftrag_Stichprobe': self.Stichprobe,
                'Arg_Auftrag_Max_Anzeigenalter': self.Max_Anzeigenalter,
                'Arg_Auftrag_Buch_Anzeigen': self.Buch_Anzeigen,
                'Arg_Auftrag_Buch_Ergebnisse': self.Buch_Ergebnisse,
                'Arg_Auftrag_Antwort_Server_str': self.Antwort_Server_str
                }
            )
        

    def _Funk_Arbeiten(self):   
        """Does the actual work after the order was received.
        """
        self._Funk_Schuerfen()
    

    def _Funk_Schuerfen(self):
        """Scrapes the offers with the help of other private methods after
        receiving the order.
        """
        Suchbegriff_url = self.Suchbegriff.replace(' ', '-')
        if Suchbegriff_url == '':
            Flagge_alle_Artikel = True
        else:
            Flagge_alle_Artikel = False

        Anhang_URL = 'k0'
        self.Zaehler_Anzeigen = 0
        self.Flagge_fertig_geschuerft = False
        self.Flagge_letzte_Seite = False

        Jahr_gerade = datetime.datetime.now().year
        Monat_gerade = datetime.datetime.now().month
        Tag_gerade = datetime.datetime.now().day
        self.Zeitstempel_heute = datetime.datetime(Jahr_gerade,
                                                   Monat_gerade,
                                                   Tag_gerade).timestamp()

        self.Max_Anzeigenalter_Sekunden = self.Max_Anzeigenalter*24*60*60

        with requests.Session() as self.Sitzung:
            self.Sitzung.cookies.clear()

            for Seite_i in range(0, int(self.Stichprobe / 25 + 2)):
                if Seite_i == 0:
                    if Flagge_alle_Artikel == False:
                        Url = f''
                    elif Flagge_alle_Artikel == True:
                        Url = ''
                
                elif Seite_i >= 1:
                    if Flagge_alle_Artikel == False:
                        Url = f''
                    elif Flagge_alle_Artikel == True:
                        Url = f''

                self.Payload = {'api_key': Constants.SCHLUESSEL, 'url': Url}

                self._Funk_HTML_Objekt_erstellen()
                self._Funk_HTML_Objekt_erste_Seite_pruefen()
                self._Funk_HTML_Objekt_Filter_schuerfen()
                self._Funk_HTML_Objekt_Anzeigen_schuerfen()

                if self.Flagge_fertig_geschuerft == True:
                    break

                if self.Flagge_letzte_Seite == True:
                    break

                Helpers.Funk_Schlafen(
                    Constants.SCHLAFEN_SEKUNDEN - 1,
                    Constants.SCHLAFEN_SEKUNDEN + 1
                    )


    def _Funk_HTML_Objekt_erstellen(self):
        """Updates attributes Baum_HTML, Liste_Elemente_Anzeigen and
        Antwort_Server_str.
        """
        for i in range(0,2):
            # Try sending the request two times
            try:
                Antwort_Server = self.Sitzung.get()
                Antwort_Server_HTML = Antwort_Server.content.decode("utf-8")
                self.Baum_HTML = html.fromstring(Antwort_Server_HTML)
                self.Liste_Elemente_Anzeigen = self.Baum_HTML.cssselect('article.aditem')

                if len(self.Liste_Elemente_Anzeigen) == 0:
                    raise IndexError  
                break
            
            except IndexError:
                # If there are not any offers on the page, set the flag for reaching the last page
                # on the Kleinanzeigen website to True
                if i == 1 or len(self.Liste_Elemente_Anzeigen) == 0:
                    self.Flagge_letzte_Seite = True
                    break

        self.Antwort_Server_str = str(Antwort_Server)


    def _Funk_HTML_Objekt_erste_Seite_pruefen(self):
        """Checks for errors after sending the request for the first time
        to the Kleinanzeigen Website.
        """
        # Error because of blocking by the Kleinanzeigen website
        if '418' in self.Antwort_Server_str:
            Nachricht_Fehler = f'''ACHTUNG!: Wahrscheinlich ist deine Suche fehlgeschlagen, weil
                die Kleinanzeigen-Website deine Anfrage blockiert! Versuche es später nochmal!'''

            self.Eventmanager.Funk_Event_eingetreten(
                Arg_Event_Name='Vorzeitig_abgebrochen',
                Arg_Argumente_von_Event={
                                        'Arg_Art': 'Fehler',
                                        'Arg_Nachricht': Nachricht_Fehler
                                        }
                )
            
        # Error because there is not a single offer for the current search term
        if len(self.Liste_Elemente_Anzeigen) == 0:                
            Nachricht_Fehler = f'''ACHTUNG!: Wahrscheinlich wurden keine Anzeigen für deinen
                Suchbegriff "_{self.Suchbegriff}_" gefunden! Die Suche wurde deswegen vorzeitig
                abgebrochen!'''

            self.Eventmanager.Funk_Event_eingetreten(
                Arg_Event_Name='Vorzeitig_abgebrochen',
                Arg_Argumente_von_Event={
                                        'Arg_Art': 'Fehler',
                                        'Arg_Nachricht': Nachricht_Fehler
                                        }
            )
            

    def _Funk_HTML_Objekt_Filter_schuerfen(self):
        """Updates attribute Buch_Ergebnisse with data found in the
        filters of the Kleinanzeigen website.
        """
        for Key_x in self.Buch_Ergebnisse.keys():
            self.Buch_Ergebnisse[Key_x]['Anzeigenanzahl_total'] = 0

        Liste_Sections = self.Baum_HTML.cssselect('section')

        for Section_x in Liste_Sections:    
            Ueberschriften = Section_x.cssselect('h2.sectionheadline')
            
            for Ueberschrift_x in Ueberschriften:
                if Ueberschrift_x.text_content() == 'Ort':
                    Laender = Section_x.cssselect('li')
                    for Land_x in Laender:
                        Text = Land_x.text_content()
                        Text = Text.replace('.', '')
                        Text = Text.replace('(', '')
                        Text = Text.replace(')', '')
                        Text = Text.replace('\n', '')
                        
                        Land_str, Anzahl_str = Text.split()
                        Anzahl_int = int(Anzahl_str)

                        self.Buch_Ergebnisse[Land_str]['Anzeigenanzahl_total'] = Anzahl_int

                    break


    def _Funk_HTML_Objekt_Anzeigen_schuerfen(self):
        """Updates attribute Buch_Anzeigen with data from the offers."""
        for x in self.Liste_Elemente_Anzeigen: 
            Ort_str = x.cssselect('div.aditem-main--top--left')[0].text_content().lstrip()

            # Direct URL to the offer
            href_str = str(x.attrib['data-href'])

            Preis_str = x.cssselect('p.aditem-main--middle--price-shipping--price')[0].\
                            text_content().\
                            lstrip()

            Zeit_str = x.cssselect('div.aditem-main--top > div.aditem-main--top--right')[0].\
                            text_content().\
                            lstrip()

            if Zeit_str == '':
                Zeitstempel = self.Zeitstempel_heute
            elif 'Heute' in Zeit_str:
                Zeitstempel = self.Zeitstempel_heute
            elif 'Gestern' in Zeit_str:
                Zeitstempel = self.Zeitstempel_heute - 24*60*60
            else:
                Zeitstempel = datetime.datetime.strptime(Zeit_str, '%d.%m.%Y').timestamp()

            # Check whether offer is too old
            if self.Zeitstempel_heute - Zeitstempel > self.Max_Anzeigenalter_Sekunden:
                self.Flagge_fertig_geschuerft = True
                break

            # Add offer to dict in attribute Buch_Anzeigen
            if href_str not in list(self.Buch_Anzeigen.keys()): #neu
                self.Buch_Anzeigen[href_str] = {'Preis': Preis_str,
                                                'Ort': Ort_str,
                                                'Zeit': Zeit_str
                                                }
                self.Zaehler_Anzeigen += 1

            # Stop scraping when enough offers are scraped already
            if self.Zaehler_Anzeigen >= self.Stichprobe:
                self.Flagge_fertig_geschuerft = True
                break



# %%
###################################################################################################
class Analyzer_Worker:
    """An instance of this class can perform all analyzing related
    actions in the web app.

    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        Eventmanager -- Instance of Eventmanager to work with\n
        UI -- Instance of User_Interface to work with\n
        Suchbegriff -- Current search term\n
        Stichprobe -- Number of offers that should be scraped, i. e.
        expected sample size\n
        Max_Anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample\n
        Buch_Anzeigen -- Current dict of scraped offers with links to
        the offers as keys of the dict\n
        Buch_Ergebnisse -- Current dict of the results aggregated on the
        level of the 16 states in germany, i. e. names of the different
        states are the keys of the dict\n
        Antwort_Server_str -- Current response from Kleinanzeigen server
        after sending a request while scraping\n
        Frame_Geojson_Laender -- Loaded geojson data for the borders of
        the 16 states\n
        Frame_Ergebnisse -- Pandas dataframe containing the scraped data
        and external data (e. g. inhabitant numbers) for analyzing\n
        Frame_Merge -- Like attribute Frame_Ergebnisse but also with geo
        data for each of the 16 states\n
        Korrelationen -- Correlation matrix for heatmap and clustermap
        based on the data of attribute Frame_Ergebnisse\n
        Ergebnis_Bericht -- In general the same data as in attribute
        Frame_Ergebnisse but formatted\n
        Ergebnis_Karte_Standorte -- Folium Map object with added markers
        representing the locations of the offers (this map will be
        displayed as "Karte 1 (Anzeigenstandorte)" to the user)\n
        Ergebnis_Karte_Anzeigenquote -- Folium Map object with mapped
        data from attribute Frame_Merge (this map will be displayed as
        "Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern)" to the user)\n
        Ergebnis_Chi_Quadrat -- Results of the chi-square test\n
        Ergebnis_Heatmap -- Heatmap as opened png file to display to the
        user\n
        Ergebnis_Clustermap -- Clustermap as opened png file to display
        to the user\n
        Ergebnis_Scatterplots -- Scatterplots as opened png file to
        display to the user
    
    Public methods:\n
        Funk_Auftrag_annehmen -- This function receives the analyzing
        order from the Eventmanager.
    
    Private methods:\n
        _Funk_Arbeiten -- Analyzes the data with the help of the other
        private methods.\n
        _Funk_Buch_Anzeigen_fertigstellen -- Updates the attribute
        Buch_Anzeigen: Adds location data to each scraped offer.\n
        _Funk_Buch_Ergebnisse_fertigstellen -- Updates the attribute
        Buch_Ergebnisse: Calculates additional variables.\n
        _Funk_Frames_erstellen -- Creates attributes Frame_Ergebnisse
        and Frame_Merge.\n
        _Funk_Korrelationen_erstellen -- Creates attribute
        Korrelationen.\n
        _Funk_Ergebnisse_speichern -- Saves relevant results to
        streamlit.session_state.\n
        _Funk_Frame_Bericht_erstellen -- Returns dataframe which will
        become attribute Ergebnis_Bericht.\n
        _Funk_Karte_Standorte_erstellen -- Returns folium map object
        which will become attribute Ergebnis_Karte_Standorte.\n
        _Funk_Marker_einfuegen -- Adds location markers to a folium map
        object.\n
        _Funk_Karte_Anzeigenquote_erstellen -- Returns folium map object
        which will become attribute Ergebnis_Karte_Anzeigenquote.\n
        _Funk_Chi_Quadrat_erstellen -- Returns dictionary which will
        become attribute Ergebnis_Chi_Quadrat.\n
        _Funk_Heatmap_erstellen -- Returns loaded png file which will
        become attribute Ergebnis_Heatmap.\n
        _Funk_Clustermap_erstellen -- Returns loaded png file which will
        become attribute Ergebnis_Clustermap.\n
        Funk_Scatterplots_erstellen -- Returns loaded png file which
        will become attribute Ergebnis_Scatterplots.
        """
    
    def __init__(
            self,
            Init_Eventmanager: Eventmanager,
            Init_UI: User_Interface,
            ):
        """Inits Analyzer_Worker.

        Keyword arguments:\n
        Init_Eventmanager -- Active instance of class Eventmanager\n
        Init_UI -- Active instance of class User_Interface
        """
        self.Eventmanager = Init_Eventmanager
        self.UI = Init_UI

        self.Suchbegriff = ''
        self.Stichprobe = Constants.N_DEFAULT_STICHPROBE_AUFTRAG
        self.Max_Anzeigenalter = Constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG
        self.Buch_Anzeigen = {}
        self.Buch_Ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.Antwort_Server_str = ''

        self.Frame_Geojson_Laender = geopandas.read_file(streamlit.\
                                                         session_state['Geojson_Laender']
                                                         )
        self.Frame_Ergebnisse = None
        self.Frame_Merge = None
        
        self.Korrelationen = None
        self.Ergebnis_Bericht = None
        self.Ergebnis_Karte_Standorte = None
        self.Ergebnis_Karte_Anzeigenquote = None
        self.Ergebnis_Chi_Quadrat = None
        self.Ergebnis_Heatmap = None
        self.Ergebnis_Clustermap = None
        self.Ergebnis_Scatterplots = None


    def Funk_Auftrag_annehmen(
            self,
            Arg_Auftrag_Suchbegriff: str,
            Arg_Auftrag_Stichprobe: int,
            Arg_Auftrag_Max_Anzeigenalter: int,
            Arg_Auftrag_Buch_Anzeigen: dict,
            Arg_Auftrag_Buch_Ergebnisse: dict,
            Arg_Auftrag_Antwort_Server_str: str):
        """This function receives the analyzing order from the
        Eventmanager.
        
        Keyword arguments:\n
        Arg_Auftrag_Suchbegriff -- Search term for the processed order\n
        Arg_Auftrag_Stichprobe -- Number of offers that were scraped
        for the processed order\n
        Arg_Auftrag_Max_Anzeigenalter -- Maximum age of offers (in days)
        which should be included in the scraped sample for the processed
        order\n
        Arg_Auftrag_Buch_Anzeigen -- Dict of scraped offers with links
        to offers as keys of the dict\n
        Arg_Auftrag_Buch_Ergebnisse -- Dict of the results aggregated on
        the level of the 16 states in germann, i. e. the keys of the
        dict are the names of the different states\n
        Arg_Auftrag_Antwort_Server_str -- Final response from the
        Kleinanzeigen server
        """ 
        self.Suchbegriff = Arg_Auftrag_Suchbegriff
        self.Stichprobe = Arg_Auftrag_Stichprobe
        self.Max_Anzeigenalter = Arg_Auftrag_Max_Anzeigenalter
        self.Buch_Anzeigen = Arg_Auftrag_Buch_Anzeigen
        self.Buch_Ergebnisse = Arg_Auftrag_Buch_Ergebnisse
        self.Antwort_Server_str = Arg_Auftrag_Antwort_Server_str
        
        with self.UI.Platzhalter_Ausgabe_Spinner_02:
            with streamlit.spinner('Deine Daten werden gerade analysiert.'):
                self._Funk_Arbeiten()

        # Tell the Eventmanager that the analyzing is done
        self.Eventmanager.Funk_Event_eingetreten(
            Arg_Event_Name='Fertig_analysiert',
            Arg_Argumente_von_Event={
                                    'Arg_Art': 'Erfolg',
                                    'Arg_Nachricht': 'NEUER AUFTRAG FERTIG BEARBEITET!'
                                    }
            )


    def _Funk_Arbeiten(self):
        """Analyzes the data with the help of the other private
        methods.
        """
        self._Funk_Buch_Anzeigen_fertigstellen()
        self._Funk_Buch_Ergebnisse_fertigstellen()
        self._Funk_Frames_erstellen()
        self._Funk_Korrelationen_erstellen()
        self._Funk_Ergebnisse_speichern()


    def _Funk_Buch_Anzeigen_fertigstellen(self):
        """Updates the attribute Buch_Anzeigen: Adds location data to
        each scraped offer.
        """
        for Key_x in self.Buch_Anzeigen:
            PLZ_Anzeige = self.Buch_Anzeigen[Key_x]['Ort'].split(' ')[0]

            Eintrag_aus_Buch_PLZs = streamlit.session_state['Buch_PLZs'][PLZ_Anzeige]
            
            self.Buch_Anzeigen[Key_x]['PLZ'] = PLZ_Anzeige
            self.Buch_Anzeigen[Key_x]['Land'] = Eintrag_aus_Buch_PLZs['Land']
            self.Buch_Anzeigen[Key_x]['Breitengrad'] = Eintrag_aus_Buch_PLZs['Breitengrad']
            self.Buch_Anzeigen[Key_x]['Laengengrad'] = Eintrag_aus_Buch_PLZs['Laengengrad']
    

    def _Funk_Buch_Ergebnisse_fertigstellen(self):
        """Updates the attribute Buch_Ergebnisse: Calculates additional
        variables.
        """
        Anzeigenanzahl_total_Deutschland = 0

        for x in self.Buch_Ergebnisse.keys():
            self.Buch_Ergebnisse[x]['Anzeigenanzahl'] = 0
            Anzeigenanzahl_total_Deutschland = (
                Anzeigenanzahl_total_Deutschland + self.Buch_Ergebnisse[x]['Anzeigenanzahl_total']
                )

        for x in self.Buch_Anzeigen.keys():
            Land_von_Anzeige = self.Buch_Anzeigen[x]['Land']
            self.Buch_Ergebnisse[Land_von_Anzeige]['Anzeigenanzahl'] = (
                self.Buch_Ergebnisse[Land_von_Anzeige]['Anzeigenanzahl'] + 1
                )
        
        for x in self.Buch_Ergebnisse.keys():
            self.Buch_Ergebnisse[x]['Anzeigenquote'] = (
                self.Buch_Ergebnisse[x]['Anzeigenanzahl']
                / self.Buch_Ergebnisse[x]['Einwohnerzahl']
                * 1000000
                )
            
            self.Buch_Ergebnisse[x]['Anzeigenanzahl_erwartet'] = (
                self.Buch_Ergebnisse[x]['Gewicht_Einwohnerzahl']
                * len(self.Buch_Anzeigen)
                )
            
            self.Buch_Ergebnisse[x]['ANZEIGENQUOTE_TOTAL'] = (
                self.Buch_Ergebnisse[x]['Anzeigenanzahl_total']
                / self.Buch_Ergebnisse[x]['Einwohnerzahl']
                * 1000000
                )
            
            self.Buch_Ergebnisse[x]['Anzeigenanzahl_total_erwartet'] = (
                self.Buch_Ergebnisse[x]['Gewicht_Einwohnerzahl']
                * Anzeigenanzahl_total_Deutschland
                )
    

    def _Funk_Frames_erstellen(self):
        """Creates attributes Frame_Ergebnisse and Frame_Merge."""
        self.Frame_Ergebnisse = Helpers.Funk_Nested_Dict_zu_Frame(
                                    Arg_Dict=self.Buch_Ergebnisse,
                                    Arg_Schluessel='Land'
                                    )
        
        self.Frame_Merge = self.Frame_Geojson_Laender.merge(self.Frame_Ergebnisse, on = 'Land')
        
        Spaltennamen_fuer_int = [
            'Flaeche', 'Einwohnerdichte', 'ANZEIGENQUOTE_TOTAL', 'Anzeigenanzahl_total_erwartet'
            ]
        
        self.Frame_Merge[Spaltennamen_fuer_int] = self.Frame_Merge[Spaltennamen_fuer_int].\
                                                    astype(int)
        
        Spaltenamen_fuer_round_2 = [
            'Alter_0_17', 'Alter_18_65', 'Alter_66_100', 'Anzeigenquote', 'Anzeigenanzahl_erwartet'
            ]
        
        self.Frame_Merge[Spaltenamen_fuer_round_2] = self.Frame_Merge[Spaltenamen_fuer_round_2].\
                                                        round(2)
        
        self.Frame_Merge['Gewicht_Einwohnerzahl'] = self.Frame_Merge['Gewicht_Einwohnerzahl'].\
                                                        round(3)
            

    def _Funk_Korrelationen_erstellen(self):
        """Creates attribute Korrelationen."""
        try:
            Frame_Korrelationen = copy.deepcopy(self.Frame_Ergebnisse)
            Frame_Korrelationen.drop(
                [
                'Gewicht_Einwohnerzahl', 'Anzeigenanzahl', 'Anzeigenquote',
                'Anzeigenanzahl_erwartet', 'Anzeigenanzahl_total_erwartet'
                ],
                axis=1, inplace=True
                )
            
            Frame_Korrelationen = Frame_Korrelationen.select_dtypes(exclude=['object']) 

            self.Korrelationen = Frame_Korrelationen.corr(method='spearman')
    
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in _Funk_Korrelationen_erstellen:')
            print(Fehler)


    def _Funk_Ergebnisse_speichern(self):
        """Saves relevant results to streamlit.session_state."""
        # If the results are for an order which has already been executed with the same parameters
        # before, delete the old results in streamlit.session_state
        Order_ID_in_state = f'{self.Suchbegriff}_{self.Stichprobe}_{self.Max_Anzeigenalter}'
        
        try:
            del(streamlit.session_state['Ergebnisse'][Order_ID_in_state])
        except Exception:
            pass
        
        ##########
        streamlit.session_state['Ergebnisse'][Order_ID_in_state] = {}

        ##########
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Suchbegriff'] = self.Suchbegriff
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Stichprobe'] = self.Stichprobe
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Max_Anzeigenalter']\
            = self.Max_Anzeigenalter
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Buch_Anzeigen']\
            = self.Buch_Anzeigen
        
        ##########
        self.Ergebnis_Bericht = self._Funk_Frame_Bericht_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Frame_Bericht']\
            = self.Ergebnis_Bericht

        ##########
        self.Ergebnis_Karte_Standorte = self._Funk_Karte_Standorte_erstellen() 
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Karte_Standorte']\
            = self.Ergebnis_Karte_Standorte
        
        ##########              
        self.Ergebnis_Karte_Anzeigenquote = self._Funk_Karte_Anzeigenquote_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Karte_Anzeigenquote']\
            = self.Ergebnis_Karte_Anzeigenquote
        
        self.Ergebnis_Chi_Quadrat = self._Funk_Chi_Quadrat_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Chi_Quadrat']\
            = self.Ergebnis_Chi_Quadrat
        
        self.Ergebnis_Heatmap = self._Funk_Heatmap_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Heatmap']\
            = self.Ergebnis_Heatmap
        
        self.Ergebnis_Clustermap = self._Funk_Clustermap_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Clustermap']\
            = self.Ergebnis_Clustermap

        self.Ergebnis_Scatterplots = self._Funk_Scatterplots_erstellen()
        streamlit.session_state['Ergebnisse'][Order_ID_in_state]['Scatterplots']\
            = self.Ergebnis_Scatterplots


    def _Funk_Frame_Bericht_erstellen(self):
        """Returns dataframe which will become attribute
        Ergebnis_Bericht.
        """
        try:
            Frame_Bericht = copy.deepcopy(self.Frame_Ergebnisse)

            Frame_Bericht = Frame_Bericht[[
                'Land', 'Reg_S', 'ANZEIGENQUOTE_TOTAL', 'Flaeche', 'Einwohnerzahl',
                'Einwohnerdichte', 'Haus_Einkommen', 'Alter_Mittelwert', 'Alter_0_17',
                'Alter_18_65', 'Alter_66_100', 'Anzeigenanzahl_total',
                'Anzeigenanzahl_total_erwartet', 'Gewicht_Einwohnerzahl',
                'Anzeigenquote', 'Anzeigenanzahl', 'Anzeigenanzahl_erwartet'
                ]]
            
            Frame_Bericht.set_index('Land', inplace=True)
            
            Spaltennamen_fuer_int = [
                'Flaeche', 'Einwohnerdichte', 'ANZEIGENQUOTE_TOTAL',
                'Anzeigenanzahl_total_erwartet'
                ]
            Frame_Bericht[Spaltennamen_fuer_int] = Frame_Bericht[Spaltennamen_fuer_int].astype(int)
            
            return(Frame_Bericht)
        
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Frame_Bericht_erstellen:')
            print(Fehler)
            return(None)


    def _Funk_Karte_Standorte_erstellen(self):
        """Returns folium map object which will become attribute
        Ergebnis_Karte_Standorte.
        """
        try:
            Karte_Standorte = folium.Map(
                                location=[51.21541768046512, 10.545707079698555],
                                zoom_start=5.5,
                                control_scale=True
                                )
            
            self._Funk_Marker_einfuegen(
                Arg_Buch_Anzeigen=self.Buch_Anzeigen,
                Arg_Karte=Karte_Standorte
                )
            return(Karte_Standorte)
        
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Karte_Standorte_erstellen:')
            print(Fehler)
            return(None)


    def _Funk_Marker_einfuegen(self, Arg_Buch_Anzeigen, Arg_Karte):
        """Adds location markers to a folium map object.

        Keyword arguments:\n
        Arg_Buch_Anzeigen -- Dict with offers and corresponding location
        data\n
        Arg_Karte -- Folium map object for adding the markers to
        """
        Buch_Laengengrade = {}
        
        for x in Arg_Buch_Anzeigen.keys():
            Breitengrad = Arg_Buch_Anzeigen[x]['Breitengrad']
            Laengengrad = Arg_Buch_Anzeigen[x]['Laengengrad']

            Plz = Arg_Buch_Anzeigen[x]['PLZ']

            # komdoku: If there is already an offer with the same PLZ, change the longitude for the
            # marker slightly to make the markers distinguishable
            if Plz in Buch_Laengengrade:
                Laengengrad = Buch_Laengengrade[Plz] + 0.002
                Buch_Laengengrade[Plz] = Buch_Laengengrade[Plz] + 0.002
            else:
                Buch_Laengengrade[Plz] = Laengengrad
 
            Titel = x.split('/')[2].replace('-', ' ')
            Preis = '## ' + Arg_Buch_Anzeigen[x]['Preis']
            Url = f'<a href="https://www.ebay-kleinanzeigen.de{x}"\
                target="_blank">{Titel}\n{Preis}</a>'

            if len(Titel) > 20:
                Titel_kurz = Titel[:20] + '...'
            else:
                Titel_kurz = Titel

            folium.Marker(
                [Breitengrad, Laengengrad],
                icon = folium.Icon(color="red"),
                popup = Url,
                tooltip =  f'{Titel_kurz}\n{Preis}\n ## ' + Arg_Buch_Anzeigen[x]['Ort']
                ).add_to(Arg_Karte)
    

    def _Funk_Karte_Anzeigenquote_erstellen(self):
        """Returns folium map object which will become attribute
        Ergebnis_Karte_Anzeigenquote.
        """
        try:
            if self.Frame_Merge['Anzeigenanzahl_total'].sum() == 0:
                return(None)
            
            Karte_Anzeigenquote = folium.Map(
                                    location=[51.21541768046512, 10.545707079698555],
                                    prefer_canvas=True,
                                    zoom_start=4.7,
                                    control_scale=True
                                    )

            Style_Funktion = lambda x: {
                                'fillColor': '#ffffff', 
                                'color':'#000000', 
                                'fillOpacity': 0.1, 
                                'weight': 0.1
                                }
            
            Highlight_Funktion = lambda x: {
                                    'fillColor': '#5df724', 
                                    'color':'#000000', 
                                    'fillOpacity': 1.0, 
                                    'weight': 1.0
                                    }

            folium.Choropleth(
                geo_data=streamlit.session_state['Geojson_Laender'],
                name='choropleth',
                data=self.Frame_Merge,
                columns=['Land', 'ANZEIGENQUOTE_TOTAL'],
                key_on='feature.id',
                fill_color='Reds',
                fill_opacity=1.0,
                line_opacity=1.0,
                legend_name='ANZEIGENQUOTE_TOTAL',
                highlight=True
                ).add_to(Karte_Anzeigenquote)
            
            Highlights = folium.features.GeoJson(
                data=self.Frame_Merge,
                style_function=Style_Funktion, 
                control=False,
                highlight_function=Highlight_Funktion, 
                tooltip=folium.features.GeoJsonTooltip(
                    prefer_canvas=True,
                    fields=[
                        'Land', 'ANZEIGENQUOTE_TOTAL', 'Anzeigenanzahl_total',
                        'Anzeigenanzahl_total_erwartet', 'Flaeche', 'Einwohnerzahl',
                        'Einwohnerdichte', 'Haus_Einkommen', 'Alter_Mittelwert', 'Alter_0_17',
                        'Alter_18_65', 'Alter_66_100'
                        ],
                    aliases=[
                        'Land', 'ANZEIGENQUOTE_TOTAL', 'Anzeigenanzahl_total',
                        'Anzeigenanzahl_total_erwartet', 'Flaeche', 'Einwohnerzahl',
                        'Einwohnerdichte', 'Haus_Einkommen', 'Alter_Mittelwert', 'Alter_0_17',
                        'Alter_18_65', 'Alter_66_100'
                        ],
                    style=("background-color: white; color: #333333; font-family: arial; \
                                font-size: 12px; padding: 10px;") 
                    )
                )

            Karte_Anzeigenquote.add_child(Highlights)
        
            return(Karte_Anzeigenquote)
    
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Karte_Anzeigenquote_erstellen:')
            print(Fehler)
            return(None)


    def _Funk_Chi_Quadrat_erstellen(self):
        """Returns dictionary which will become attribute
        Ergebnis_Chi_Quadrat.
        """
        try:
            Anzeigenanzahl_beobachtet = self.Frame_Ergebnisse['Anzeigenanzahl_total']
            Anzeigenanzahl_erwartet = self.Frame_Ergebnisse['Anzeigenanzahl_total_erwartet']

            Chi_Quadrat = scipy.stats.chisquare(
                f_obs=Anzeigenanzahl_beobachtet,
                f_exp=Anzeigenanzahl_erwartet
                )

            Anzeigenanzahl_total_Deutschland = self.Frame_Ergebnisse['Anzeigenanzahl_total'].sum()
            
            Freiheitsgrade = self.Frame_Ergebnisse.shape[0] - 1
            
            Buch_Chi_Quadrat = {'Freiheitsgrade': Freiheitsgrade,
                                'Stichprobe': Anzeigenanzahl_total_Deutschland,
                                'Chi_Quadrat': Chi_Quadrat.statistic,
                                'p_Wert': Chi_Quadrat.pvalue
                                }

            if numpy.isnan(Buch_Chi_Quadrat['Chi_Quadrat']) == True:
                return(None)
            else:
                return(Buch_Chi_Quadrat)
            
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in _Funk_Chi_Quadrat_erstellen:')
            print(Fehler)
            return(None)


    def _Funk_Heatmap_erstellen(self):
        """Returns loaded png file which will become attribute
        Ergebnis_Heatmap.
        """
        try:
            Fig, Ax = plt.subplots(figsize=(5,5))

            seaborn.set_theme(font_scale=0.7)
            seaborn.heatmap(
                self.Korrelationen,
                annot=True, fmt=".2f", cmap='seismic', vmin=-1.0, vmax=1.0,
                annot_kws={"size": 8}
                )
            
            Fig.savefig('Heatmap.png', bbox_inches="tight")

            Fig_geladen = PIL.Image.open('Heatmap.png')

            return(Fig_geladen)
        
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Heatmap_erstellen:')
            print(Fehler)
            return(None)
    

    def _Funk_Clustermap_erstellen(self):
        """Returns loaded png file which will become attribute
        Ergebnis_Clustermap.
        """
        try:                    
            seaborn.set_theme(font_scale=0.8)
            Clustermap = seaborn.clustermap(
                self.Korrelationen,
                annot=True, fmt=".2f", cmap='seismic', vmin=-1.0, vmax=1.0,
                annot_kws={"size": 8}, figsize=(6,6)
                )
            
            Clustermap.savefig('Clustermap.png', bbox_inches="tight")

            Fig_geladen = PIL.Image.open('Clustermap.png')

            return(Fig_geladen)
        
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Clustermap_erstellen:')
            print(Fehler)
            return(None)
    

    def _Funk_Scatterplots_erstellen(self):
        """Returns loaded png file which will become attribute
        Ergebnis_Scatterplots.
        """
        try:
            Frame_Scatterplots = copy.deepcopy(self.Frame_Ergebnisse)
            Frame_Scatterplots.drop(columns=[
                'Gewicht_Einwohnerzahl', 'Anzeigenanzahl', 'Anzeigenquote',
                'Anzeigenanzahl_erwartet', 'Anzeigenanzahl_total_erwartet', 'Flaeche',
                'Einwohnerzahl', 'Anzeigenanzahl_total'
                ],
                inplace=True
                ) 
            
            Fig = pandas.plotting.scatter_matrix(
                Frame_Scatterplots,
                alpha=0.2,
                figsize=(10, 10),
                diagonal='hist'
                )
            
            [plt.setp(x.xaxis.get_label(), 'size', 7) for x in Fig.ravel()]
            [plt.setp(x.yaxis.get_label(), 'size', 7) for x in Fig.ravel()]
            
            plt.savefig(r'Scatterplots.png', bbox_inches='tight') 

            Fig_geladen = PIL.Image.open('Scatterplots.png')

            return(Fig_geladen)
        
        except Exception as Fehler:
            Helpers.Funk_Drucken('ACHTUNG!: Fehler in Funk_Scatterplots_erstellen:')
            print(Fehler)
            return(None)
