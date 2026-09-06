#!/usr/bin/env python3
"""
Work out which country a free-text job location refers to.

Job boards write locations as "London, UK", "Sydney", "Toronto, ON, Canada" or
just "Dublin", so the country has to be inferred. The traps are real and cost
you a wrong shortlist: London is also in Ontario, Cambridge and Birmingham are
also in the US, and Perth is also in Scotland. So the order matters -
an explicit country name wins, then a US state marker, then the city.
"""
import re

US = 'United States'

# Tiering from the search brief: English-speaking tech markets first, then
# countries where English is commonly the working language in tech.
TIER_1 = ['Australia', 'Canada', 'United Kingdom', 'Ireland', 'Singapore', 'New Zealand']
TIER_2 = ['Netherlands', 'Germany', 'Sweden', 'Denmark', 'Norway', 'Finland', 'Switzerland']

# Location preference from the brief, used by the match score.
LOCATION_PREFERENCE = [
    'Australia', 'Singapore', 'Ireland', 'United Kingdom', 'Canada',
    'Netherlands', 'Germany', 'Sweden', 'Denmark', 'Norway', 'Finland',
    'Switzerland', 'New Zealand',
]

COUNTRY_ALIASES = {
    'United Kingdom': ['united kingdom', 'uk', 'u.k.', 'great britain', 'england',
                       'scotland', 'wales', 'northern ireland', 'gb', 'gbr'],
    'Ireland': ['ireland', 'republic of ireland', 'eire', 'ie', 'irl'],
    'Australia': ['australia', 'au', 'aus'],
    'New Zealand': ['new zealand', 'nz', 'nzl'],
    'Canada': ['canada', 'ca', 'can'],
    'Singapore': ['singapore', 'sg', 'sgp'],
    'Netherlands': ['netherlands', 'the netherlands', 'holland', 'nl', 'nld'],
    'Germany': ['germany', 'deutschland', 'de', 'deu', 'ger'],
    'Sweden': ['sweden', 'sverige', 'se', 'swe'],
    'Denmark': ['denmark', 'danmark', 'dk', 'dnk'],
    'Norway': ['norway', 'norge', 'no', 'nor'],
    'Finland': ['finland', 'suomi', 'fi', 'fin'],
    'Switzerland': ['switzerland', 'schweiz', 'suisse', 'ch', 'che'],
    'India': ['india', 'in', 'ind'],
    'Japan': ['japan', 'jp', 'jpn'],
    'France': ['france', 'fr', 'fra'],
    'Spain': ['spain', 'espana', 'es', 'esp'],
    'Poland': ['poland', 'polska', 'pl', 'pol'],
    'Israel': ['israel', 'il', 'isr'],
    'United Arab Emirates': ['united arab emirates', 'uae', 'ae'],
    'Hong Kong': ['hong kong', 'hk', 'hkg'],
    'South Korea': ['south korea', 'korea', 'kr', 'kor'],
    'China': ['china', 'cn', 'chn'],
    'Taiwan': ['taiwan', 'tw', 'twn'],
    'Brazil': ['brazil', 'brasil', 'br', 'bra'],
    'Mexico': ['mexico', 'mx', 'mex'],
    'Portugal': ['portugal', 'pt', 'prt'],
    'Austria': ['austria', 'at', 'aut'],
    'Belgium': ['belgium', 'be', 'bel'],
    'Czechia': ['czechia', 'czech republic', 'cz', 'cze'],
    'Italy': ['italy', 'italia', 'it', 'ita'],
    'South Africa': ['south africa', 'za', 'zaf'],
    US: ['united states', 'usa', 'u.s.', 'u.s.a.', 'us', 'america'],
}

# Two-letter aliases are ambiguous with US state codes ('IN' Indiana vs India,
# 'CA' California vs Canada, 'DE' Delaware vs Germany), so they are only
# honoured when nothing else in the string identifies a country.
_AMBIGUOUS_SHORT = {'ca', 'in', 'de', 'no', 'or', 'me', 'la', 'pa', 'oh', 'id',
                    'co', 'ne', 'mo', 'ms', 'mt', 'nd', 'sd', 'va', 'wa', 'ar',
                    'il', 'ia', 'ks', 'ky', 'ma', 'md', 'mi', 'mn', 'nc', 'nh',
                    'nj', 'nm', 'nv', 'ny', 'ok', 'ri', 'sc', 'tn', 'tx', 'ut',
                    'vt', 'wi', 'wv', 'wy', 'al', 'ak', 'az', 'ct', 'dc', 'fl',
                    'ga', 'hi', 'is', 'at', 'be', 'it', 'se', 'pl', 'cn', 'br'}

