"""This module contains constants for individual adjusting of the program."""

# %%
###################################################################################################
# Local IP for use on local machine
LOKALE_IP = ''

# Path to remote database on local machine
Pfad_DB_lokal = ''

# Key for scraperapi
Schluessel = ''

# Average seconds to sleep between scraping of two pages of the Kleinanzeigen website
SCHLAFEN_SEKUNDEN = 3


##################################################
# Limiting the number of pages which can be scraped in a specific timeframe (summed over all active
# users of the web app), i. e. rate limit

# Timeframe for rate limit (in seconds)
ZEITRAUM_FUER_RATELIMIT = 180

# Maximum number of offers which can be scraped in ZEITRAUM_FUER_RATELIMIT (summed over all active
# users)
N_FUER_RATELIMIT = 200

# Upper boundary for the number of offers which can be scraped in one single order, i. e. upper
# boundary of the sample size
N_GRENZE_STICHPROBE_AUFTRAG = 100

# Upper boundary for the age of offers which should be included in the scraped sample (in days) 
GRENZE_ANZEIGENALTER_AUFTRAG = 365

# Default setting in the UI for the number of offers which are scraped in one single order
N_DEFAULT_STICHPROBE_AUFTRAG = 25

# Default setting in the UI for the age of offers which should be included in the scraped sample
# (in days)
DEFAULT_MAX_ANZEIGENALTER_AUFTRAG = 365
