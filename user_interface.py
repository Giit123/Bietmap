"""This module contains the class UserInterface.

Classes:\n
    UserInterface -- An instance of this class can perform all UI
    related actions in the web app.
"""

# %%
###################################################################################################
import streamlit
import streamlit.components.v1 as import_komponenten
from streamlit_folium import folium_static

import datetime
import time
import random
import json
import seaborn
import matplotlib
import matplotlib.pyplot as plt

##################################################
# Import modules from folder
import constants
from eventmanager import Eventmanager
import helpers


# %%
###################################################################################################
class UserInterface:
    """An instance of this class can perform all UI related actions in
    the web app.

    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        eventmanager -- Instance of Eventmanager to work with\n
        spalte_A, spalte_B -- Invisible columns in which elements can
        be inserted\n
        expander_optionen -- Equippable expander element on the left
        side of the UI for options\n
        expander_ausgabe -- Equippable expander element on the upper
        side of the UI for the results of the user's orders\n
        expander_anleitung -- Equippable expander element on the lower
        side of the UI for the manual\n
        platzhalter -- All attributes which have "platzhalter" in their
        name are streamlit objects which can be equipped with objects
        that should be displayed to the user\n
        input_suchbegriff -- Search term currenty typed in by the user
        in the UI\n
        input_stichprobe -- Sample size currently selected by the user
        in the UI\n
        input_max_anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample selected by the user
        in the UI\n
        liste_tabs -- List with tabs, each for one of the last three
        successfully processed orders sent by the user
        
    Public methods:\n
        funk_einrichten -- Sets up user interface.\n
        funk_feedback_ausgeben -- Prints feedback in the UI in attribute
        platzhalter_ausgabe_feedback.\n
        funk_ergebnisse_ausgeben -- Creates all result tabs: one tab for
        each of the last three successfully processed orders sent by the
        user.\n
        funk_jobs_pruefen -- Checks whether there are open jobs, i. e.
        the button was pressed by the user.\n
        funk_aufraeumen -- Cleans up and stops the script from running.

    Private methods:\n
        _funk_dateien_abfragen -- Loads necessary files into
        streamlit.session_state.\n
        _funk_header_erstellen -- Returns new header for web requests.
        _funk_startseite_einrichten -- Sets up basic user interface
        template.\n
        _funk_geruest_erstellen -- Creates elements for basic user
        interface template.\n
        _funk_expander_optionen_bestuecken -- SSets up options in
        attribute platzhalter_optionen_01 which can be used by the
        user.\n
        _funk_on_click_button -- This function is called when the
        button is pressed by the user.\n
        _funk_scrollen -- Scrolls page element in argument
        arg_element into view.
    """

    def __init__(
            self,
            init_eventmanager: Eventmanager
            ):
        """Inits UserInterface.

        Keyword arguments:\n
        init_eventmanager -- Active instance of class Eventmanager
        """
        self.eventmanager = init_eventmanager
        
        self.spalte_A = None
        self.spalte_B = None
        self.expander_optionen = None
        self.platzhalter_optionen_01 = None
        self.expander_ausgabe = None
        self.platzhalter_ausgabe_spinner_01 = None
        self.platzhalter_ausgabe_spinner_02 = None
        self.platzhalter_ausgabe_feedback = None
        self.platzhalter_ausgabe_ergebnisse = None
        self.expander_anleitung = None
        self.platzhalter_anleitung_01 = None
        self.input_suchbegriff = None
        self.input_stichprobe = None
        self.input_max_anzeigenalter = None
        self.liste_tabs = None


    def funk_einrichten(self):
        """Sets up user interface."""
        # First loading of the web app by the user
        if 'User_Interface_eingerichtet' not in streamlit.session_state:
            self._funk_startseite_einrichten()

            # Create variables in streamlit.session_state for storing between runs
            UserInterface._funk_dateien_abfragen()
            streamlit.session_state['Header'] = UserInterface._funk_header_erstellen()
            streamlit.session_state['Button_gedrueckt'] = False
            streamlit.session_state['Flagge_Ergebnis_gespeichert'] = False
            streamlit.session_state['Ergebnisse'] = {}

            streamlit.session_state['User_Interface_eingerichtet'] = 'Startseite'

        elif streamlit.session_state['Button_gedrueckt'] == True:
            self._funk_startseite_einrichten()

        else:
            self._funk_startseite_einrichten()


    @staticmethod
    def _funk_dateien_abfragen():
        """Loads necessary files into streamlit.session_state."""
        with open('Buch_PLZs.json', encoding='utf-8') as datei:
            Buch_PLZs = json.load(datei)
            streamlit.session_state['Buch_PLZs'] = Buch_PLZs
        
        with open('Geojson_Laender.geojson', encoding='utf-8') as datei:
            geojson_laender = json.load(datei)
            geojson_laender = json.dumps(geojson_laender)
            streamlit.session_state['Geojson_Laender'] = geojson_laender

        with open('Buch_Laender.json', encoding='utf-8') as datei:
            buch_laender = json.load(datei)
            streamlit.session_state['Buch_Laender'] = buch_laender


    @staticmethod
    def _funk_header_erstellen():
        """Returns new header for web requests."""
        zufall_firefox_version = float(random.randint(94, 98))

        liste_neu_header_user_agent = [
                                    [1.0, f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{zufall_firefox_version}) Gecko/20100101 Firefox/{zufall_firefox_version}']
                                    ]

        zufallszahl = random.uniform(0,1)
        for x in liste_neu_header_user_agent:
            if x[0] >= zufallszahl:
                neu_header_user_agent = x[1]
                break

        liste_neu_header_referer = [
                                    [0.7, 'https://www.google.com/'],
                                    [1.0, 'https://www.bing.com/']
                                   ]

        zufallszahl = random.uniform(0,1)
        for x in liste_neu_header_referer:
            if x[0] >= zufallszahl:
                neu_header_referer = x[1]
                break
                
        header = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
                'Referer': neu_header_referer,
                'User-Agent': neu_header_user_agent
                }
        
        return(header)
    

    def _funk_startseite_einrichten(self):
        """Sets up basic user interface template."""
        self._funk_geruest_erstellen()
        self._funk_expander_optionen_bestuecken()


    def _funk_geruest_erstellen(self):
        """Creates elements for basic user interface template."""
        self.spalte_A, self.spalte_B = streamlit.columns((10, 35))

        with self.spalte_A:
            self.expander_optionen = streamlit.expander('Optionen:', expanded=True)

            with self.expander_optionen:
                self.platzhalter_optionen_01 = streamlit.empty()

        with self.spalte_B:
            self.expander_ausgabe = streamlit.expander('Ausgabe:', expanded=True)

            with self.expander_ausgabe:
                self.platzhalter_ausgabe_spinner_01 = streamlit.empty()
                self.platzhalter_ausgabe_spinner_02 = streamlit.empty()
                self.platzhalter_ausgabe_feedback = streamlit.empty()
                self.platzhalter_ausgabe_ergebnisse = streamlit.empty()
            
            UserInterface._funk_scrollen(arg_element='div.st-emotion-cache-18kf3ut')
            
            self.expander_anleitung = streamlit.expander('Anleitung:', expanded=True)

            with self.expander_anleitung:
                self.platzhalter_anleitung_01 = streamlit.empty()

                streamlit.markdown('### **Willkommen bei Bietmap!**')
                streamlit.markdown('''Mit dieser Web App kannst du nach Kleinanzeigen in ganz
                    Deutschland suchen und deren Standorte auf einer Karte anzeigen lassen.
                    So kannst du etwa untersuchen, ob bestimmte Artikel in deinem Bundesland
                    häufiger angeboten werden als in einem anderen. Nutze dazu die 
                    [Optionen](#suchbegriff). Die Optionen werden [gleich](#erklaerung-der-optionen)
                    erklärt.
                    Um eine Suche zu starten, drücke den Button unter den Optionen mit dem Namen
                    "BUTTON: Suche starten!". Die Ergebnisse für deine Suchen werden jeweils
                    in einem App-internen Tab dargestellt (maximal 3 Stück).
                    Um noch mehr Ergebnisse zu vergleichen (oder um weniger zu scrollen), öffne die
                    Web App einfach in einem weiteren Tab deines Browsers. Das Neuladen oder
                    Schließen des _Browsertabs_ löscht alle deine bisherigen Ergebnisse! Schau auch
                    mal in den Abschnitt zu
                    [interessanten Suchbegriffen](#interessante-suchbegriffe). Auch wichtig:
                    [Hinweis zum Rate Limiting](#hinweis-zum-rate-limiting).''')
                streamlit.write('''**_Diese Anleitung wird sich immer ganz unten in der Web App
                    wiederfinden lassen._**''')
                
                streamlit.markdown('#### **Erklärung der Optionen:**')
                streamlit.write('''Die folgenden zwei einstellbaren Optionen werden nur Karte 1
                    (Anzeigenstandorte) beeinflussen, aber nicht Karte 2 (ANZEIGENQUOTE_TOTAL in
                    Bundesländern)! Die Erläuterung der Karten findest du
                    [hier](#erlaeuterung-der-karten).''')
                streamlit.write('''_Anzeigenanzahl:_ Mit dieser Option kannst du festlegen, wie
                    viele Anzeigen maximal in deine Stichprobe aufgenommen werden sollen!''')
                streamlit.write('''_Max. Anzeigenalter:_ Mit dieser Option kannst du festlegen, wie
                    alt die gefundenen Anzeigen maximal sein dürfen (in Tagen). Die Anzeigen werden
                    nach ihrer Aktualität sortiert und die aktuellsten in deine Stichprobe
                    aufgenommen!''')
                streamlit.write('''Dein Suchbegriff wird automatisch in Kleinbuchstaben
                    umgewandelt!''')

                streamlit.markdown('#### **Erläuterung der Karten:**')
                streamlit.write('''Die Ergebnisse deiner Suche werden auf zwei
                    verschiedenen Karten visualisiert:''')
                streamlit.write('''_Karte 1 (Anzeigenstandorte):_ Diese Karte wird von deinen
                    Einstellungen in den Optionen beeinflusst. Hier wird dir jede gefundene
                    Anzeige als Marker auf der Deutschlandkarte angezeigt. Falls viele Anzeigen in
                    einer Stadt gefunden worden sind, musst du vielleicht etwas in die Karte
                    reinzoomen, um die Marker zu unterscheiden! Die Anzeigenstandorte bzw. Marker
                    werden automatisiert anhand der Postleitzahl eingefügt. Dazu wird eine Datei
                    mit Geodaten verwendet, die jeder Postleitzahl genau einen Standort zuordnet.
                    Die Marker befinden sich also nicht immer _exakt_ an den Standorten /
                    Stadtteilen der Anzeigen!''')
                streamlit.write('''_Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern):_ Diese Karte
                    wird NICHT von deinen Einstellungen in den Optionen beeinflusst. Anstatt dessen
                    werden die Angaben aus den Filtern der Kleinanzeigen-Website genutzt, mit
                    welchen die Anzeigen nach (Bundes-)ländern gefiltert werden können.
                    Die Anzahl der Anzeigen in diesen Filtern ist in der Regel größer als die der
                    Anzeigen aus Karte 1 (Anzeigenstandorte). Es werden in den Filtern nämlich
                    _alle_ Anzeigen auf Kleinanzeigen unabhängig deiner Einstellungen in den
                    Optionen dieser Web App berücksichtigt. Durch Verwendung dieser größeren Zahlen
                    sind die Auswertungen in Karte 2 und die weiteren Berechnungen aussagekräftiger.
                    Hier auf Karte 2 werden dir also je Bundesland die gefundenen Anzeigen pro
                    Million Einwohner angezeigt. Es geht also um die Anzeigenquote je Bundesland,
                    bezogen auf die totale Menge von auffindbaren Anzeigen bei Kleinanzeigen.
                    Dementsprechend wird diese Variable in der Web App mit "ANZEIGENQUOTE_TOTAL"
                    bezeichnet.
                    Da sich die Bundesländer bzw. deren Einwohner aber auch in weiteren
                    [Variablen](#erlaeuterung-der-variablen) unterscheiden, bieten sich vielfältige
                    Interpretationsmöglichkeiten. Überlege dir z. B., welchen Einfluss die
                    Einwohnerdichte, die Alterstruktur oder das Einkommen auf die Ergebnisse zu
                    deinem spezifischen Artikel haben könnten.''')
                streamlit.write('''Zudem wird dir eine Tabelle mit den Rohdaten deines Auftrags
                    angezeigt. Die Quellen externer Daten findest du
                    [unten](#datenquellen).''')
                
                streamlit.markdown('#### **Erläuterung der Variablen:**')
                streamlit.write('''**_Die Auflistung erfolgt in alphabetischer Reihenfolge!
                    Die Variablen beziehen sich jeweils auf ein Bundesland. Die Quellen externer
                    Daten findest du [unten](#datenquellen)._**''')
                streamlit.write('''_Alter_0_17_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter bis einschließlich 17 Jahren.''')
                streamlit.write('''_Alter_18_65_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter von 18 bis einschließlich 65 Jahren.''')
                streamlit.write('''_Alter_66_100_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter von mindestens 66 Jahren.''')
                streamlit.write('_Alter_Mittelwert_: Mittelwert des Alters über alle Personen.')
                streamlit.write('''_Anzeigenanzahl_: Dies ist die absolute Anzeigenzahl, welche
                    durch die Suche mit den von dir in den Optionen eingestellten Parametern
                    gefunden wurde. Diese Anzahl von Anzeigen erscheint in Karte 1
                    (Anzeigenstandorte).''')
                streamlit.write('''_Anzeigenanzahl_erwartet_: siehe zunächst Definition
                    der Variable "Anzeigenanzahl". Die erwartete Anzeigenanzahl
                    wäre die, wenn sich alle gefundenen Anzeigen in Deutschland gleich auf die
                    Bundesländer verteilen würden (unter Berücksichtigung der Einwohnerzahl).''')
                streamlit.write('''_Anzeigenanzahl_total_: Dies ist die absolute Anzeigenzahl,
                    welche auf den Angaben aus den Filtern der Kleinanzeigen-Website beruht.
                    Hier werden also _alle_ Anzeigen berücksichtigt, die auf Kleinanzeigen für
                    deinen Suchbegriff gefunden wurden.''')
                streamlit.write('''_Anzeigenanzahl_total_erwartet_: siehe zunächst Definition
                    der Variable "Anzeigenanzahl_total". Die erwartete Anzeigenanzahl_total
                    wäre die, wenn sich alle gefundenen Anzeigen in Deutschland (aus den Filtern)
                    gleich auf die Bundesländer verteilen würden (unter Berücksichtigung der
                    Einwohnerzahl).''')
                streamlit.write(f'''_Anzeigenquote_: Dies ist der Quotient aus der Variable
                    "Anzeigenanzahl" und der Variable "Einwohnerzahl" multipliziert mit 1000000.
                    Dies ist somit die Anzahl der Anzeigen pro Million Einwohner. Diese Zahl
                    ist aber bei kaum aussagekräftig, da sie auf maximal
                    {constants.N_GRENZE_STICHPROBE_AUFTRAG} Anzeigen basiert.''')
                streamlit.write('''_ANZEIGENQUOTE_TOTAL_: Dies ist der Quotient aus der Variable
                    "Anzeigenanzahl_total" und der Variable "Einwohnerzahl" multipliziert mit
                    1000000. Dies ist somit die Anzahl der Anzeigen (in den Filtern)
                    pro Million Einwohner. Diese Variable wird für Karte 2 (ANZEIGENQUOTE_TOTAL
                    in Bundesländern) verwendet.''')
                streamlit.write('''_Einwohnerdichte_: Dies ist der Quotient aus der Variable
                    "Einwohnerzahl" und der Variable "Flaeche".''')
                streamlit.write('_Einwohnerzahl_: Absolute Einwohnerzahl.')
                streamlit.write('_Flaeche_: Fläche des Bundeslands in', r'$km^2$', '.')
                streamlit.write('''_Gewicht_Einwohnerzahl_: Dies ist der Quotient aus der Variable
                    "Einwohnerzahl" und der Einwohnerzahl in ganz Deutschland.''')
                streamlit.write('''_Haus_Einkommen_: Mittelwert des verfügbaren jährlichen
                    Haushaltseinkommens (einschließlich Sozialleistungen, nach Steuern). Dieses
                    Einkommen können die Haushalte also für Lebenshaltungs-, Konsum- und Sparzwecke
                    verwenden. Beachte aber bei deinen Interpretationen die Eigenheiten des
                    Haushaltseinkommens als Indikator,
                    [hier](https://www.bpb.de/themen/soziale-lage/verteilung-von-armut-reichtum/237427/verteilung-der-nettoaequivalenzeinkommen/)
                    gibt es Informationen dazu von der Hans-Böckler-Stiftung.''')
                streamlit.write('''_Regionalschluessel_: Amtlicher Regionalschlüssel.''')

                streamlit.markdown('#### **Interessante Suchbegriffe:**')
                streamlit.write('''Beachte bitte bei den folgenden Überlegungen, dass diese nicht
                    immer ganz ganz ernst gemeint sind. Bedenke auch, dass die Variablen mitunter
                    nicht unabhängig sind, z. B. ist in Städten die Einwohnerdichte höher _und_ das
                    mittlere Alter geringer. Ob also ein Artikel vielleicht deshalb öfter angeboten
                    wird, weil dort mehr Menschen auf geringem Raum wohnen und / oder mehr junge
                    Menschen dort leben, ist nicht klar. Auf eine direkte Kausalität kann daher
                    ohne Weiteres nicht geschlossen werden. Insbesondere gilt dies auch für
                    Interpretationen hinsichtlich West vs. Ost: Menschen im Westen sind im Mittel
                    jünger _und_ verdienen mehr _und_ leben eher in Ballungsgebieten. Dies kannst
                    du auch in der Heatmap, der Clustermap und in den Rohdaten erkennen.''')
                streamlit.write('''_Rolex_: Hamburg hat die höchste ANZEIGENQUOTE_TOTAL.
                    Dort ist auch die Millionärsdichte in Deutschland am höchsten,
                    [hier](https://hamburg.t-online.de/region/hamburg/id_100615280/hamburg-zahl-der-millionaere-waechst-rasant-sorge-vor-ungleichheit.html)
                    ein Artikel dazu.''')
                streamlit.write('''_Chanel, Louis Vuitton, Golfschläger, Silberlöffel etc._:
                    Hier zeigt sich ein ähnliches Bild.''')
                streamlit.write('''_Goldkette_: Der Handel mit Gold scheint dagegen ein Berliner
                    Phänomen zu sein. Vielleicht könnte dies
                    [hieran](https://www.sueddeutsche.de/panorama/goldmuenze-bode-museum-berlin-gericht-urteil-1.5304608)
                    liegen?!''')
                streamlit.write('''_Hund_: In Schleswig-Holstein scheinen viele Hundeliebhaber/innen
                    zu leben.''')
                streamlit.write('''_Katze_: Auch Katzen kommen nicht zu kurz.''')
                streamlit.write('''_Grundstück_: Die
                    [Landflucht](https://www.spiegel.de/wirtschaft/soziales/deutschland-die-extreme-landflucht-der-jungen-und-ihre-gruende-a-1292981.html)
                    und der demografische Wandel in Ostdeutschland zeigen sich auch in dem Verkauf
                    von Grundstücken.''')
                streamlit.write('''_Bayern München_: Während Artikel zu anderen Vereinen eher
                    regional gehäuft angeboten werden, scheinen Bayern-"Fans" in ganz Deutschland
                    ihre Besitztümer zu veräußern. Vielleicht sind dies die "Erfolgsfans", von denen
                    alle immer [sprechen](https://www.tz.de/sport/fc-bayern/vorurteile-gegen-fc-bayern-wirklich-berechtigt-zr-5359532.html)?!
                    ''')

                streamlit.markdown('#### **Datenquellen:**')
                streamlit.write('''Die Standortdaten der PLZs aus
                    [Karte 1](#erlaeuterung-der-karten) stammen von
                    [hier](https://github.com/zauberware/postal-codes-json-xml-csv).
                    ''')
                streamlit.write('''Die Geodaten für die Ländergrenzen in
                    [Karte 2](#erlaeuterung-der-karten) stammen von
                    [hier](https://github.com/isellsoap/deutschlandGeoJSON?tab=readme-ov-file).
                    ''')
                streamlit.write('''Alle Daten hinsichtlich Einwohnerzahlen und Flächen stammen vom
                    statistischen Bundesamt (Destatis), Gebietsstand 31.12.2022, und lassen sich
                    [hier](https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/Administrativ/04-kreise.html)
                    finden.''')
                streamlit.write('''Alle Daten hinsichtlich des Haushaltseinkommens stammen vom
                    Statistikportal des Bundes und der Länder, Stand 2021, und lassen sich
                    [hier](https://www.statistikportal.de/de/veroeffentlichungen/einkommen-der-privaten-haushalte)
                    finden (Tabellenblatt "2.4").
                    ''')
                streamlit.write('''Alle Daten hinsichtlich des Durchschnittsalters (d. h. für die
                    Variable "Alter_Mittelwert") stammen von statista, Stand 2022, und lassen sich
                    [hier](https://de.statista.com/statistik/daten/studie/1093993/umfrage/durchschnittsalter-der-bevoelkerung-in-deutschland-nach-bundeslaendern/)
                    finden.''')
                streamlit.write('''Alle Daten hinsichtlich der Altersgruppen (d. h. für die
                    Variablen "Alter_0_17" etc.) wurden mit Hilfe von Daten aus dem
                    Deutschlandatlas berechnet, Stand 2021, und lassen sich
                    [hier](https://www.deutschlandatlas.bund.de/DE/Karten/Wer-wir-sind/030-Altersgruppen-der-Bevoelkerung.html)
                    finden (Tabellenblatt "Deutschlandatlas_KRS1221").''')

                streamlit.markdown('#### **!!!!! HINWEIS ZUM RATE LIMITING !!!!!:**')
                streamlit.write(f'''Die Suchrate ist so beschränkt, dass über _alle aktiven
                    Appnutzer/innen summiert_ nach maximal {constants.N_FUER_RATELIMIT} Anzeigen
                    pro {constants.ZEITRAUM_FUER_RATELIMIT} Sekunden gesucht werden kann. Wenn
                    dieses Kontingent (von einer anderen Person oder dir) bereits ausgeschöpft
                    wurde, warte bitte ein paar Sekunden und versuche deinen Suchauftrag erneut zu
                    senden. Beachte außerdem, dass die Kleinanzeigen-Website absichtlich etwas
                    langsamer durchsucht wird, um diese nicht unnötig zu belasten.''')            


    def _funk_expander_optionen_bestuecken(self):
        """Sets up options in attribute platzhalter_optionen_01 which
        can be used by the user.
        """
        with self.platzhalter_optionen_01: 
            with streamlit.form('Suchparameter'):
                streamlit.markdown('##### **Suchbegriff:**')
                self.input_suchbegriff = streamlit.text_input(
                    'Suchbegriff eingeben wie auf Kleinanzeigen!:',
                    max_chars=50
                    )

                streamlit.markdown('##### **Anzeigenanzahl:**')
                self.input_stichprobe = streamlit.slider(
                    'Begrenze mit dem Slider die Anzeigenanzahl!:',
                    min_value=25, max_value=constants.N_GRENZE_STICHPROBE_AUFTRAG,
                    value=constants.N_DEFAULT_STICHPROBE_AUFTRAG, step=25
                    )
                
                streamlit.markdown('##### **Max. Anzeigenalter:**')
                self.input_max_anzeigenalter = streamlit.slider(
                    '''(in Tagen): Wähle 0 für heutige Anzeigen (inkl. dauerhafter "TOP"
                    Anzeigen)!:''',
                    min_value=0, max_value=constants.GRENZE_ANZEIGENALTER_AUFTRAG,
                    value=constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG, step=1
                    )
                
                # The code of the if block is only executed in a run of the script if the user
                # pressed the button in the previous run
                if streamlit.form_submit_button(
                    'BUTTON: Suche starten!',
                    on_click=self._funk_on_click_button
                    ):
                        pass

    
    def _funk_on_click_button(self):
        """This function is called before running the script again when
        the button is pressed by the user.
        """
        # Clear Streamlit URL before running the script again
        streamlit.query_params.clear()
        
        # Set session_state['Button_gedrueckt'] = True to tell the eventmanager in the subsequent
        # run of the main script that there are open jobs
        streamlit.session_state['Button_gedrueckt'] = True
        
    
    def funk_feedback_ausgeben(
            self,
            arg_art,
            arg_nachricht: str
            ):
        """Prints feedback in the UI in attribute
        platzhalter_ausgabe_feedback.

        Keyword arguments:\n
        arg_nachricht -- Message to show\n
        arg_art -- Select 'Fehler' pro printing error feedback or
        'Erfolg' for printing success feedback
        """
        with self.platzhalter_ausgabe_feedback:
            if arg_art == 'Fehler':
                streamlit.warning(arg_nachricht)
            elif arg_art == 'Erfolg':
                streamlit.success(arg_nachricht)


    def funk_ergebnisse_ausgeben(
            self,
            **kwargs):
        """Creates all result tabs: one tab for each of the last three
        successfully processed orders sent by the user.
        """
        # If there is nothing to show, return
        if len(streamlit.session_state['Ergebnisse'].keys()) == 0:
             return()
        
        # Elif there are more than 3 tabs with different search terms, delete the oldest one
        elif len(streamlit.session_state['Ergebnisse'].keys()) > 3:
            liste_suchbeggriffe_in_state = list(streamlit.session_state['Ergebnisse'].\
                                                keys())
            liste_suchbeggriffe_in_state.reverse()
            
            for i, x in enumerate (liste_suchbeggriffe_in_state):
                if i > 2:
                    del(streamlit.session_state['Ergebnisse'][x])
        
        liste_namen_tabs = []
        liste_fuer_loop = []

        for key_x, value_x in streamlit.session_state['Ergebnisse'].items():
            suchbegriff = value_x['Suchbegriff']
            liste_namen_tabs.append(f':red[{suchbegriff}]')
            liste_fuer_loop.append(key_x)

        liste_namen_tabs.reverse()
        liste_fuer_loop.reverse()

        with self.platzhalter_ausgabe_ergebnisse:
            self.liste_tabs = streamlit.tabs(liste_namen_tabs)

            # Create one tab for each processed order saved in streamlit.session_state
            for i, x in enumerate(liste_fuer_loop):
                with self.liste_tabs[i]:  
                    if i == 0:              
                        streamlit.markdown('''Hier geht es direkt nach unten zur
                            [Karte 1 (Anzeigenstandorte)](#karte-1-anzeigenstandorte) oder
                            [Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern)](#82fdf71b).
                            ''')
                        streamlit.markdown('''Direkt nach unten zum
                            [Chi-Quadrat-Test](#chi-quadrat-test).''')
                        streamlit.markdown('''Direkt nach unten zu den
                            [Korrelationen als Heatmap](#korrelationen-als-heatmap), der
                            [Clustermap der Korrelationen](#clustermap-der-korrelationen) oder den
                            [Scatterplots der Variablen](#scatterplots-der-variablen).''')
                        streamlit.markdown('Direkt nach unten zu den [Rohdaten](#rohdaten).')
                    
                    aufgetragen_suchbegriff = streamlit.session_state['Ergebnisse'][x]\
                                                ['Suchbegriff'] 
                    aufgetragen_stichprobe = streamlit.session_state['Ergebnisse'][x]\
                                                ['Stichprobe']
                    aufgetragen_max_anzeigenalter = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Max_Anzeigenalter']
                    anzeigenanzahl_manuell_gefunden = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']['Anzeigenanzahl'].\
                                                        sum()
                    anzeigen_in_filtern_gefunden = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']['Anzeigenanzahl_total']\
                                                        .sum()
                    
                    if anzeigenanzahl_manuell_gefunden == aufgetragen_stichprobe:
                        streamlit.write(f'''Du hast für deinen Suchbegriff
                            "_{aufgetragen_suchbegriff}_" nach **{aufgetragen_stichprobe}**
                            Anzeigen gesucht, die maximal {aufgetragen_max_anzeigenalter} Tage alt
                            sein dürfen. Es wurden **{anzeigenanzahl_manuell_gefunden}** Anzeigen
                            gefunden. Wahrscheinlich existieren auf Kleinanzeigen also noch mehr
                            Anzeigen als die von dir angeforderte Menge auf. Es wird jedoch nur die
                            angeforderte Menge in Karte 1 (Anzeigenstandorte) abgebildet.''')
                    elif anzeigenanzahl_manuell_gefunden < aufgetragen_stichprobe:
                        streamlit.write(f'''Du hast für deinen Suchbegriff
                            "_{aufgetragen_suchbegriff}_" nach **{aufgetragen_stichprobe}**
                            Anzeigen gesucht, die maximal {aufgetragen_max_anzeigenalter} Tage alt
                            sein dürfen. Es wurden **{anzeigenanzahl_manuell_gefunden}** Anzeigen
                            gefunden. Somit handelt es sich tatsächlich um die Gesamtmenge aller
                            Anzeigen auf der Kleinanzeigen-Website, die _momentan_ mit den von dir
                            gewählten Suchparametern gefunden werden kann! Diese werden in Karte 1
                            (Anzeigenstandorte) abgebildet.''')

                    streamlit.write('''Für Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern) und die
                        weiteren Auswertungen werden jedoch nicht die Daten aus Karte 1
                        genutzt. Anstatt dessen werden die Angaben aus den Filtern der
                        Kleinanzeigen-Website genutzt, mit welchen die Anzeigen nach
                        (Bundes-)ländern gefiltert werden können. Die Anzahl der Anzeigen in diesen
                        Filtern ist in der Regel größer als die der Anzeigen aus Karte 1
                        (Anzeigenstandorte). Es werden in den Filtern nämlich _alle_ Anzeigen auf
                        Kleinanzeigen unabhängig deiner Einstellungen in den Optionen dieser Web
                        App berücksichtigt. Durch Verwendung dieser größeren Zahlen sind die
                        Auswertungen in Karte 2 und die weiteren Berechnungen aussagekräftiger:''')
                        
                    streamlit.write(f'''Für deinen Suchbegriff "_{aufgetragen_suchbegriff}_" wurden
                        in den Filtern **{anzeigen_in_filtern_gefunden}** Anzeigen gefunden. Im
                        Folgenden wird die Anzeigenzahl, welche auf diesen Filtern beruht, mit
                        "_Anzeigenanzahl_total_" bezeichnet, d. h. die totale Menge der Anzeigen auf
                        Kleinanzeigen für deinen Suchbegriff. Für jedes Bundesland exisitiert also
                        solch ein Wert, der die totale Menge der Anzeigen in diesem Bundesland
                        darstellt.''')
                    streamlit.write('''Mit "_Anzeigenanzahl_" wird lediglich die Menge bezeichnet,
                        die mittels der Suche für Karte 1 gefunden wurde.''')
                    streamlit.markdown('''Eine weitere Erläuterung dieser und weiterer Variablen
                        findest du [unten in der Anleitung](#erlaeuterung-der-variablen).''')

                    streamlit.markdown('### **Karte 1 (Anzeigenstandorte):**')
                    if streamlit.session_state['Ergebnisse'][x]['Karte_Standorte'] != None:
                        streamlit.write('''Klicke auf einen Marker, um den vollen Titel der Anzeige
                            zu lesen! Klickst du dann noch auf diesen vollen Titel, wird sich ein
                            Link zu der Anzeige in einem neuen Tab öffnen!''')
                        folium_static(streamlit.session_state['Ergebnisse'][x]['Karte_Standorte'])
                    elif streamlit.session_state['Ergebnisse'][x]['Karte_Standorte'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung von Karte 1!')
      
                    streamlit.markdown('### **Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern):**')
                    if streamlit.session_state['Ergebnisse'][x]['Karte_Anzeigenquote'] != None:
                        streamlit.write('''Die Farbe des Bundeslands zeigt dir, wie viele Anzeigen
                            je Million Einwohner in diesem Bundesland auf Kleinanzeigen
                            veröffentlicht sind. Die entsprechende Variable heißt
                            "ANZEIGENQUOTE_TOTAL" und ist groß geschrieben, damit du sie schneller
                            in den Auswertungen findest. Bewege den Cursor über das Bundesland, um
                            mehr Variablen zu diesem einzusehen!''')
                        streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                            [unten in der Anleitung](#erlaeuterung-der-variablen).''')
                        streamlit.markdown('''**_HINWEIS:_** Eine interaktive Karte zum Einkommen
                            findest du
                            [hier](https://www.wsi.de/de/einkommen-14582-einkommen-im-regionalen-vergleich-40420.htm)
                            bei der Hans-Böckler-Stiftung (ACHTUNG!: Die Daten im Link sind von
                            2019 und entsprechen nicht den Daten, die in dieser Web App verwendet
                            wurden! Die Quellen externer Daten, die in dieser Web App verwendet
                            wurden, findest du [unten in der Anleitung](#datenquellen)).''')
                        streamlit.markdown('''Eine interaktive Karte zur Alterstruktur der
                            Bundesländer findest du
                            [hier](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Bevoelkerungsstand/karte-altersgruppen.html)
                            beim statistischen Bundesamt (ACHTUNG!: Die Daten im Link sind von
                            2011 und entsprechen nicht den Daten, die in dieser Web App verwendet
                            wurden!).''')
                        
                        folium_static(streamlit.session_state['Ergebnisse'][x]\
                                      ['Karte_Anzeigenquote']
                                      )
                    elif streamlit.session_state['Ergebnisse'][x]['Karte_Anzeigenquote'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung von Karte 2!')

                    streamlit.markdown('### **Chi-Quadrat-Test:**')
                    if streamlit.session_state['Ergebnisse'][x]['Chi_Quadrat'] != None:
                        streamlit.write('''Mit dem
                        [Chi-Quadrat-Test](https://de.wikipedia.org/wiki/Chi-Quadrat-Test) wird
                        geprüft, ob sich die Anzeigen auf alle Bundesländer gleich verteilen (unter
                        Berücksichtigung der Einwohnerzahl). Eine solche Gleichverteilung würde
                        sich darin äußern, dass alle Bundesländer in der obigen Karte 2 gleich
                        gefärbt wären. Ein _p_-Wert < .05 signalisiert eine Ungleichverteilung.
                        Beachte dabei bitte aber, dass bei Suchbegriffen mit hunderten Anzeigen die
                        Stichprobe sehr groß ist, sodass ein signifikantes Ergebnis (d. h. eine
                        Ungleichverteilung) auch zu erwarten ist.''')
                            
                        ergebnis_chi_quadrat = streamlit.session_state['Ergebnisse'][x]\
                                                ['Chi_Quadrat']
                        a = ergebnis_chi_quadrat['Freiheitsgrade']
                        b = ergebnis_chi_quadrat['Stichprobe']
                        c = "{:.2f}".format(ergebnis_chi_quadrat['Chi_Quadrat'])
                        d = "{:.2f}".format(ergebnis_chi_quadrat['p_Wert']).lstrip('0')

                        if ergebnis_chi_quadrat['p_Wert'] >= 0.01:
                            streamlit.write(r'$\chi^2$', f'({a}, _N_ = {b}) = {c}, _p_ = {d}')
                        elif ergebnis_chi_quadrat['p_Wert'] < 0.01:
                            streamlit.write(r'$\chi^2$', f'({a}, _N_ = {b}) = {c}, _p_ < .01')
                    elif streamlit.session_state['Ergebnisse'][x]['Chi_Quadrat'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Berechnung des Chi-Quadrat-Tests!')
                            
                    streamlit.markdown('### **Korrelationen als Heatmap:**')
                    if streamlit.session_state['Ergebnisse'][x]['Heatmap'] != None:
                        streamlit.markdown('''Die Variable "ANZEIGENQUOTE_TOTAL" aus Karte 2 ist in
                            der letzten Zeile der Heatmap zu finden. Aufgrund der geringen
                            "Stichprobe" aus 16 Bundesländern wurden
                            [Rangkorrelationen](https://de.wikipedia.org/wiki/Rangkorrelationskoeffizient)
                            berechnet. Korrelationen ab ±.53 sind mit einem _p_ < .05 signifikant
                            (2-seitig). Beachte aber bitte die
                            [Scatterplots unten](#scatterplots-der-variablen), um die Verteilungen
                            der Variablen in deine Interpretationen einzubeziehen. Sowohl die
                            Heatmap als auch die Scatterplots beruhen auf Daten, die du
                            [unten in einer Tabelle](#rohdaten) einsehen kannst.''')
                        streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                            [unten in der Anleitung](#erlaeuterung-der-variablen).''')
                        streamlit.image(streamlit.session_state['Ergebnisse'][x]['Heatmap'])
                    elif streamlit.session_state['Ergebnisse'][x]['Heatmap'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung der Heatmap!')                    
                         
                    streamlit.markdown('### **Clustermap der Korrelationen:**') 
                    if streamlit.session_state['Ergebnisse'][x]['Clustermap'] != None:
                        streamlit.markdown('''Mit der
                            [Clusteranalyse](https://de.wikipedia.org/wiki/Clusteranalyse) wird in
                            unserem Fall die Ähnlichkeit der Variablen bezüglich ihrer
                            Korrelationen mit anderen Variablen untersucht. Die Korrelationen sind
                            dieselben wie oben in der Heatmap. Variablen mit ähnlichen
                            Korrelationsmustern bilden ein Cluster und werden
                            ["zusammengefasst"](https://seaborn.pydata.org/generated/seaborn.clustermap.html).
                            Nach und nach entstehen so größere Cluster. Um dies visualisieren zu
                            können, ist die Reihenfolge der Zeilen und Spalten in der Clustermap
                            evtl. anders als in der Heatmap!''')         
                        streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                            [unten in der Anleitung](#erlaeuterung-der-variablen).''')
                        streamlit.image(streamlit.session_state['Ergebnisse'][x]['Clustermap'])
                    elif streamlit.session_state['Ergebnisse'][x]['Clustermap'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung der Clustermap!')
                        
                    streamlit.markdown('### **Scatterplots der Variablen:**')
                    if streamlit.session_state['Ergebnisse'][x]['Scatterplots'] != None:
                        streamlit.markdown('''In den Scatterplots sind nur die relevantesten
                        Variablen aufgeführt. Jeder kleine Punkt repräsentiert eines der 16
                        Bundesländer. Die Histogramme in der Diagonalen entsprechen den
                        Verteilungen der Variablen. Auch hierbei beruht zwar je ein Histogramm auf
                        16 Datenpunkten, die Beschriftung der Y-Achse ist aber bei den Histogrammen
                        nicht zu beachten. Es handelt sich nämlich bei allen Histogrammen um
                        Häufigkeiten.''')
                        streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                            [unten in der Anleitung](#erlaeuterung-der-variablen).''')
                        streamlit.image(streamlit.session_state['Ergebnisse'][x]['Scatterplots']) 
                    elif streamlit.session_state['Ergebnisse'][x]['Scatterplots'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung der Scatterplots!')
                    
                    streamlit.markdown('### **Rohdaten:**') 
                    try:
                        if streamlit.session_state['Ergebnisse'][x]['Frame_Bericht'] == None:
                            streamlit.write('ACHTUNG!: Fehler bei Erstellung der Rohdaten!')
                    except Exception as Fehler:
                        helpers.funk_drucken('########## ACHTUNG!: Fehler beim Zeigen der '
                            'Rohdaten:')
                        helpers.funk_drucken(Fehler)

                        if streamlit.session_state['Ergebnisse'][x]['Frame_Bericht'].empty == False: 
                            streamlit.markdown('''Dunkelrote Zellen repräsentieren hohe Werte in
                                der jeweiligen Spalte. Die Tabelle lässt sich durch einen Klick auf
                                einen Spaltenname sortieren. Im Moment ist sie alphabetisch nach
                                den Namen der Länder sortiert. Um die Tabelle zu vergrößern, führe
                                den Cursor über die Tabelle und klicke oben rechts auf das Symbol
                                zum Vergrößern!''')
                            streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                                [unten in der Anleitung](#erlaeuterung-der-variablen).''')
                            streamlit.write('''Die Quellen externer Daten findest du
                                [unten in der Anleitung](#datenquellen).''')
                            
                            colormap = seaborn.light_palette("#ae272d", as_cmap=True)
                            frame_bericht_geladen = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']
                            
                            format = {'Alter_Mittelwert': '{:.2f}',
                                      'Alter_0_17': '{:.2f}',
                                      'Alter_18_65': '{:.2f}',
                                      'Alter_66_100': '{:.2f}',
                                      'Anzeigenquote': '{:.2f}',
                                      'Anzeigenanzahl_erwartet': '{:.2f}',
                                      'Gewicht_Einwohnerzahl': '{:.3f}'
                                      }
                            
                            def funk_schriftfarbe_anpassen(arg_x):
                                """Function for setting font color in streamlit.dataframe."""
                                if type(arg_x) == str:
                                    return()
                                else:
                                    farbe = 'black'
                                    return(f'color: {farbe}')

                            streamlit.dataframe(frame_bericht_geladen.\
                                                style.background_gradient(cmap=colormap).\
                                                applymap(funk_schriftfarbe_anpassen).\
                                                format(format)
                                                )

                    time.sleep(0.1)
            
    
    def funk_jobs_pruefen(self):
        """Checks whether there are open jobs, i. e. whether the button
        was pressed by the user.
        """    
        if streamlit.session_state['Button_gedrueckt'] == True:
            # Tell the eventmanager that the button was pressed by the user
            self.eventmanager.funk_event_eingetreten(
                arg_event_name='Button_gedrueckt',
                arg_argumente_von_event={
                    'arg_auftrag_suchbegriff': self.input_suchbegriff,
                    'arg_auftrag_stichprobe': self.input_stichprobe,
                    'arg_auftrag_max_anzeigenalter': self.input_max_anzeigenalter,
                    }
                )
            

    def funk_aufraeumen(
            self,
            **kwargs):
        """Cleans up and stops the script from running."""
        self.platzhalter_ausgabe_spinner_02.empty()
        
        streamlit.session_state['Button_gedrueckt'] = False

        self.platzhalter_ausgabe_spinner_01.empty()

        UserInterface._funk_scrollen(arg_element='div.st-emotion-cache-18kf3ut')

        streamlit.stop()


    @staticmethod
    def _funk_scrollen(
            arg_element,
            ):
        """Scrolls page element in argument arg_element into view.
        
        Keyword arguments:\n
        arg_element -- HTML element to scroll to
        """
        dummy = datetime.datetime.now().timestamp()
        
        import_komponenten.html(
            html=
                f"""
                    <!--<p>{dummy}</p>-->
                    <script>
                        window.parent.document.querySelector('{arg_element}').scrollIntoView();
                    </script>
                """,
            height=1
            )