US_STATES = {
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
    'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
    'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi',
    'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
    'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
    'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
    'washington', 'west virginia', 'wisconsin', 'wyoming',
    'district of columbia', 'washington dc', 'washington d.c.',
}

US_STATE_CODES = {
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga', 'hi', 'id',
    'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms',
    'mo', 'mt', 'ne', 'nv', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok',
    'or', 'pa', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv',
    'wi', 'wy', 'dc',
}

# Major tech-hub cities. Only cities whose name is unambiguous enough to
# identify a country on its own; ambiguous ones are handled below.
CITY_COUNTRY = {
    'Australia': ['sydney', 'melbourne', 'brisbane', 'canberra', 'adelaide',
                  'gold coast', 'hobart', 'darwin', 'wollongong', 'newcastle nsw'],
    'Canada': ['toronto', 'vancouver', 'montreal', 'montréal', 'waterloo', 'ottawa',
               'calgary', 'edmonton', 'winnipeg', 'quebec city', 'québec',
               'mississauga', 'kitchener', 'halifax', 'victoria bc', 'burnaby',
               'markham', 'brampton', 'saskatoon', 'ontario', 'british columbia',
               'alberta', 'quebec', 'nova scotia', 'manitoba'],
    'United Kingdom': ['london', 'manchester', 'edinburgh', 'bristol', 'leeds',
                       'glasgow', 'liverpool', 'sheffield', 'nottingham', 'oxford',
                       'reading', 'brighton', 'belfast', 'cardiff', 'newcastle upon tyne',
                       'milton keynes', 'southampton', 'coventry'],
    'Ireland': ['dublin', 'cork', 'galway', 'limerick', 'waterford'],
    'Singapore': ['singapore'],
    'New Zealand': ['auckland', 'wellington', 'christchurch', 'hamilton nz', 'dunedin'],
    'Netherlands': ['amsterdam', 'rotterdam', 'utrecht', 'eindhoven', 'the hague',
                    'den haag', 'delft', 'groningen', 'hilversum'],
    'Germany': ['berlin', 'munich', 'münchen', 'hamburg', 'frankfurt', 'cologne',
                'köln', 'stuttgart', 'düsseldorf', 'dusseldorf', 'leipzig',
                'dresden', 'karlsruhe', 'nuremberg', 'aachen', 'heidelberg'],
    'Sweden': ['stockholm', 'gothenburg', 'göteborg', 'malmö', 'malmo', 'lund', 'uppsala'],
    'Denmark': ['copenhagen', 'københavn', 'aarhus', 'odense', 'aalborg'],
    'Norway': ['oslo', 'bergen', 'trondheim', 'stavanger'],
    'Finland': ['helsinki', 'espoo', 'tampere', 'oulu', 'turku'],
    'Switzerland': ['zurich', 'zürich', 'geneva', 'genève', 'lausanne', 'basel',
                    'bern', 'zug', 'lugano'],
    'India': ['bangalore', 'bengaluru', 'hyderabad', 'pune', 'mumbai', 'chennai',
              'gurgaon', 'gurugram', 'noida', 'new delhi', 'kolkata', 'ahmedabad'],
    'Japan': ['tokyo', 'osaka', 'kyoto', 'yokohama', 'fukuoka'],
    'France': ['paris', 'lyon', 'toulouse', 'grenoble', 'lille', 'nantes',
               'bordeaux', 'marseille', 'sophia antipolis'],
    'Spain': ['madrid', 'barcelona', 'valencia', 'seville', 'malaga', 'bilbao'],
    'Poland': ['warsaw', 'warszawa', 'krakow', 'kraków', 'wroclaw', 'wrocław',
               'gdansk', 'gdańsk', 'poznan', 'poznań'],
    'Israel': ['tel aviv', 'jerusalem', 'haifa', 'herzliya', 'ramat gan'],
    'United Arab Emirates': ['dubai', 'abu dhabi', 'sharjah'],
    'Hong Kong': ['hong kong', 'kowloon'],
    'South Korea': ['seoul', 'busan', 'incheon'],
    'China': ['beijing', 'shanghai', 'shenzhen', 'guangzhou', 'hangzhou',
              'chengdu', 'nanjing', 'wuhan', 'suzhou', 'xian', "xi'an"],
    'Taiwan': ['taipei', 'hsinchu', 'taichung'],
    'Brazil': ['sao paulo', 'são paulo', 'rio de janeiro', 'belo horizonte'],
    'Mexico': ['mexico city', 'guadalajara', 'monterrey'],
    'Portugal': ['lisbon', 'lisboa', 'porto', 'braga'],
    'Austria': ['vienna', 'wien', 'graz', 'linz'],
    'Belgium': ['brussels', 'bruxelles', 'antwerp', 'ghent', 'leuven'],
    'Czechia': ['prague', 'praha', 'brno', 'ostrava'],
    'Italy': ['milan', 'milano', 'rome', 'roma', 'turin', 'torino', 'bologna'],
    'South Africa': ['cape town', 'johannesburg', 'pretoria', 'durban'],
}

