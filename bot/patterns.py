"""Regex patterns for watch parsing."""

import regex as re

# Amazon ASIN pattern - matches both URL format and standalone ASINs
PAT_ASIN = re.compile(
    r"(?:dp/|/gp/product/)([B0-9A-Z]{10})|(?:\b)(B[0-9A-Z]{9})\b", re.IGNORECASE
)

# Brand pattern - comprehensive brand matching with car/chemical/tool brands
PAT_BRAND = re.compile(
    r"\b(3m|samsung|lg|sony|boat|apple|mi|oneplus|realme|oppo|vivo|xiaomi|asus|dell|hp|lenovo|acer|msi|gigabyte|intel|amd|nvidia|corsair|logitech|razer|steelseries|hyperx|creative|jbl|sennheiser|audio[- ]?technica|bose|skullcandy|plantronics|jabra|anker|belkin|tp[- ]?link|d[- ]?link|netgear|asus|linksys|amazon|echo|fire|kindle|google|nest|philips|havells|bajaj|crompton|orient|usha|blue[- ]?star|voltas|lloyd|godrej|whirlpool|ifb|bosch|siemens|panasonic|carrier|daikin|mitsubishi|hitachi|toshiba|sharp|tcl|vu|micromax|intex|spice|lava|karbonn|celkon|videocon|onida|sansui|lloyd|haier|maharaja|prestige|pigeon|hawkins|presto|butterfly|glen|inalsa|morphy|richards|philips|braun|gillette|oral[- ]?b|colgate|sensodyne|pepsodent|closeup|patanjali|himalaya|lakme|loreal|olay|ponds|nivea|vaseline|johnson|baby|dabur|emami|marico|godrej|hindustan|unilever|itc|britannia|parle|cadbury|nestle|amul|mother[- ]?dairy|kwality[- ]?walls|baskin[- ]?robbins|dominos|pizza[- ]?hut|kfc|mcdonald|subway|starbucks|costa|cafe[- ]?coffee[- ]?day|barista|tata|reliance|airtel|jio|vodafone|idea|bsnl|mtnl|tikona|hathway|den|dish|tata[- ]?sky|airtel[- ]?digital|d2h|videocon[- ]?d2h|sun[- ]?direct|dd[- ]?free[- ]?dish|big[- ]?tv|zing[- ]?digital|gtpl|siti|cable|hathway|den|tikona|railtel|bsnl|mtnl|spectra|excitel|act|you[- ]?broadband|hathway|alliance|wishnet|connect|fibernet|bharti[- ]?airtel|jio[- ]?fiber|tata[- ]?sky[- ]?broadband|vodafone[- ]?red|idea[- ]?cellular|uninor|telenor|docomo|loop[- ]?mobile|videocon[- ]?telecom|spice[- ]?digital|etisalat|sistema[- ]?shyam|mts|tatadocomo|virgin[- ]?mobile|s[- ]?tel|meguiars|chemical[- ]?guys|mothers|armor[- ]?all|turtle[- ]?wax|sonax|autoglym|griot|poorboy|menzerna|swissvax|dodo[- ]?juice|poorboys|carpro|gtechniq|rupes|flex|dewalt|makita|milwaukee|festool|stanley|black[- ]?decker|craftsman|kobalt|worx|ryobi|porter[- ]?cable|ridgid|metabo|hilti|würth|wurth|stp|liqui[- ]?moly|motul|castrol|mobil|shell|total|elf|valvoline)\b",
    re.IGNORECASE,
)

# Price under pattern - matches "under 30000", "below 25k", "under INR 30k", etc.
PAT_PRICE_UNDER = re.compile(
    r"\b(?:under|below|less[- ]?than|within|max|maximum|up[- ]?to)[- ]?(?:rs\.?[- ]?|₹[- ]?|inr[- ]?)?([1-9][0-9,]*(?:k|000)?)\b",
    re.IGNORECASE,
)

# Price range pattern - matches "between 40000 and 50000", "₹40k to ₹50k", "INR 40k to INR 50k", etc.
PAT_PRICE_RANGE = re.compile(
    r"\b(?:between|from|range)[- ]?(?:rs\.?[- ]?|₹[- ]?|inr[- ]?)?([1-9][0-9,]*(?:k|000)?)[- ]?(?:and|to|[- ])[- ]?(?:rs\.?[- ]?|₹[- ]?|inr[- ]?)?([1-9][0-9,]*(?:k|000)?)\b",
    re.IGNORECASE,
)

# Discount pattern - matches "20% off", "minimum 15% discount", etc.
PAT_DISCOUNT = re.compile(
    r"\b(?:(?:min|minimum|at[- ]?least)[- ]?)?([1-9][0-9]?)[- ]?%[- ]?(?:off|discount|deal|sale)\b",
    re.IGNORECASE,
)

# Size pattern for monitors, TVs - matches "27 inch", "32\"", etc.
PAT_SIZE = re.compile(r"\b([1-9][0-9]?)[- ]?(?:inch|in|\")\b", re.IGNORECASE)

# RAM/Storage pattern - matches "8GB RAM", "256 GB SSD", etc.
PAT_MEMORY = re.compile(
    r"\b([1-9][0-9]*)[- ]?(?:gb|tb)[- ]?(?:ram|ssd|hdd|storage|memory)?\b",
    re.IGNORECASE,
)
