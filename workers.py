"""This module contains the classes which do the actual work for
seperate task areas. They communicate via the class Eventmanager which
is in a seperate module.

Classes:\n
    SQLWorker -- An instance of this class can perform all SQL related
    actions in the web app.\n
    ScraperWorker -- An instance of this class can perform all scraping
    related actions in the web app.\n
    AnalyzerWorker -- An instance of this class can perform all
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
import helpers
import constants
from sql_schema import sql_basis
from sql_schema import sqlKlasseTracker
from eventmanager import Eventmanager
from user_interface import UserInterface


# %%
###################################################################################################
class sqlWorker:
    """An instance of this class can perform all SQL related actions in
    the web app.
    
    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        eventmanager -- Instance of Eventmanager to work with\n
        user_interface -- Instance of UserInterface to work with\n
        engine_erstellt -- Engine for postgreSQL database\n
        sql_session_macher -- Instance of sessionmaker which works with
        attribute engine_erstellt\n
        sql_session_erstellt -- Active SQL Session of the instance to
        work with\n
        tracker_objekt -- Object from database query which holds
        information about the current workload of the web app
        caused by all users
        
    Public methods:\n
        funk_sql_tracker_updaten -- Checks if a scraping order is
        allowed to be executed.

    Private methods:\n
        _funk_sql_engine_erstellen -- Returns a created engine for a
        postgreSQL database.\n
        _funk_db_pfad_erstellen -- Returns the path of the postgreSQL
        database on the local machine.\n
        _funk_sql_add_und_commit_all -- Adds and commits all (changed)
        objects from a list to the database.\n
        _funk_sql_commit -- Executes a controlled commit to the
        database with rollback if failed.\n
        _funk_sql_neue_session_erstellen -- Renews the SQL Session in
        attribute sql_session_erstellt.\n
        _funk_sql_session_schliessen -- Closes the SQL Session in
        attribute sql_session_erstellt.\n
        _funk_sql_schema_erstellen -- Creates the SQL database schema.
    """

    def __init__(
            self,
            init_eventmanager: Eventmanager,
            init_user_interface: UserInterface
            ):
        """Inits sqlWorker.

        Keyword arguments:\n
        init_eventmanager -- Active instance of class Eventmanager\n
        init_user_interface -- Active instance of class UserInterface
        """
        self.eventmanager = init_eventmanager
        self.user_interface = init_user_interface
        
        self.engine_erstellt = sqlWorker._funk_sql_engine_erstellen()
        self.sql_session_macher = sessionmaker(bind=self.engine_erstellt)
        self.sql_session_erstellt = self.sql_session_macher() 
        self.tracker_objekt = None

        self._funk_sql_schema_erstellen()


    @staticmethod
    @streamlit.cache_resource(ttl=3600, show_spinner=False)
    def _funk_sql_engine_erstellen():
        """Returns a created engine for a postgreSQL database."""
        if socket.gethostbyname(socket.gethostname()) == constants.LOKALE_IP:
            db_pfad = sqlWorker._funk_db_pfad_erstellen()
        else:
            db_pfad = str(os.environ['DATABASE_URL']).replace('postgres', 'postgresql')

        sql_engine = create_engine(
            db_pfad,
            echo=False,
            poolclass=sqlalchemy.pool.NullPool
            )

        return(sql_engine)
    

    @staticmethod
    @streamlit.cache_resource(ttl=3600, show_spinner=False)
    def _funk_db_pfad_erstellen():
        """Returns the path of the postgreSQL database on the local
        machine.
        """
        pfad_aktuell = subprocess.Popen(
            constants.PFAD_DB_LOKAL,
            shell=True,
            stdout=subprocess.PIPE
        ).stdout.read()
        
        pfad_aktuell_formatiert = copy.deepcopy(
            pfad_aktuell.\
                decode().\
                split('\n')[1].\
                split(' ')[1].\
                replace('postgres', 'postgresql')
            )

        return(pfad_aktuell_formatiert)
        
        
    def funk_sql_tracker_updaten(
            self,
            arg_stichprobe: int
            ):
        """Returns True if a scraping order is allowed to be executed,
        otherwise returns False.
        
        Keyword arguments:\n
        Arg_Stichprobe -- Number of offers that should be scraped
        """
        zeit_jetzt = datetime.datetime.now()
        zeit_jetzt_stamp = int(zeit_jetzt.timestamp())
        flagge_ausfuehren = True

        # SQL query to get current status of the tracker_objekt
        self.tracker_objekt = self.sql_session_erstellt.query(sqlKlasseTracker).first()
        
        # Create new object tracker_objekt if there is none in the database
        if self.tracker_objekt == None:
            self.tracker_objekt=sqlKlasseTracker(
                tracker_id='Tracker_00',
                letzter_job_zeit=str(zeit_jetzt),
                letzter_job_zeit_stamp=zeit_jetzt_stamp,
                summe_n_aktuell_in_zeitraum=arg_stichprobe,
                letzte_nullung_stamp=zeit_jetzt_stamp
                )
        
        # Check if the incoming order suceeds the limit for simultaneously processed orders over
        # all users
        elif self.tracker_objekt != None:
            letzte_nullung_vor_sek = zeit_jetzt_stamp - self.tracker_objekt.letzte_nullung_stamp
            naechste_nullung_in_sek = constants.ZEITRAUM_FUER_RATELIMIT - letzte_nullung_vor_sek

            if letzte_nullung_vor_sek > constants.ZEITRAUM_FUER_RATELIMIT:
                setattr(self.tracker_objekt, 'summe_n_aktuell_in_zeitraum', 0)
                setattr(self.tracker_objekt, 'letzte_nullung_stamp', zeit_jetzt_stamp)
                self._funk_sql_add_und_commit_all([self.tracker_objekt])

            zeit_diff_letzter_job = zeit_jetzt_stamp - self.tracker_objekt.letzter_job_zeit_stamp

            if zeit_diff_letzter_job <= constants.ZEITRAUM_FUER_RATELIMIT:
                kontingent_offen = (constants.N_FUER_RATELIMIT
                                    - self.tracker_objekt.summe_n_aktuell_in_zeitraum)
                if kontingent_offen < arg_stichprobe:
                    flagge_ausfuehren = False

            # If the rate limit is not reached, allow the processing of the order
            if flagge_ausfuehren == True:
                setattr(self.tracker_objekt, 'summe_n_aktuell_in_zeitraum',
                        self.tracker_objekt.summe_n_aktuell_in_zeitraum + arg_stichprobe)
                setattr(self.tracker_objekt, 'letzter_job_zeit', str(zeit_jetzt))
                setattr(self.tracker_objekt, 'letzter_job_zeit_stamp', zeit_jetzt_stamp)

        self._funk_sql_add_und_commit_all([self.tracker_objekt])
        
        # If the rate limit is reached, do not allow the processing of the order and stop script
        # from running
        if flagge_ausfuehren == False:                    
            nachricht_fehler = f'''ACHTUNG!: In den letzten {constants.ZEITRAUM_FUER_RATELIMIT}
                Sekunden wurden (von möglicherweise verschiedenen Personen) bereits zu viele
                Aufträge an diese Web App gesendet. Bitte versuche es in {naechste_nullung_in_sek}
                Sekunden erneut oder verringere die gesuchte Anzeigenanzahl in den Optionen auf
                höchstens {kontingent_offen} Anzeigen!
                [Hier](#hinweis-zum-rate-limiting) findest du einen Hinweis zum Rate Limiting.
                '''

            self.eventmanager.funk_event_eingetreten(
                arg_event_name='Vorzeitig_abgebrochen',
                arg_argumente_von_event={
                                        'arg_art': 'Fehler',
                                        'arg_nachricht': nachricht_fehler
                                        }
                )
    
    
    def _funk_sql_add_und_commit_all(
            self,
            arg_liste_objekte: list
            ):
        """Adds and commits all (changed) objects in list
        arg_liste_objekte to the database.
        
        Keyword arguments:\n
        arg_liste_objekte -- List of (changed) objects to commit
        """
        self.sql_session_erstellt.add_all(arg_liste_objekte)
        self._funk_sql_commit()


    def _funk_sql_commit(self):
        """Executes a controlled commit to the database with rollback
        if failed.
        """
        try:
            self.sql_session_erstellt.commit()
        except IntegrityError as integrity_fehler:
            try:
                self.sql_session_erstellt.rollback()
                helpers.funk_drucken('BESTAETIGUNG!: Rollback nach IntegrityError erfolgreich')                
            except Exception as fehler:
                pass
                helpers.funk_drucken('ACHTUNG!: Fehler bei rollback nach IntegrityError')
                
        except Exception as fehler:
            pass
            fehler_name = str(type(fehler).__name__)
            helpers.funk_drucken(f'BESTAETIGUNG!: Rollback nach {fehler_name} erfolgreich')  
            try:
                self.SQL_Session_erstellt.rollback()
                helpers.funk_drucken(f'ACHTUNG!: Fehler bei rollback nach {fehler_name}')
            except:
                pass


    def _funk_sql_neue_session_erstellen(self):
        """Renews the SQL session in attribute sql_session_erstellt."""
        self._funk_sql_session_schliessen()
        self.sql_session_macher = sessionmaker(bind=self.engine_erstellt)
        self.sql_session_erstellt = self.sql_session_macher()   

    
    def _funk_sql_session_schliessen(self):
        """Closes the SQL session in attribute sql_session_erstellt."""
        try:
            self.sql_session_erstellt.close()
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in sqlWorker._funk_sql_session_schliessen')
            helpers.funk_drucken('Exception:', str(type(fehler).__name__))
            helpers.funk_drucken('Fehler:', fehler)


    def _funk_sql_schema_erstellen(self):
        """Creates the SQL database schema."""
        sql_basis.metadata.create_all(self.engine_erstellt)
    


# %%
###################################################################################################
class Scraper_Worker:
    """An instance of this class can perform all scraping related
    actions in the web app.
    
    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        eventmanager -- Instance of Eventmanager to work with\n
        sql_Worker -- Instance of sqlWorker to work with\n
        user_interface -- Instance of UserInterface to work with\n
        suchbegriff -- Current search term\n
        stichprobe -- Number of offers that should be scraped, i. e.
        expected sample size\n
        max_anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample\n
        buch_anzeigen -- Current dict of scraped offers with links to
        offers as keys of the dict\n
        buch_ergebnisse -- Current dict containing the scraped data and
        external data (e. g. inhabitant numbers) aggregated on the
        level of the 16 states in germann, i. e. the keys of the dict
        are the names of the different states\n
        antwort_server_str -- Current response from Kleinanzeigen server
        after sending a request while scraping\n
        zaehler_anzeigen -- Counter for scraped offers while scraping\n
        liste_elemente_anzeige -- Temporary list with scraped HTML
        elements while scraping\n
        baum_html -- Temporary HTML tree while scraping\n
        flagge_fertig_geschuerft -- Flag which becomes True when
        scraping is done\n
        flagge_letzte_seite -- Flag which becomes True when the last
        page for the searched article on the Kleinanzeigen website is
        reached\n
        zeitstempel_heute -- Timestamp for 00:00:00 of the current day\n
        max_anzeigenalter_sekunden -- Attribute max_anzeigenalter
        converted to seconds\n
        sitzung -- Current object for sending requests created by
        calling requests.Session()\n
        payload -- Payload for the external scraper API
        
    Public methods:\n
        funk_auftrag_annehmen -- This function receives the scraping
        order from the eventmanager.

    Private methods:\n
        _funk_arbeiten -- Does the actual work after the order was
        received.\n
        _funk_schuerfen -- Scrapes the offers with the help of other
        private methods after receiving the order.\n
        _funk_html_objekt_erstellen -- Updates attributes baum_html,
        liste_elemente_anzeigen and antwort_server_str.\n
        _funk_html_objekt_erste_seite_pruefen -- Checks for errors after
        sending the request for the first time to the Kleinanzeigen
        website.\n
        _funk_html_objekt_filter_schuerfen -- Updates attribute
        buch_ergebnisse with data found in the filters of the
        Kleinanzeigen website.\n
        _funk_html_objekt_anzeigen_schuerfen -- Updates attribute
        buch_anzeigen with data from the offers.
    """

    def __init__(
            self,
            init_eventmanager: Eventmanager,
            init_sql_worker: sqlWorker,
            init_user_interface: UserInterface
            ):
        """Inits ScraperWorker.

        Keyword arguments:\n
        init_eventmanager -- Active instance of class Eventmanager\n
        init_sql_Worker -- Active instance of class SQLWorker\n
        init_user_interface -- Active instance of class UserInterface
        """
        self.eventmanager = init_eventmanager
        self.sql_worker = init_sql_worker
        self.user_interface = init_user_interface
        
        self.suchbegriff = ''
        self.stichprobe = constants.N_DEFAULT_STICHPROBE_AUFTRAG
        self.max_anzeigenalter = constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG
        
        self.buch_anzeigen = {}
        self.buch_ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.Antwort_Server_str = ''  
        
        self.zaehler_anzeigen = None
        self.liste_elemente_anzeige = None
        self.baum_html = None
        self.flagge_fertig_geschuerft = None
        self.flagge_letzte_seite = None
        self.zeitstempel_heute = None
        self.max_anzeigenalter_sekunden = None
        self.sitzung = None
        self.payload = None


    def funk_auftrag_annehmen(
            self,
            arg_auftrag_suchbegriff: str,
            arg_auftrag_stichprobe: int,
            arg_auftrag_max_anzeigenalter: int):
        """This function receives the scraping order from the
        eventmanager.
        
        Keyword arguments:\n
        arg_auftrag_suchbegriff -- Search term of incoming order\n
        arg_auftrag_stichprobe -- Number of offers that should be scraped
        for the incoming order\n
        arg_auftrag_max_anzeigenalter -- Maximum age of offers (in days)
        which should be included in the scraped sample for the incoming
        order
        """ 
        if arg_auftrag_stichprobe > constants.N_GRENZE_STICHPROBE_AUFTRAG:
            self.stichprobe = constants.N_GRENZE_STICHPROBE_AUFTRAG
        else:
            self.stichprobe = arg_auftrag_stichprobe
        
        # Check whether the rate limit for all users is not reached
        self.sql_worker.funk_sql_tracker_updaten(arg_stichprobe=self.stichprobe)
        
        self.suchbegriff = arg_auftrag_suchbegriff.lstrip().rstrip().lower()       
        self.max_anzeigenalter = arg_auftrag_max_anzeigenalter

        self.buch_anzeigen = {}
        self.buch_ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.antwort_server_str = ''
        self.baum_html = None
        
        with self.user_interface.platzhalter_ausgabe_spinner_02:
            with streamlit.spinner('Deine Daten werden gerade gesammelt.'):
                self._funk_arbeiten()
                    
        # Tell the Eventmanager that the scraping is done
        self.eventmanager.funk_event_eingetreten(
            arg_event_name='Fertig_geschuerft',
            arg_argumente_von_event={
                'arg_auftrag_suchbegriff': self.suchbegriff,
                'arg_auftrag_stichprobe': self.stichprobe,
                'arg_auftrag_max_anzeigenalter': self.max_anzeigenalter,
                'arg_auftrag_buch_anzeigen': self.buch_anzeigen,
                'arg_auftrag_buch_ergebnisse': self.buch_ergebnisse,
                'arg_auftrag_antwort_server_str': self.antwort_server_str
                }
            )
        

    def _funk_arbeiten(self):   
        """Does the actual work after the order was received.
        """
        self._funk_schuerfen()
    

    def _Funk_Schuerfen(self):
        """Scrapes the offers with the help of other private methods after
        receiving the order.
        """
        suchbegriff_url = self.suchbegriff.replace(' ', '-')
        if suchbegriff_url == '':
            flagge_alle_artikel = True
        else:
            flagge_alle_artikel = False

        anhang_url = 'k0'
        self.zaehler_anzeigen = 0
        self.flagge_fertig_geschuerft = False
        self.flagge_letzte_seite = False

        jahr_gerade = datetime.datetime.now().year
        monat_gerade = datetime.datetime.now().month
        tag_gerade = datetime.datetime.now().day
        self.zeitstempel_heute = datetime.datetime(jahr_gerade,
                                                   monat_gerade,
                                                   tag_gerade).timestamp()

        self.max_anzeigenalter_sekunden = self.max_anzeigenalter*24*60*60

        with requests.Session() as self.sitzung:
            self.sitzung.cookies.clear()

            for seite_i in range(0, int(self.stichprobe / 25 + 2)):
                if seite_i == 0:
                    if flagge_alle_artikel == False:
                        url = f''
                    elif flagge_alle_artikel == True:
                        url = ''
                
                elif seite_i >= 1:
                    if flagge_alle_artikel == False:
                        url = f''
                    elif flagge_alle_artikel == True:
                        url = f''

                self.payload = {'api_key': constants.SCHLUESSEL, 'url': url}

                self._funk_html_objekt_erstellen()
                self._funk_html_objekt_erste_seite_pruefen()
                self._funk_html_objekt_filter_schuerfen()
                self._funk_html_objekt_anzeigen_schuerfen()

                if self.flagge_fertig_geschuerft == True:
                    break

                if self.flagge_letzte_seite == True:
                    break

                helpers.funk_schlafen(
                    constants.SCHLAFEN_SEKUNDEN - 1,
                    constants.SCHLAFEN_SEKUNDEN + 1
                    )


    def _funk_html_objekt_erstellen(self):
        """Updates attributes baum_html, liste_elemente_anzeigen and
        antwort_server_str.
        """
        for i in range(0,2):
            # Try sending the request two times
            try:
                antwort_server = self.sitzung.get('', params=self.payload)
                antwort_server_html = antwort_server.content.decode("utf-8")
                self.baum_html = html.fromstring(antwort_server_html)
                self.liste_elemente_anzeigen = self.baum_html.cssselect('article.aditem')

                if len(self.liste_elemente_anzeigen) == 0:
                    raise IndexError  
                break
            
            except IndexError:
                # If there are not any offers on the page, set the flag for reaching the last page
                # on the Kleinanzeigen website to True
                if i == 1 or len(self.liste_elemente_anzeigen) == 0:
                    self.flagge_letzte_seite = True
                    break

        self.antwort_server_str = str(antwort_server)


    def _funk_html_objekt_erste_seite_pruefen(self):
        """Checks for errors after sending the request for the first time
        to the Kleinanzeigen website.
        """
        # Error because of blocking by the Kleinanzeigen website
        if '418' in self.antwort_server_str:
            nachricht_fehler = f'''ACHTUNG!: Wahrscheinlich ist deine Suche fehlgeschlagen, weil
                die Kleinanzeigen-Website deine Anfrage blockiert! Versuche es später nochmal!'''

            self.eventmanager.funk_event_eingetreten(
                arg_event_name='Vorzeitig_abgebrochen',
                arg_argumente_von_event={
                                        'arg_art': 'Fehler',
                                        'arg_nachricht': nachricht_fehler
                                        }
                )
            
        # Error because there is not a single offer for the current search term
        if len(self.liste_elemente_anzeigen) == 0:                
            nachricht_fehler = f'''ACHTUNG!: Wahrscheinlich wurden keine Anzeigen für deinen
                Suchbegriff "_{self.suchbegriff}_" gefunden! Die Suche wurde deswegen vorzeitig
                abgebrochen!'''

            self.eventmanager.funk_event_eingetreten(
                arg_event_name='Vorzeitig_abgebrochen',
                arg_argumente_von_event={
                                        'arg_art': 'Fehler',
                                        'arg_nachricht': nachricht_fehler
                                        }
            )
            

    def _funk_html_objekt_filter_schuerfen(self):
        """Updates attribute buch_ergebnisse with data found in the
        filters of the Kleinanzeigen website.
        """
        for key_x in self.buch_ergebnisse.keys():
            self.buch_ergebnisse[key_x]['Anzeigenanzahl_total'] = 0

        liste_sections = self.baum_html.cssselect('section')

        for section_x in liste_sections:    
            ueberschriften = section_x.cssselect('h2.sectionheadline')
            
            for ueberschrift_x in ueberschriften:
                if ueberschrift_x.text_content() == 'Ort':
                    laender = section_x.cssselect('li')
                    for land_x in laender:
                        text = land_x.text_content()
                        text = text.replace('.', '')
                        text = text.replace('(', '')
                        text = text.replace(')', '')
                        text = text.replace('\n', '')
                        
                        land_str, anzahl_str = text.split()
                        anzahl_int = int(anzahl_str)

                        self.buch_ergebnisse[land_str]['Anzeigenanzahl_total'] = anzahl_int

                    break


    def _funk_html_objekt_anzeigen_schuerfen(self):
        """Updates attribute buch_anzeigen with data from the offers."""
        for x in self.liste_elemente_anzeigen: 
            ort_str = x.cssselect('div.aditem-main--top--left')[0].text_content().lstrip()

            # Direct URL to the offer
            href_str = str(x.attrib['data-href'])

            preis_str = x.cssselect('p.aditem-main--middle--price-shipping--price')[0].\
                            text_content().\
                            lstrip()

            zeit_str = x.cssselect('div.aditem-main--top > div.aditem-main--top--right')[0].\
                            text_content().\
                            lstrip()
            
            if zeit_str == '':
                zeitstempel = self.zeitstempel_heute
            elif 'Heute' in zeit_str:
                zeitstempel = self.zeitstempel_heute
            elif 'Gestern' in zeit_str:
                zeitstempel = self.zeitstempel_heute - 24*60*60
            else:
                zeit_str = zeit_str.rstrip()
                zeitstempel = datetime.datetime.strptime(zeit_str, '%d.%m.%Y').timestamp()

            # Check whether offer is too old
            if self.zeitstempel_heute - zeitstempel > self.max_anzeigenalter_sekunden:
                self.flagge_fertig_geschuerft = True
                break

            # Add offer to dict in attribute buch_anzeigen
            if href_str not in list(self.buch_anzeigen.keys()):
                self.buch_anzeigen[href_str] = {'Preis': preis_str,
                                                'Ort': ort_str,
                                                'Zeit': zeit_str
                                                }
                self.zaehler_anzeigen += 1

            # Stop scraping when enough offers are scraped already
            if self.zaehler_anzeigen >= self.stichprobe:
                self.flagge_fertig_geschuerft = True
                break



# %%
###################################################################################################
class AnalyzerWorker:
    """An instance of this class can perform all analyzing related
    actions in the web app.

    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        eventmanager -- Instance of Eventmanager to work with\n
        user_interface -- Instance of UserInterface to work with\n
        suchbegriff -- Current search term\n
        stichprobe -- Number of offers that should be scraped, i. e.
        expected sample size\n
        max_anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample\n
        buch_anzeigen -- Current dict of scraped offers with links to
        the offers as keys of the dict\n
        buch_ergebnisse -- Current dict of the results aggregated on the
        level of the 16 states in germany, i. e. names of the different
        states are the keys of the dict\n
        antwort_server_str -- Current response from Kleinanzeigen server
        after sending a request while scraping\n
        frame_geojson_laender -- Loaded geojson data for the borders of
        the 16 states\n
        frame_ergebnisse -- Pandas dataframe containing the scraped data
        and external data (e. g. inhabitant numbers) for analyzing\n
        frame_merge -- Like attribute frame_ergebnisse but also with geo
        data for each of the 16 states\n
        korrelationen -- Correlation matrix for heatmap and clustermap
        based on the data of attribute frame_ergebnisse\n
        ergebnis_bericht -- In general the same data as in attribute
        frame_ergebnisse but formatted\n
        ergebnis_karte_standorte -- Folium Map object with added markers
        representing the locations of the offers (this map will be
        displayed as "Karte 1 (Anzeigenstandorte)" to the user)\n
        ergebnis_karte_anzeigenquote -- Folium Map object with mapped
        data from attribute frame_merge (this map will be displayed as
        "Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern)" to the user)\n
        ergebnis_chi_quadrat -- Results of the chi-square test\n
        ergebnis_heatmap -- Heatmap as opened png file to display to the
        user\n
        ergebnis_clustermap -- Clustermap as opened png file to display
        to the user\n
        ergebnis_scatterplots -- Scatterplots as opened png file to
        display to the user
    
    Public methods:\n
        funk_auftrag_annehmen -- This function receives the analyzing
        order from the eventmanager.
    
    Private methods:\n
        _funk_arbeiten -- Analyzes the data with the help of the other
        private methods.\n
        _funk_buch_anzeigen_fertigstellen -- Updates the attribute
        buch_anzeigen: Adds location data to each scraped offer.\n
        _funk_buch_ergebnisse_fertigstellen -- Updates the attribute
        buch_ergebnisse: Calculates additional variables.\n
        _funk_frames_erstellen -- Creates attributes frame_ergebnisse
        and frame_merge.\n
        _funk_korrelationen_erstellen -- Creates attribute
        Korrelationen.\n
        _funk_ergebnisse_speichern -- Saves relevant results to
        streamlit.session_state.\n
        _funk_frame_bericht_erstellen -- Returns dataframe which will
        become attribute ergebnis_bericht.\n
        _funk_karte_standorte_erstellen -- Returns folium map object
        which will become attribute ergebnis_karte_standorte.\n
        _funk_marker_einfuegen -- Adds location markers to a folium map
        object.\n
        _funk_karte_anzeigenquote_erstellen -- Returns folium map object
        which will become attribute ergebnis_karte_anzeigenquote.\n
        _funk_chi_quadrat_erstellen -- Returns dictionary which will
        become attribute ergebnis_chi_quadrat.\n
        _funk_heatmap_erstellen -- Returns loaded png file which will
        become attribute ergebnis_heatmap.\n
        _funk_clustermap_erstellen -- Returns loaded png file which will
        become attribute ergebnis_clustermap.\n
        funk_scatterplots_erstellen -- Returns loaded png file which
        will become attribute ergebnis_scatterplots.
        """
    
    def __init__(
            self,
            init_eventmanager: Eventmanager,
            init_user_interface: UserInterface,
            ):
        """Inits AnalyzerWorker.

        Keyword arguments:\n
        init_eventmanager -- Active instance of class Eventmanager\n
        init_user_interface -- Active instance of class UserInterface
        """
        self.eventmanager = init_eventmanager
        self.user_interface = init_user_interface

        self.suchbegriff = ''
        self.stichprobe = constants.N_DEFAULT_STICHPROBE_AUFTRAG
        self.max_anzeigenalter = constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG
        self.buch_anzeigen = {}
        self.buch_ergebnisse = copy.deepcopy(streamlit.session_state['Buch_Laender'])
        self.antwort_server_str = ''

        self.frame_geojson_laender = geopandas.read_file(streamlit.\
                                                         session_state['Geojson_Laender']
                                                         )
        self.frame_ergebnisse = None
        self.frame_merge = None
        
        self.korrelationen = None
        self.ergebnis_bericht = None
        self.ergebnis_karte_standorte = None
        self.ergebnis_karte_anzeigenquote = None
        self.ergebnis_chi_quadrat = None
        self.ergebnis_heatmap = None
        self.ergebnis_clustermap = None
        self.ergebnis_scatterplots = None


    def funk_auftrag_annehmen(
            self,
            arg_auftrag_suchbegriff: str,
            arg_auftrag_stichprobe: int,
            arg_auftrag_max_anzeigenalter: int,
            arg_auftrag_buch_anzeigen: dict,
            arg_auftrag_buch_ergebnisse: dict,
            arg_auftrag_antwort_server_str: str):
        """This function receives the analyzing order from the
        eventmanager.
        
        Keyword arguments:\n
        arg_auftrag_suchbegriff -- Search term for the processed order\n
        arg_auftrag_stichprobe -- Number of offers that were scraped
        for the processed order\n
        arg_auftrag_max_anzeigenalter -- Maximum age of offers (in days)
        which should be included in the scraped sample for the processed
        order\n
        arg_auftrag_buch_anzeigen -- Dict of scraped offers with links
        to offers as keys of the dict\n
        arg_auftrag_buch_ergebnisse -- Dict of the results aggregated on
        the level of the 16 states in germann, i. e. the keys of the
        dict are the names of the different states\n
        arg_auftrag_antwort_server_str -- Final response from the
        Kleinanzeigen server
        """ 
        self.suchbegriff = arg_auftrag_suchbegriff
        self.stichprobe = arg_auftrag_stichprobe
        self.max_anzeigenalter = arg_auftrag_max_anzeigenalter
        self.buch_anzeigen = arg_auftrag_buch_anzeigen
        self.buch_ergebnisse = arg_auftrag_buch_ergebnisse
        self.antwort_server_str = arg_auftrag_antwort_server_str
        
        with self.user_interface.platzhalter_ausgabe_spinner_02:
            with streamlit.spinner('Deine Daten werden gerade analysiert.'):
                self._funk_arbeiten()

        # Tell the eventmanager that the analyzing is done
        self.eventmanager.funk_event_eingetreten(
            arg_event_name='Fertig_analysiert',
            arg_argumente_von_event={
                                    'arg_art': 'Erfolg',
                                    'arg_nachricht': 'NEUER AUFTRAG FERTIG BEARBEITET!'
                                    }
            )


    def _funk_arbeiten(self):
        """Analyzes the data with the help of the other private
        methods.
        """
        self._funk_buch_anzeigen_fertigstellen()
        self._funk_buch_ergebnisse_fertigstellen()
        self._funk_frames_erstellen()
        self._funk_korrelationen_erstellen()
        self._funk_ergebnisse_speichern()


    def _funk_buch_anzeigen_fertigstellen(self):
        """Updates the attribute buch_anzeigen: Adds location data to
        each scraped offer.
        """
        for key_x in self.buch_anzeigen:
            plz_anzeige = self.buch_anzeigen[key_x]['Ort'].split(' ')[0]

            eintrag_aus_Buch_PLZs = streamlit.session_state['Buch_PLZs'][plz_anzeige]
            
            self.buch_anzeigen[key_x]['PLZ'] = plz_anzeige
            self.buch_anzeigen[key_x]['Land'] = eintrag_aus_Buch_PLZs['Land']
            self.buch_anzeigen[key_x]['Breitengrad'] = eintrag_aus_Buch_PLZs['Breitengrad']
            self.buch_anzeigen[key_x]['Laengengrad'] = eintrag_aus_Buch_PLZs['Laengengrad']
    

    def _funk_buch_ergebnisse_fertigstellen(self):
        """Updates the attribute buch_ergebnisse: Calculates additional
        variables.
        """
        anzeigenanzahl_total_deutschland = 0

        for x in self.buch_ergebnisse.keys():
            self.buch_ergebnisse[x]['Anzeigenanzahl'] = 0
            anzeigenanzahl_total_deutschland = (
                anzeigenanzahl_total_deutschland + self.buch_ergebnisse[x]['Anzeigenanzahl_total']
                )

        for x in self.buch_anzeigen.keys():
            land_von_anzeige = self.buch_anzeigen[x]['Land']
            self.buch_ergebnisse[land_von_anzeige]['Anzeigenanzahl'] = (
                self.buch_ergebnisse[land_von_anzeige]['Anzeigenanzahl'] + 1
                )
        
        for x in self.buch_ergebnisse.keys():
            self.buch_ergebnisse[x]['Anzeigenquote'] = (
                self.buch_ergebnisse[x]['Anzeigenanzahl']
                / self.buch_ergebnisse[x]['Einwohnerzahl']
                * 1000000
                )
            
            self.buch_ergebnisse[x]['Anzeigenanzahl_erwartet'] = (
                self.buch_ergebnisse[x]['Gewicht_Einwohnerzahl']
                * len(self.buch_anzeigen)
                )
            
            self.buch_ergebnisse[x]['ANZEIGENQUOTE_TOTAL'] = (
                self.buch_ergebnisse[x]['Anzeigenanzahl_total']
                / self.buch_ergebnisse[x]['Einwohnerzahl']
                * 1000000
                )
            
            self.buch_ergebnisse[x]['Anzeigenanzahl_total_erwartet'] = (
                self.buch_ergebnisse[x]['Gewicht_Einwohnerzahl']
                * anzeigenanzahl_total_deutschland
                )


    def _funk_frames_erstellen(self):
        """Creates attributes frame_ergebnisse and frame_merge."""
        self.frame_ergebnisse = helpers.funk_nested_dict_zu_frame(
                                    arg_dict=self.buch_ergebnisse,
                                    arg_schluessel='Land'
                                    )
        
        self.frame_merge = self.frame_geojson_laender.merge(self.frame_ergebnisse, on = 'Land')
        
        spaltennamen_fuer_int = [
            'Flaeche', 'Einwohnerdichte', 'ANZEIGENQUOTE_TOTAL', 'Anzeigenanzahl_total_erwartet'
            ]
        
        self.frame_merge[spaltennamen_fuer_int] = self.frame_merge[spaltennamen_fuer_int].\
                                                    astype(int)
        
        spaltenamen_fuer_round_2 = [
            'Alter_0_17', 'Alter_18_65', 'Alter_66_100', 'Anzeigenquote', 'Anzeigenanzahl_erwartet'
            ]
        
        self.frame_merge[spaltenamen_fuer_round_2] = self.frame_merge[spaltenamen_fuer_round_2].\
                                                        round(2)
        
        self.frame_merge['Gewicht_Einwohnerzahl'] = self.frame_merge['Gewicht_Einwohnerzahl'].\
                                                        round(3)
            

    def _funk_korrelationen_erstellen(self):
        """Creates attribute korrelationen."""
        try:
            frame_korrelationen = copy.deepcopy(self.frame_ergebnisse)
            frame_korrelationen.drop(
                [
                'Gewicht_Einwohnerzahl', 'Anzeigenanzahl', 'Anzeigenquote',
                'Anzeigenanzahl_erwartet', 'Anzeigenanzahl_total_erwartet'
                ],
                axis=1, inplace=True
                )
            
            frame_korrelationen = frame_korrelationen.select_dtypes(exclude=['object']) 

            self.korrelationen = frame_korrelationen.corr(method='spearman')
    
        except Exception as fehler:
            helpers.Funk_Drucken('ACHTUNG!: Fehler in _funk_korrelationen_erstellen:')
            print(fehler)


    def _funk_ergebnisse_speichern(self):
        """Saves relevant results to streamlit.session_state."""
        # If the results are for an order which has already been executed with the same parameters
        # before, delete the old results in streamlit.session_state
        order_id_in_state = f'{self.suchbegriff}_{self.stichprobe}_{self.max_anzeigenalter}'
        
        try:
            del(streamlit.session_state['Ergebnisse'][order_id_in_state])
        except Exception:
            pass
        
        ##########
        streamlit.session_state['Ergebnisse'][order_id_in_state] = {}

        ##########
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Suchbegriff'] = self.suchbegriff
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Stichprobe'] = self.stichprobe
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Max_Anzeigenalter']\
            = self.max_anzeigenalter
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Buch_Anzeigen']\
            = self.buch_anzeigen
        
        ##########
        self.ergebnis_bericht = self._funk_frame_bericht_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Frame_Bericht']\
            = self.ergebnis_bericht

        ##########
        self.ergebnis_karte_standorte = self._funk_karte_standorte_erstellen() 
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Karte_Standorte']\
            = self.ergebnis_karte_standorte
        
        ##########              
        self.ergebnis_karte_anzeigenquote = self._funk_karte_anzeigenquote_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Karte_Anzeigenquote']\
            = self.ergebnis_karte_anzeigenquote
        
        self.ergebnis_chi_quadrat = self._funk_chi_quadrat_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Chi_Quadrat']\
            = self.ergebnis_chi_quadrat
        
        self.ergebnis_heatmap = self._funk_heatmap_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Heatmap']\
            = self.ergebnis_heatmap
        
        self.ergebnis_clustermap = self._funk_clustermap_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Clustermap']\
            = self.ergebnis_clustermap

        self.ergebnis_scatterplots = self._funk_scatterplots_erstellen()
        streamlit.session_state['Ergebnisse'][order_id_in_state]['Scatterplots']\
            = self.ergebnis_scatterplots
       

    def _funk_frame_bericht_erstellen(self):
        """Returns dataframe which will become attribute
        ergebnis_bericht.
        """
        try:
            frame_bericht = copy.deepcopy(self.frame_ergebnisse)

            frame_bericht = frame_bericht[[
                'Land', 'Reg_S', 'ANZEIGENQUOTE_TOTAL', 'Flaeche', 'Einwohnerzahl',
                'Einwohnerdichte', 'Haus_Einkommen', 'Alter_Mittelwert', 'Alter_0_17',
                'Alter_18_65', 'Alter_66_100', 'Anzeigenanzahl_total',
                'Anzeigenanzahl_total_erwartet', 'Gewicht_Einwohnerzahl',
                'Anzeigenquote', 'Anzeigenanzahl', 'Anzeigenanzahl_erwartet'
                ]]
            
            frame_bericht.set_index('Land', inplace=True)
            
            spaltennamen_fuer_int = [
                'Flaeche', 'Einwohnerdichte', 'ANZEIGENQUOTE_TOTAL',
                'Anzeigenanzahl_total_erwartet'
                ]
            frame_bericht[spaltennamen_fuer_int] = frame_bericht[spaltennamen_fuer_int].astype(int)
            
            return(frame_bericht)
        
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in funk_frame_bericht_erstellen:')
            print(fehler)
            return(None)


    def _funk_karte_standorte_erstellen(self):
        """Returns folium map object which will become attribute
        ergebnis_karte_standorte.
        """
        try:
            karte_standorte = folium.Map(
                                location=[51.21541768046512, 10.545707079698555],
                                zoom_start=5.5,
                                control_scale=True
                                )
            
            self._funk_marker_einfuegen(
                arg_buch_anzeigen=self.buch_anzeigen,
                arg_karte=karte_standorte
                )
            return(karte_standorte)
        
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in funk_karte_standorte_erstellen:')
            print(fehler)
            return(None)


    def _funk_marker_einfuegen(self, arg_buch_anzeigen, arg_karte):
        """Adds location markers to a folium map object.

        Keyword arguments:\n
        arg_buch_anzeigen -- Dict with offers and corresponding location
        data\n
        arg_karte -- Folium map object for adding the markers to
        """
        buch_laengengrade = {}
        
        for x in arg_buch_anzeigen.keys():
            breitengrad = arg_buch_anzeigen[x]['Breitengrad']
            laengengrad = arg_buch_anzeigen[x]['Laengengrad']

            plz = arg_buch_anzeigen[x]['PLZ']

            # If there is already an offer with the same PLZ, change the longitude for the marker
            # slightly to make the markers distinguishable
            if plz in buch_laengengrade:
                laengengrad = buch_laengengrade[plz] + 0.002
                buch_laengengrade[plz] = buch_laengengrade[plz] + 0.002
            else:
                buch_laengengrade[plz] = laengengrad
 
            titel = x.split('/')[2].replace('-', ' ')
            preis = '## ' + arg_buch_anzeigen[x]['Preis']
            url = f''

            if len(titel) > 20:
                titel_kurz = titel[:20] + '...'
            else:
                titel_kurz = titel

            folium.Marker(
                [breitengrad, laengengrad],
                icon = folium.Icon(color="red"),
                popup = url,
                tooltip =  f'{titel_kurz}\n{preis}\n ## ' + arg_buch_anzeigen[x]['Ort']
                ).add_to(arg_karte)
    

    def _funk_karte_anzeigenquote_erstellen(self):
        """Returns folium map object which will become attribute
        ergebnis_karte_anzeigenquote.
        """
        try:
            if self.frame_merge['Anzeigenanzahl_total'].sum() == 0:
                return(None)
            
            karte_anzeigenquote = folium.Map(
                                    location=[51.21541768046512, 10.545707079698555],
                                    prefer_canvas=True,
                                    zoom_start=4.7,
                                    control_scale=True
                                    )

            style_funktion = lambda x: {
                                'fillColor': '#ffffff', 
                                'color':'#000000', 
                                'fillOpacity': 0.1, 
                                'weight': 0.1
                                }
            
            highlight_funktion = lambda x: {
                                    'fillColor': '#5df724', 
                                    'color':'#000000', 
                                    'fillOpacity': 1.0, 
                                    'weight': 1.0
                                    }

            folium.Choropleth(
                geo_data=streamlit.session_state['Geojson_Laender'],
                name='choropleth',
                data=self.frame_merge,
                columns=['Land', 'ANZEIGENQUOTE_TOTAL'],
                key_on='feature.id',
                fill_color='Reds',
                fill_opacity=1.0,
                line_opacity=1.0,
                legend_name='ANZEIGENQUOTE_TOTAL',
                highlight=True
                ).add_to(karte_anzeigenquote)
            
            highlights = folium.features.GeoJson(
                data=self.frame_merge,
                style_function=style_funktion, 
                control=False,
                highlight_function=highlight_funktion, 
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

            karte_anzeigenquote.add_child(highlights)
        
            return(karte_anzeigenquote)
    
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in funk_karte_anzeigenquote_erstellen:')
            print(fehler)
            return(None)


    def _funk_chi_quadrat_erstellen(self):
        """Returns dictionary which will become attribute
        ergebnis_chi_quadrat.
        """
        try:
            anzeigenanzahl_beobachtet = self.frame_ergebnisse['Anzeigenanzahl_total']
            anzeigenanzahl_erwartet = self.frame_ergebnisse['Anzeigenanzahl_total_erwartet']

            chi_quadrat = scipy.stats.chisquare(
                f_obs=anzeigenanzahl_beobachtet,
                f_exp=anzeigenanzahl_erwartet
                )

            anzeigenanzahl_total_deutschland = self.frame_ergebnisse['Anzeigenanzahl_total'].sum()
            
            freiheitsgrade = self.frame_ergebnisse.shape[0] - 1
            
            buch_chi_quadrat = {'Freiheitsgrade': freiheitsgrade,
                                'Stichprobe': anzeigenanzahl_total_deutschland,
                                'Chi_Quadrat': chi_quadrat.statistic,
                                'p_Wert': chi_quadrat.pvalue
                                }

            if numpy.isnan(buch_chi_quadrat['Chi_Quadrat']) == True:
                return(None)
            else:
                return(buch_chi_quadrat)
            
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in _funk_chi_quadrat_erstellen:')
            print(fehler)
            return(None)


    def _funk_heatmap_erstellen(self):
        """Returns loaded png file which will become attribute
        ergebnis_heatmap.
        """
        try:
            fig, ax = plt.subplots(figsize=(5,5))

            seaborn.set_theme(font_scale=0.7)
            seaborn.heatmap(
                self.korrelationen,
                annot=True, fmt=".2f", cmap='seismic', vmin=-1.0, vmax=1.0,
                annot_kws={"size": 8}
                )
            
            fig.savefig('Heatmap.png', bbox_inches="tight")

            fig_geladen = PIL.Image.open('Heatmap.png')

            return(fig_geladen)
        
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in funk_heatmap_erstellen:')
            print(fehler)
            return(None)
    

    def _funk_clustermap_erstellen(self):
        """Returns loaded png file which will become attribute
        ergebnis_clustermap.
        """
        try:                    
            seaborn.set_theme(font_scale=0.8)
            clustermap = seaborn.clustermap(
                self.korrelationen,
                annot=True, fmt=".2f", cmap='seismic', vmin=-1.0, vmax=1.0,
                annot_kws={"size": 8}, figsize=(6,6)
                )
            
            clustermap.savefig('Clustermap.png', bbox_inches="tight")

            fig_geladen = PIL.Image.open('Clustermap.png')

            return(fig_geladen)
        
        except Exception as fehler:
            helpers.funk_drucken('ACHTUNG!: Fehler in funk_clustermap_erstellen:')
            print(fehler)
            return(None)
    

    def _funk_scatterplots_erstellen(self):
        """Returns loaded png file which will become attribute
        ergebnis_scatterplots.
        """
        try:
            frame_scatterplots = copy.deepcopy(self.frame_ergebnisse)
            frame_scatterplots.drop(columns=[
                'Gewicht_Einwohnerzahl', 'Anzeigenanzahl', 'Anzeigenquote',
                'Anzeigenanzahl_erwartet', 'Anzeigenanzahl_total_erwartet', 'Flaeche',
                'Einwohnerzahl', 'Anzeigenanzahl_total'
                ],
                inplace=True
                ) 
            
            fig = pandas.plotting.scatter_matrix(
                frame_scatterplots,
                alpha=0.2,
                figsize=(10, 10),
                diagonal='hist'
                )
            
            [plt.setp(x.xaxis.get_label(), 'size', 7) for x in fig.ravel()]
            [plt.setp(x.yaxis.get_label(), 'size', 7) for x in fig.ravel()]
            
            plt.savefig(r'Scatterplots.png', bbox_inches='tight') 

            fig_geladen = PIL.Image.open('Scatterplots.png')

            return(fig_geladen)
        
        except Exception as fehler:
            helpers.funk_Drucken('ACHTUNG!: Fehler in funk_scatterplots_erstellen:')
            print(fehler)
            return(None)
