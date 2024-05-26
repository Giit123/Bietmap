"""This module contains the class User_Interface.

Classes:\n
    User_Interface -- An instance of this class can perform all UI
    related actions in the web app.
"""

# %%
###################################################################################################
import streamlit
import streamlit.components.v1 as Komponenten
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
import Constants
from Eventmanager import Eventmanager
import Helpers


# %%
###################################################################################################
class User_Interface:
    """An instance of this class can perform all UI related actions in
    the web app.

    Attributes:\n
        CAUTION!: All attributes should be used as private ones despite
        not being prefixed with an underscore.\n
        Eventmanager -- Instance of Eventmanager to work with\n
        Spalte_A, Spalte_B -- Invisible columns in which elements can
        be inserted\n
        Expander_Optionen -- Equippable expander element on the left
        side of the UI for options\n
        Expander_Ausgabe -- Equippable expander element on the upper
        side of the UI for the results of the user's orders\n
        Expander_Anleitung -- Equippable expander element on the lower
        side of the UI for the manual\n
        Platzhalter -- All attributes which have "Platzhalter" in their
        name are streamlit objects which can be equipped with objects
        that should be displayed to the user\n
        Input_Suchbegriff -- Search term currenty typed in by the user
        in the UI\n
        Input_Stichprobe -- Sample size currently selected by the user
        in the UI\n
        Input_Max_Anzeigenalter -- Maximum age of offers (in days) which
        should be included in the scraped sample selected by the user
        in the UI\n
        Liste_Tabs -- List with tabs, each for one of the last three
        successfully processed orders sent by the user
        
    Public methods:\n
        Funk_Einrichten -- Sets up user interface.\n
        Funk_Feedback_ausgeben -- Prints feedback in the UI in attribute
        Platzhalter_Ausgabe_Feedback.\n
        Funk_Ergebnisse_ausgeben -- Creates all result tabs: one tab for
        each of the last three successfully processed orders sent by the
        user.\n
        Funk_Jobs_pruefen -- Checks whether there are open jobs, i. e.
        the button was pressed by the user.\n
        Funk_Aufraeumen -- Cleans up and stops stopping the script from
        running.

    Private methods:\n
        _Funk_Dateien_abfragen -- Loads necessary files into
        streamlit.session_state.\n
        _Funk_Header_erstellen -- Returns new header for web requests.
        _Funk_Startseite_einrichten -- Sets up basic user interface
        template.\n
        _Funk_Geruest_erstellen -- Creates elements for basic user
        interface template.\n
        _Funk_Expander_Optionen_bestuecken -- SSets up options in
        attribute Platzhalter_Optionen_01 which can be used by the
        user.\n
        _Funk_on_click_Button -- This function is called when the
        button is pressed by the user.\n
        _Funk_Scrollen -- Scrolls page element in argument
        Arg_Element into view.
    """

    def __init__(
            self,
            Init_Eventmanager: Eventmanager
            ):
        """Inits User_Interface.

        Keyword arguments:\n
        Init_Eventamanager -- Active instance of class Eventmanager
        """
        self.Eventmanager = Init_Eventmanager
        
        self.Spalte_A = None
        self.Spalte_B = None
        self.Expander_Optionen = None
        self.Platzhalter_Optionen_01 = None
        self.Expander_Ausgabe = None
        self.Platzhalter_Ausgabe_Spinner_01 = None
        self.Platzhalter_Ausgabe_Spinner_02 = None
        self.Platzhalter_Ausgabe_Feedback = None
        self.Platzhalter_Ausgabe_Ergebnisse = None
        self.Expander_Anleitung = None
        self.Platzhalter_Anleitung_01 = None
        self.Input_Suchbegriff = None
        self.Input_Stichprobe = None
        self.Input_Max_Anzeigenalter = None
        self.Liste_Tabs = None


    def Funk_Einrichten(self):
        """Sets up user interface."""
        # First loading of the web app by the user
        if 'User_Interface_eingerichtet' not in streamlit.session_state:
            self._Funk_Startseite_einrichten()

            # Create variables in streamlit.session_state for storing between runs
            User_Interface._Funk_Dateien_abfragen()
            streamlit.session_state['Header'] = User_Interface._Funk_Header_erstellen()
            streamlit.session_state['Button_gedrueckt'] = False
            streamlit.session_state['Flagge_Ergebnis_gespeichert'] = False
            streamlit.session_state['Ergebnisse'] = {}

            streamlit.session_state['User_Interface_eingerichtet'] = 'Startseite'

        elif streamlit.session_state['Button_gedrueckt'] == True:
            self._Funk_Startseite_einrichten()

        else:
            self._Funk_Startseite_einrichten()


    @staticmethod
    def _Funk_Dateien_abfragen():
        """Loads necessary files into streamlit.session_state."""
        with open('Buch_PLZs.json', encoding='utf-8') as Datei:
            Buch_PLZs = json.load(Datei)
            streamlit.session_state['Buch_PLZs'] = Buch_PLZs
        
        with open('Geojson_Laender.geojson', encoding='utf-8') as Datei:
            Geojson_Laender = json.load(Datei)
            Geojson_Laender = json.dumps(Geojson_Laender)
            streamlit.session_state['Geojson_Laender'] = Geojson_Laender

        with open('Buch_Laender.json', encoding='utf-8') as Datei:
            Buch_Laender = json.load(Datei)
            streamlit.session_state['Buch_Laender'] = Buch_Laender


    @staticmethod
    def _Funk_Header_erstellen():
        """Returns new header for web requests."""
        Zufall_FirefoxVersion = float(random.randint(94, 98))

        Liste_Neu_Header_UserAgent = [
                                    [1.0, f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{Zufall_FirefoxVersion}) Gecko/20100101 Firefox/{Zufall_FirefoxVersion}']
                                    ]

        Zufallszahl = random.uniform(0,1)
        for x in Liste_Neu_Header_UserAgent:
            if x[0] >= Zufallszahl:
                Neu_Header_UserAgent = x[1]
                break

        Liste_Neu_Header_Referer = [
                                    [0.7, 'https://www.google.com/'],
                                    [1.0, 'https://www.bing.com/']
                                   ]

        Zufallszahl = random.uniform(0,1)
        for x in Liste_Neu_Header_Referer:
            if x[0] >= Zufallszahl:
                Neu_Header_Referer = x[1]
                break
                
        Header = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
                'Referer': Neu_Header_Referer,
                'User-Agent': Neu_Header_UserAgent
                }
        
        return(Header)
    

    def _Funk_Startseite_einrichten(self):
        """Sets up basic user interface template."""
        self._Funk_Geruest_erstellen()
        self._Funk_Expander_Optionen_bestuecken()

    
    def _Funk_Geruest_erstellen(self):
        """Creates elements for basic user interface template."""
        self.Spalte_A, self.Spalte_B = streamlit.columns((10, 35))

        with self.Spalte_A:
            self.Expander_Optionen = streamlit.expander('Optionen:', expanded=True)

            with self.Expander_Optionen:
                self.Platzhalter_Optionen_01 = streamlit.empty()

        with self.Spalte_B:
            self.Expander_Ausgabe = streamlit.expander('Ausgabe:', expanded=True)

            with self.Expander_Ausgabe:
                self.Platzhalter_Ausgabe_Spinner_01 = streamlit.empty()
                self.Platzhalter_Ausgabe_Spinner_02 = streamlit.empty()
                self.Platzhalter_Ausgabe_Feedback = streamlit.empty()
                self.Platzhalter_Ausgabe_Ergebnisse = streamlit.empty()

            # Scroll to expander with the name self.Expander_Ausgabe
            User_Interface._Funk_Scrollen(Arg_Element='div.st-emotion-cache-1bt9eao')
            
            self.Expander_Anleitung = streamlit.expander('Anleitung:', expanded=True)

            with self.Expander_Anleitung:
                self.Platzhalter_Anleitung_01 = streamlit.empty()

                streamlit.markdown('### **Willkommen bei Bietmap!**')
                streamlit.markdown('''Mit dieser Web App kannst du nach Kleinanzeigen in ganz
                    Deutschland suchen und deren Standorte auf einer Karte anzeigen lassen.
                    So kannst du etwa untersuchen, ob bestimmte Artikel in deinem Bundesland
                    häufiger angeboten werden als in einem anderen. Nutze dazu die Optionen.
                    Auf dem Handy musst du nach oben scrollen, um die Optionen zu sehen,
                    [hierhin](#suchbegriff). Die Optionen werden gleich erklärt.
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
                streamlit.write('''Dein Suchbegriff wird automatisch in Kleinbuchstaben
                    umgewandelt!''')
                streamlit.write('''Auf folgenden Einstellungen werden die Anzeigen für Karte 1
                    (Anzeigenstandorte) beruhen, aber nicht für Karte 2
                    (ANZEIGENQUOTE_TOTAL in Bundesländern)!
                    [Zur Erläuterung der Karten](#5ac7a061).''')
                streamlit.write('''_Anzeigenanzahl:_ Hier kannst du festlegen, wie viele Anzeigen
                    maximal in deine Stichprobe aufgenommen werden sollen!''')
                streamlit.write('''_Max. Anzeigenalter:_ Hier kannst du festlegen, wie alt die
                    gefundenen Anzeigen maximal sein dürfen (in Tagen). Die Anzeigen werden nach
                    ihrer Aktualität sortiert und in entsprechender Reihenfolge in deine Stichprobe
                    aufgenommen!''')

                streamlit.markdown('#### **Erläuterung der Karten:**')
                streamlit.write('''Die Ergebnisse deiner Suche werden auf zwei
                    verschiedenen Karten visualisiert:''')
                streamlit.write('''_Karte 1 (Anzeigenstandorte):_ Hier wird dir jede gefundene
                    Anzeige als Marker auf der Deutschlandkarte angezeigt. Falls viele Anzeigen in
                    einer Stadt gefunden worden sind, musst du vielleicht etwas in die Karte
                    reinzoomen, um die Marker zu unterscheiden! Die Anzeigenstandorte bzw. Marker
                    werden automatisiert anhand der Postleitzahl eingefügt. Dazu wird eine Datei
                    mit Geodaten verwendet, die jeder Postleitzahl genau einen Standort zuordnet.
                    Die Marker befinden sich also nicht immer _exakt_ an den Standorten /
                    Stadtteilen der Anzeigen!''')
                streamlit.write('''_Karte 2 (ANZEIGENQUOTE_TOTAL in Bundesländern):_ Hier werden
                    dir je Bundesland die gefundenen Anzeigen pro Million Einwohner angezeigt.
                    Da sich die Bundesländer bzw. deren Einwohner aber auch in weiteren
                    [Variablen](#4da307ae) unterscheiden, biete sich vielfältige
                    Interpretationsmöglichkeiten. Überlege dir z. B., welchen Einfluss die
                    Einwohnerdichte, die Alterstruktur oder das Einkommen auf die Ergebnisse zu
                    deinem spezifischen Artikel haben könnten. Deshalb bekommst in den weiteren
                    Auswertungen auch einen Einblick in diese Variablen.''')
                streamlit.write('''Zudem wird dir auch eine Tabelle mit den Rohdaten deines
                    Auftrags angezeigt. Die Datenquellen externer Daten findest du
                    [unten](#datenquellen).''')
                
                streamlit.markdown('#### **Erläuterung der Variablen:**')
                streamlit.write('''**_Die Auflistung erfolgt in alphabetischer Reihenfolge!
                    Die Variablen beziehen sich jeweils auf ein Bundesland. Die Datenquellen
                    externer Daten findest du [unten](#datenquellen)._**''')
                streamlit.write('''_Alter_0_17_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter bis einschließlich 17 Jahren.''')
                streamlit.write('''_Alter_18_65_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter von 18 bis 65 Jahren.''')
                streamlit.write('''_Alter_66_100_: Prozentualer Anteil der Bevölkerung mit einem
                    Alter von mindestens 66 Jahren.''')
                streamlit.write('_Alter_Mittelwert_: Mittelwert des Alters über alle Personen.')
                streamlit.write('''_Anzeigenanzahl_: Dies ist die absolute Anzeigenzahl, welche
                    durch die Suche mit den von dir eingestellten Parametern in den Optionen
                    gefunden wurde. Dies Anzahl von Anzeigen erscheint in Karte 1
                    (Anzeigenstandorte).''')
                streamlit.write('''_Anzeigenanzahl_erwartet_: siehe zunächst Definition
                    der Variable "Anzeigenanzahl". Die erwartete Anzeigenanzahl
                    wäre die, wenn sich alle gefundenen Anzeigen in Deutschland gleich auf die
                    Bundesländer verteilen würden (unter Berücksichtigung der Einwohnerzahl).''')
                streamlit.write('''_Anzeigenanzahl_total_: Dies ist die absolute Anzeigenzahl,
                    welche auf den Angaben aus den Filtern der Kleinanzeigen-Website beruht.
                    Hier werden also _alle_ Anzeigen berücksichtigt, die auf Kleinanzeigen für
                    deinen Suchbegriff gefunden worden.''')
                streamlit.write('''_Anzeigenanzahl_total_erwartet_: siehe zunächst Definition
                    der Variable "Anzeigenanzahl_total". Die erwartete Anzeigenanzahl_total
                    wäre die, wenn sich alle gefundenen Anzeigen in Deutschland (aus den Filtern)
                    gleich auf die Bundesländer verteilen würden (unter Berücksichtigung der
                    Einwohnerzahl).''')
                streamlit.write('''_Anzeigenquote_: Dies ist der Quotient aus der Variable
                    "Anzeigenanzahl" und der Variable "Einwohnerzahl" multipliziert mit 1000000.
                    Dies ist somit die Anzahl der Anzeigen pro Million Einwohner. Diese Zahl
                    ist aber bei kaum aussagekräftig, da sie auf maximal 100 Anzeigen basiert.''')
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
                    wird, weil mehr dort Menschen auf geringem Raum wohnen und / oder mehr junge
                    Menschen dort leben, ist nicht klar. Auf eine direkte Kausalität kann daher
                    ohne Weiteres nicht geschlossen werden. Insbesondere gilt dies auch für
                    Interpretationen hinsichtlich West vs. Ost: Menschen im Westen sind im Mittel
                    jünger _und_ verdienen mehr _und_ leben eher in Ballungsgebieten. Dies kannst
                    du auch in der Heatmap, der Clustermap und in den Rohdaten erkennen.''')
                streamlit.write('''_Rolex_: Hamburg hat die höchste ANZEIGENQUOTE_TOTAL.
                    Dort ist auch die Millionärsdichte in Deutschland am höchsten,
                    [hier](https://www.ndr.de/nachrichten/hamburg/Neue-Statistik-Groesste-Millionaersdichte-in-Hamburg,millionaere188.html)
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
                    [Karte 1](#5ac7a061) stammen von
                    [hier](https://github.com/zauberware/postal-codes-json-xml-csv).
                    ''')
                streamlit.write('''Die Geodaten für die Ländergrenzen in
                    [Karte 2](#5ac7a061) stammen von
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
                    Variable "Alter_Mittelwert") wurden auf statista gefunden, Stand 2022, und
                    lassen sich
                    [hier](https://de.statista.com/statistik/daten/studie/1093993/umfrage/durchschnittsalter-der-bevoelkerung-in-deutschland-nach-bundeslaendern/)
                    finden.''')
                streamlit.write('''Alle Daten hinsichtlich der Altersgruppen (d. h. für die
                    Variablen "Alter_0_17" etc.) wurden mit Hilfe von Daten aus dem
                    Deutschlandatlas berechnet, Stand 2021, und lassen sich
                    [hier](https://www.deutschlandatlas.bund.de/DE/Karten/Wer-wir-sind/030-Altersgruppen-der-Bevoelkerung.html)
                    finden (Tabellenblatt "Deutschlandatlas_KRS1221").''')

                streamlit.markdown('#### **!!!!! HINWEIS ZUM RATE LIMITING !!!!!:**')
                streamlit.write(f'''Die Suchrate ist so beschränkt, dass über _alle aktiven
                    Appnutzer/innen summiert_ nach maximal {Constants.N_FUER_RATELIMIT} Anzeigen
                    pro {Constants.ZEITRAUM_FUER_RATELIMIT} Sekunden gesucht werden kann. Wenn
                    dieses Kontingent (von einer anderen Person oder dir) bereits ausgeschöpft
                    wurde, warte bitte ein paar Sekunden und versuche deinen Suchauftrag erneut zu
                    senden. Beachte außerdem, dass die Kleinanzeigen-Website absichtlich etwas
                    langsamer durchsucht wird, um diese nicht unnötig zu belasten.''')
            
                
    def _Funk_Expander_Optionen_bestuecken(self):
        """Sets up options in attribute Platzhalter_Optionen_01 which
        can be used by the user.
        """
        with self.Platzhalter_Optionen_01: 
            with streamlit.form('Suchparameter'):
                streamlit.markdown('##### **Suchbegriff:**')
                self.Input_Suchbegriff = streamlit.text_input(
                    'Suchbegriff eingeben wie auf Kleinanzeigen!:',
                    max_chars=50
                    )

                streamlit.markdown('##### **Anzeigenanzahl:**')
                self.Input_Stichprobe = streamlit.slider(
                    'Begrenze mit dem Slider die Anzeigenanzahl!:',
                    min_value=25, max_value=Constants.N_GRENZE_STICHPROBE_AUFTRAG,
                    value=Constants.N_DEFAULT_STICHPROBE_AUFTRAG, step=25
                    )
                
                streamlit.markdown('##### **Max. Anzeigenalter:**')
                self.Input_Max_Anzeigenalter = streamlit.slider(
                    '''(in Tagen): Wähle 0 für heutige Anzeigen (inkl. dauerhafter "TOP"
                    Anzeigen)!:''',
                    min_value=0, max_value=Constants.GRENZE_ANZEIGENALTER_AUFTRAG,
                    value=Constants.DEFAULT_MAX_ANZEIGENALTER_AUFTRAG, step=1
                    )
                
                # The code of the if block is only executed in a run of the script if the user
                # pressed the button in the previous run
                if streamlit.form_submit_button(
                    'BUTTON: Suche starten!',
                    on_click=self._Funk_on_click_Button
                    ):
                        pass

    
    def _Funk_on_click_Button(self):
        """This function is called before running the script again when
        the button is pressed by the user.
        """
        # Clear Streamlit URL before running the script again
        streamlit.query_params.clear()
        
        # Set session_state['Button_gedrueckt'] = True to tell the Eventamanager in the subsequent
        # run of the main script that there are open jobs
        streamlit.session_state['Button_gedrueckt'] = True
        
    
    def Funk_Feedback_ausgeben(
            self,
            Arg_Art,
            Arg_Nachricht: str
            ):
        """Prints feedback in the UI in attribute
        Platzhalter_Ausgabe_Feedback.

        Keyword arguments:\n
        Arg_Nachricht -- Message to show\n
        Arg_Art -- Select 'Fehler' pro printing error feedback or
        'Erfolg' for printing success feedback
        """
        with self.Platzhalter_Ausgabe_Feedback:
            if Arg_Art == 'Fehler':
                streamlit.warning(Arg_Nachricht)
            elif Arg_Art == 'Erfolg':
                streamlit.success(Arg_Nachricht)


    def Funk_Ergebnisse_ausgeben(
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
            Liste_Suchbeggriffe_in_state = list(streamlit.session_state['Ergebnisse'].\
                                                keys())
            Liste_Suchbeggriffe_in_state.reverse()
            
            for i, x in enumerate (Liste_Suchbeggriffe_in_state):
                if i > 2:
                    del(streamlit.session_state['Ergebnisse'][x])
        
        Liste_Namen_Tabs = []
        Liste_fuer_Loop = []

        for Key_x, Value_x in streamlit.session_state['Ergebnisse'].items():
            Suchbegriff = Value_x['Suchbegriff']
            Liste_Namen_Tabs.append(f':red[{Suchbegriff}]')
            Liste_fuer_Loop.append(Key_x)

        Liste_Namen_Tabs.reverse()
        Liste_fuer_Loop.reverse()

        with self.Platzhalter_Ausgabe_Ergebnisse:
            self.Liste_Tabs = streamlit.tabs(Liste_Namen_Tabs)

            # Create one tab for each processed order saved in streamlit.session_state
            for i, x in enumerate(Liste_fuer_Loop):
                with self.Liste_Tabs[i]:  
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
                    
                    Aufgetragen_Suchbegriff = streamlit.session_state['Ergebnisse'][x]\
                                                ['Suchbegriff'] 
                    Aufgetragen_Stichprobe = streamlit.session_state['Ergebnisse'][x]\
                                                ['Stichprobe']
                    Aufgetragen_Max_Anzeigenalter = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Max_Anzeigenalter']
                    Anzeigenanzahl_manuell_gefunden = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']['Anzeigenanzahl'].\
                                                        sum()
                    Anzeigen_in_Filtern_gefunden = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']['Anzeigenanzahl_total']\
                                                        .sum()
                    
                    if Anzeigenanzahl_manuell_gefunden == Aufgetragen_Stichprobe:
                        streamlit.write(f'''Du hast für deinen Suchbegriff
                            "_{Aufgetragen_Suchbegriff}_" nach **{Aufgetragen_Stichprobe}**
                            Anzeigen gesucht, die maximal {Aufgetragen_Max_Anzeigenalter} Tage alt
                            sein dürfen. Es wurden **{Anzeigenanzahl_manuell_gefunden}** Anzeigen
                            gefunden. Wahrscheinlich existieren also noch mehr Anzeigen als die
                            gefundene Menge auf Kleinanzeigen. Es wird jedoch nur die gefundene
                            Menge in Karte 1 (Anzeigenstandorte) abgebildet.''')
                    elif Anzeigenanzahl_manuell_gefunden < Aufgetragen_Stichprobe:
                        streamlit.write(f'''Du hast für deinen Suchbegriff
                            "_{Aufgetragen_Suchbegriff}_" nach **{Aufgetragen_Stichprobe}**
                            Anzeigen gesucht, die maximal {Aufgetragen_Max_Anzeigenalter} Tage alt
                            sein dürfen. Es wurden **{Anzeigenanzahl_manuell_gefunden}** Anzeigen
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
                        Kleinanzeigen unabhängig deiner Einstellungen in dieser Web App
                        berücksichtigt. Durch Verwendung dieser größeren Zahlen sind die
                        Auswertungen in Karte 2 und den anderen Abbildungen aussagekräftiger.
                        ''')
                        
                    streamlit.write(f'''Für deinen Suchbegriff "_{Aufgetragen_Suchbegriff}_" wurden
                        in den Filtern **{Anzeigen_in_Filtern_gefunden}** Anzeigen gefunden. Im
                        Folgenden wird die Anzeigenzahl, welche auf den Filtern beruht, mit
                        "_Anzeigenanzahl_total_" bezeichnet, d. h. die totale Menge der Anzeigen auf
                        Kleinanzeigen für deinen Suchbegriff. Für jedes Bundesland exisitiert also
                        solch ein Wert, der die totale Menge der Anzeigen in diesem Bundesland
                        darstellt. Mit "_Anzeigenanzahl_" wird lediglich die Menge bezeichnet, die
                        mittels der Suche für Karte 1 gefunden wurde.''')
                    streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                        [unten in der Anleitung](#4da307ae).''')

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
                            [unten in der Anleitung](#4da307ae).''')
                        streamlit.markdown('''**_HINWEIS:_** Eine interaktive Karte zum Einkommen
                            findest du
                            [hier](https://www.wsi.de/de/einkommen-14582-einkommen-im-regionalen-vergleich-40420.htm)
                            bei der Hans-Böckler-Stiftung (ACHTUNG!: Die Daten im Link stammen aus
                            2019 und entsprechen nicht den Daten, die in dieser Web App verwendet
                            wurden!).''')
                        streamlit.markdown('''Eine interaktive Karte zur Alterstruktur der
                            Bundesländer findest du
                            [hier](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Bevoelkerungsstand/karte-altersgruppen.html)                  
                            beim statistischen Bundesamt (ACHTUNG!: Die Daten im Link stammen aus
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
                        [Chi-Quadrat-Test](https://de.wikipedia.org/wiki/Chi-Quadrat-Test) wird die
                        Hypothese getestet, dass sich die Anzeigen auf alle Bundesländer gleich
                        verteilen (unter Berücksichtigung der Einwohnerzahl). Eine solche
                        Gleichverteilung würde sich darin äußern, dass alle Bundesländer in der
                        obigen Karte 2 gleich gefärbt wären. Ein _p_-Wert < .05 signalisiert eine
                        Ungleichverteilung. Beachte dabei bitte aber, dass bei Suchbegriffen mit
                        hunderten Anzeigen die Stichprobe sehr groß ist, sodass ein signifikantes
                        Ergebnis (d. h. eine Ungleichverteilung) auch zu erwarten ist.''')
                            
                        Ergebnis_Chi_Quadrat = streamlit.session_state['Ergebnisse'][x]\
                                                ['Chi_Quadrat']
                        a = Ergebnis_Chi_Quadrat['Freiheitsgrade']
                        b = Ergebnis_Chi_Quadrat['Stichprobe']
                        c = "{:.2f}".format(Ergebnis_Chi_Quadrat['Chi_Quadrat'])
                        d = "{:.2f}".format(Ergebnis_Chi_Quadrat['p_Wert']).lstrip('0')

                        if Ergebnis_Chi_Quadrat['p_Wert'] >= 0.01:
                            streamlit.write(r'$\chi^2$', f'({a}, _N_ = {b}) = {c}, _p_ = {d}')
                        elif Ergebnis_Chi_Quadrat['p_Wert'] < 0.01:
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
                            [unten in der Anleitung](#4da307ae).''')
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
                            [unten in der Anleitung](#4da307ae).''')
                        streamlit.image(streamlit.session_state['Ergebnisse'][x]['Clustermap'])
                    elif streamlit.session_state['Ergebnisse'][x]['Clustermap'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung der Clustermap!')
                        
                    streamlit.markdown('### **Scatterplots der Variablen:**')
                    if streamlit.session_state['Ergebnisse'][x]['Scatterplots'] != None:
                        streamlit.markdown('''In den Scatterplots sind nur die relevantesten
                        Variablen aufgeführt. Jeder kleine Punkt repräsentiert eines der 16
                        Bundesländer. Die Histogramme in der Diagonalen entsprechen den
                        Verteilungen der Variablen. Auch hierbei beruht je ein Histogramm zwar auf
                        16 Datenpunkten, die Beschriftung der Y-Achse ist aber bei den Histogrammen
                        nicht zu beachten. Es handelt sich nämlich bei allen Histogrammen um
                        Häufigkeiten.''')
                        streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                            [unten in der Anleitung](#4da307ae).''')
                        streamlit.image(streamlit.session_state['Ergebnisse'][x]['Scatterplots']) 
                    elif streamlit.session_state['Ergebnisse'][x]['Scatterplots'] == None:
                        streamlit.write('ACHTUNG!: Fehler bei Erstellung der Scatterplots!')
                    
                    streamlit.markdown('### **Rohdaten:**') 
                    try:
                        if streamlit.session_state['Ergebnisse'][x]['Frame_Bericht'] == None:
                            streamlit.write('ACHTUNG!: Fehler bei Erstellung der Rohdaten!')
                    except Exception as Fehler:
                        Helpers.Funk_Drucken('########## ACHTUNG!: Fehler beim Zeigen der '
                            'Rohdaten:')
                        Helpers.Funk_Drucken(Fehler)

                        if streamlit.session_state['Ergebnisse'][x]['Frame_Bericht'].empty == False: 
                            streamlit.markdown('''Dunkelrote Zellen repräsentieren hohe Werte in
                                der jeweiligen Spalte. Die Tabelle lässt sich durch einen Klick auf
                                einen Spaltenname sortieren. Im Moment ist sie alphabetisch nach
                                den Namen der Länder sortiert. Um die Tabelle zu vergrößern, führe
                                den Cursor über die Tabelle und klicke oben rechts auf das Symbol
                                zum Vergrößern!''')
                            streamlit.markdown('''Eine weitere Erläuterung der Variablen findest du
                                [unten in der Anleitung](#4da307ae).''')
                            streamlit.write('''Die Datenquellen externer Daten findest du
                                [unten in der Anleitung](#datenquellen).''')
                            
                            Colormap = seaborn.light_palette("#ae272d", as_cmap=True)
                            Frame_Bericht_geladen = streamlit.session_state['Ergebnisse'][x]\
                                                        ['Frame_Bericht']
                            
                            Format = {'Alter_Mittelwert': '{:.2f}',
                                      'Alter_0_17': '{:.2f}',
                                      'Alter_18_65': '{:.2f}',
                                      'Alter_66_100': '{:.2f}',
                                      'Anzeigenquote': '{:.2f}',
                                      'Anzeigenanzahl_erwartet': '{:.2f}',
                                      'Gewicht_Einwohnerzahl': '{:.3f}'
                                      }
                            
                            def Funk_Schriftfarbe_anpassen(Arg_x):
                                """Function for setting font color in streamlit.dataframe."""
                                if type(Arg_x) == str:
                                    return()
                                else:
                                    Farbe = 'black'
                                    return(f'color: {Farbe}')

                            streamlit.dataframe(Frame_Bericht_geladen.\
                                                style.background_gradient(cmap=Colormap).\
                                                applymap(Funk_Schriftfarbe_anpassen).\
                                                format(Format)
                                                )

                    time.sleep(0.1)
            
    
    def Funk_Jobs_pruefen(self):
        """Checks whether there are open jobs, i. e. whether the button
        was pressed by the user.
        """    
        if streamlit.session_state['Button_gedrueckt'] == True:
            # Tell the Eventmanager that the button was pressed by the user
            self.Eventmanager.Funk_Event_eingetreten(
                Arg_Event_Name='Button_gedrueckt',
                Arg_Argumente_von_Event={
                    'Arg_Auftrag_Suchbegriff': self.Input_Suchbegriff,
                    'Arg_Auftrag_Stichprobe': self.Input_Stichprobe,
                    'Arg_Auftrag_Max_Anzeigenalter': self.Input_Max_Anzeigenalter,
                    }
                )
            

    def Funk_Aufraeumen(
            self,
            **kwargs):
        """Cleans up and stops the script from running."""
        self.Platzhalter_Ausgabe_Spinner_02.empty()
        
        streamlit.session_state['Button_gedrueckt'] = False

        self.Platzhalter_Ausgabe_Spinner_01.empty()

        User_Interface._Funk_Scrollen(Arg_Element='div.st-emotion-cache-1bt9eao')

        streamlit.stop()
    

    @staticmethod
    def _Funk_Scrollen(
            Arg_Element,
            ):
        """Scrolls page element in argument Arg_Element into view.
        
        Keyword arguments:\n
        Arg_Element -- HTML Element to scroll to
        """
        Dummy = datetime.datetime.now().timestamp()
        Komponenten.html(
            f"""
                <p>{Dummy}</p>
                <script>
                    window.parent.document.querySelector('{Arg_Element}').scrollIntoView();
                </script>
            """,
            height=0
            )