# Cities that exist in more than one target country. Resolved only when the
# string also carries a disambiguating marker, otherwise left unknown.
AMBIGUOUS_CITIES = {'london', 'cambridge', 'birmingham', 'perth', 'newcastle',
                    'hamilton', 'richmond', 'victoria', 'waterloo', 'windsor',
                    'york', 'boston', 'manchester', 'bristol', 'oxford'}

_CITY_LOOKUP = {}
for _country, _cities in CITY_COUNTRY.items():
    for _city in _cities:
        _CITY_LOOKUP.setdefault(_city, _country)

_COUNTRY_LOOKUP = {}
for _country, _names in COUNTRY_ALIASES.items():
    for _name in _names:
        _COUNTRY_LOOKUP.setdefault(_name, _country)

REMOTE_MARKERS = ['remote', 'anywhere', 'distributed', 'work from home', 'wfh']


def _tokens(text):
    """Split a location into comparable, punctuation-free segments."""
    parts = re.split(r'[,;/|()\n]|\s+-\s+|\bor\b|\band\b', text.lower())
    return [re.sub(r'[^\w\s\.\'’-]', ' ', p).strip() for p in parts if p.strip()]


def is_remote(location):
    return any(marker in (location or '').lower() for marker in REMOTE_MARKERS)


def detect_country(location, fallback_country=None):
    """Best-effort country for a location string.

    Returns a country name, or None when the string is too vague. A None is
    honest and useful: the caller can flag it for manual checking instead of
    silently filing a UK role under Canada.
    """
    if not location:
        return _normalize_code(fallback_country)

    text = str(location).strip()
    if not text:
        return _normalize_code(fallback_country)

    parts = _tokens(text)
    lowered = text.lower()

    # 'U.S.' / 'U.S.A.' will not survive a \b word-boundary match because the
    # trailing dot is not a word character, so they are matched explicitly.
    if re.search(r'\bu\.?\s?s\.?(a\.?)?(\W|$)', lowered) and 'u.k' not in lowered:
        return US

    # 1. An explicit country name anywhere in the string wins outright.
    for part in parts:
        country = _COUNTRY_LOOKUP.get(part)
        if country and part not in _AMBIGUOUS_SHORT:
            return country
    for name, country in _COUNTRY_LOOKUP.items():
        if len(name) > 3 and re.search(r'\b' + re.escape(name) + r'\b', lowered):
            return country

    # 2. A US state name or code means the United States, even when the city
    #    name also exists abroad ("Cambridge, MA", "London, KY").
    for part in parts:
        if part in US_STATES or part in US_STATE_CODES:
            return US

    # 3. An unambiguous city.
    for part in parts:
        if part in AMBIGUOUS_CITIES:
            continue
        country = _CITY_LOOKUP.get(part)
        if country:
            return country

    # 4. Ambiguous city with no other signal: default to the most common
    #    reading only when the string names nothing else at all.
    for part in parts:
        if part in AMBIGUOUS_CITIES and len(parts) == 1:
            return _CITY_LOOKUP.get(part)

    # 5. Two-letter codes, last, because they collide with US states.
    for part in parts:
        if part in _AMBIGUOUS_SHORT and part in _COUNTRY_LOOKUP:
            return _COUNTRY_LOOKUP[part]

    return _normalize_code(fallback_country)


def _normalize_code(value):
    """Map an ISO-ish country code from an ATS ('US', 'GB') to a country name."""
    if not value:
        return None
    return _COUNTRY_LOOKUP.get(str(value).strip().lower())


def is_international(location, fallback_country=None):
    """True if the location is identifiably outside the United States."""
    country = detect_country(location, fallback_country)
    return bool(country) and country != US


def country_tier(country):
    """1, 2 or 3 per the search brief; None for the US or unknown."""
    if not country or country == US:
        return None
    if country in TIER_1:
        return 1
    if country in TIER_2:
        return 2
    return 3
