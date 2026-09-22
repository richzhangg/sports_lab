"""
NCAA Division I tennis institution registry.

`host` is the athletics-department domain. The scraper tries both mens-tennis
and womens-tennis roster paths (with slug fallbacks) and skips any that 404 —
not every school sponsors men's tennis. Per-school/season coverage is written to
data/real/roster_scrape_coverage.csv on every run.

Compiled from public conference membership (2024-25 realignment). Domains that
have changed will simply show as gaps in the coverage report; add/fix and re-run
`python -m realdata.scrape.run_pilot` (nothing else changes).
"""

_CONF: dict[str, list[tuple[str, str]]] = {
    "ACC": [
        ("Boston College", "bceagles.com"), ("California", "calbears.com"),
        ("Clemson", "clemsontigers.com"), ("Duke", "goduke.com"),
        ("Florida State", "seminoles.com"), ("Georgia Tech", "ramblinwreck.com"),
        ("Louisville", "gocards.com"), ("Miami", "miamihurricanes.com"),
        ("NC State", "gopack.com"), ("North Carolina", "goheels.com"),
        ("Notre Dame", "fightingirish.com"), ("Pittsburgh", "pittsburghpanthers.com"),
        ("SMU", "smumustangs.com"), ("Stanford", "gostanford.com"),
        ("Syracuse", "cuse.com"), ("Virginia", "virginiasports.com"),
        ("Virginia Tech", "hokiesports.com"), ("Wake Forest", "godeacs.com"),
    ],
    "Big Ten": [
        ("Illinois", "fightingillini.com"), ("Indiana", "iuhoosiers.com"),
        ("Iowa", "hawkeyesports.com"), ("Maryland", "umterps.com"),
        ("Michigan", "mgoblue.com"), ("Michigan State", "msuspartans.com"),
        ("Minnesota", "gophersports.com"), ("Nebraska", "huskers.com"),
        ("Northwestern", "nusports.com"), ("Ohio State", "ohiostatebuckeyes.com"),
        ("Penn State", "gopsusports.com"), ("Purdue", "purduesports.com"),
        ("Rutgers", "scarletknights.com"), ("UCLA", "uclabruins.com"),
        ("USC", "usctrojans.com"), ("Washington", "gohuskies.com"),
        ("Wisconsin", "uwbadgers.com"), ("Oregon", "goducks.com"),
    ],
    "SEC": [
        ("Alabama", "rolltide.com"), ("Arkansas", "arkansasrazorbacks.com"),
        ("Auburn", "auburntigers.com"), ("Florida", "floridagators.com"),
        ("Georgia", "georgiadogs.com"), ("Kentucky", "ukathletics.com"),
        ("LSU", "lsusports.net"), ("Mississippi State", "hailstate.com"),
        ("Missouri", "mutigers.com"), ("Ole Miss", "olemisssports.com"),
        ("Oklahoma", "soonersports.com"), ("South Carolina", "gamecocksonline.com"),
        ("Tennessee", "utsports.com"), ("Texas", "texassports.com"),
        ("Texas A&M", "12thman.com"), ("Vanderbilt", "vucommodores.com"),
    ],
    "Big 12": [
        ("Arizona", "arizonawildcats.com"), ("Arizona State", "thesundevils.com"),
        ("Baylor", "baylorbears.com"), ("BYU", "byucougars.com"),
        ("Cincinnati", "gobearcats.com"), ("Colorado", "cubuffs.com"),
        ("Houston", "uhcougars.com"), ("Iowa State", "cyclones.com"),
        ("Kansas", "kuathletics.com"), ("Kansas State", "kstatesports.com"),
        ("Oklahoma State", "okstate.com"), ("TCU", "gofrogs.com"),
        ("Texas Tech", "texastech.com"), ("UCF", "ucfknights.com"),
        ("Utah", "utahutes.com"), ("West Virginia", "wvusports.com"),
    ],
    "Pac-12": [
        ("Oregon State", "osubeavers.com"), ("Washington State", "wsucougars.com"),
    ],
    "Ivy League": [
        ("Brown", "brownbears.com"), ("Columbia", "gocolumbialions.com"),
        ("Cornell", "cornellbigred.com"), ("Dartmouth", "dartmouthsports.com"),
        ("Harvard", "gocrimson.com"), ("Penn", "pennathletics.com"),
        ("Princeton", "goprincetontigers.com"), ("Yale", "yalebulldogs.com"),
    ],
    "Big East": [
        ("Butler", "butlersports.com"), ("Creighton", "gocreighton.com"),
        ("DePaul", "depaulbluedemons.com"), ("Georgetown", "guhoyas.com"),
        ("Marquette", "gomarquette.com"), ("Providence", "friars.com"),
        ("Seton Hall", "shupirates.com"), ("St. John's", "redstormsports.com"),
        ("UConn", "uconnhuskies.com"), ("Villanova", "villanova.com"),
        ("Xavier", "goxavier.com"),
    ],
    "American": [
        ("Charlotte", "charlotte49ers.com"), ("East Carolina", "ecupirates.com"),
        ("Florida Atlantic", "fausports.com"), ("Memphis", "gotigersgo.com"),
        ("North Texas", "meangreensports.com"), ("Rice", "riceowls.com"),
        ("South Florida", "gousfbulls.com"), ("Temple", "owlsports.com"),
        ("Tulane", "tulanegreenwave.com"), ("Tulsa", "tulsahurricane.com"),
        ("UAB", "uabsports.com"), ("UTSA", "goutsa.com"), ("Wichita State", "goshockers.com"),
    ],
    "Atlantic 10": [
        ("Davidson", "davidsonwildcats.com"), ("Dayton", "daytonflyers.com"),
        ("Duquesne", "goduquesne.com"), ("Fordham", "fordhamsports.com"),
        ("George Mason", "gomason.com"), ("George Washington", "gwsports.com"),
        ("La Salle", "goexplorers.com"), ("Loyola Chicago", "loyolaramblers.com"),
        ("UMass", "umassathletics.com"), ("Rhode Island", "gorhody.com"),
        ("Richmond", "richmondspiders.com"), ("Saint Joseph's", "sjuhawks.com"),
        ("Saint Louis", "slubillikens.com"), ("St. Bonaventure", "gobonnies.com"),
        ("VCU", "vcuathletics.com"),
    ],
    "Mountain West": [
        ("Air Force", "goairforcefalcons.com"), ("Boise State", "broncosports.com"),
        ("Colorado State", "csurams.com"), ("Fresno State", "gobulldogs.com"),
        ("Nevada", "nevadawolfpack.com"), ("New Mexico", "golobos.com"),
        ("San Diego State", "goaztecs.com"), ("San Jose State", "sjsuspartans.com"),
        ("UNLV", "unlvrebels.com"), ("Utah State", "utahstateaggies.com"),
        ("Wyoming", "gowyo.com"),
    ],
    "WCC": [
        ("Gonzaga", "gozags.com"), ("Loyola Marymount", "lmulions.com"),
        ("Pacific", "pacifictigers.com"), ("Pepperdine", "pepperdinewaves.com"),
        ("Portland", "portlandpilots.com"), ("Saint Mary's", "smcgaels.com"),
        ("San Diego", "usdtoreros.com"), ("San Francisco", "usfdons.com"),
        ("Santa Clara", "santaclarabroncos.com"),
    ],
    "Big West": [
        ("Cal Poly", "gopoly.com"), ("CSU Fullerton", "fullertontitans.com"),
        ("CSUN", "gomatadors.com"), ("Hawai'i", "hawaiiathletics.com"),
        ("Long Beach State", "longbeachstate.com"), ("UC Davis", "ucdavisaggies.com"),
        ("UC Irvine", "ucirvinesports.com"), ("UC Riverside", "gohighlanders.com"),
        ("UC San Diego", "ucsdtritons.com"), ("UC Santa Barbara", "ucsbgauchos.com"),
    ],
    "Conference USA": [
        ("FIU", "fiusports.com"), ("Jacksonville State", "jaxstatesports.com"),
        ("Liberty", "libertyflames.com"), ("Louisiana Tech", "latechsports.com"),
        ("Middle Tennessee", "goblueraiders.com"), ("New Mexico State", "nmstatesports.com"),
        ("Sam Houston", "gobearkats.com"), ("UTEP", "utepathletics.com"),
        ("Western Kentucky", "wkusports.com"),
    ],
    "Sun Belt": [
        ("Coastal Carolina", "goccusports.com"), ("Georgia Southern", "gseagles.com"),
        ("Georgia State", "georgiastatesports.com"), ("James Madison", "jmusports.com"),
        ("Louisiana", "ragincajuns.com"), ("Old Dominion", "odusports.com"),
        ("South Alabama", "usajaguars.com"), ("Texas State", "txstatebobcats.com"),
        ("Troy", "troytrojans.com"),
    ],
    "Missouri Valley": [
        ("Bradley", "bradleybraves.com"), ("Drake", "godrakebulldogs.com"),
        ("Evansville", "gopurpleaces.com"), ("Illinois State", "goredbirds.com"),
        ("Southern Illinois", "siusalukis.com"), ("UNI", "unipanthers.com"),
        ("Valparaiso", "valpoathletics.com"),
    ],
    "CAA": [
        ("Campbell", "gocamels.com"), ("Charleston", "cofcsports.com"),
        ("Drexel", "drexeldragons.com"), ("Elon", "elonphoenix.com"),
        ("Hampton", "hamptonpirates.com"), ("Hofstra", "gohofstra.com"),
        ("Monmouth", "monmouthhawks.com"), ("NC A&T", "ncataggies.com"),
        ("Northeastern", "nuhuskies.com"), ("Towson", "towsontigers.com"),
        ("UNC Wilmington", "uncwsports.com"), ("William & Mary", "tribeathletics.com"),
    ],
    "Big South": [
        ("Charleston Southern", "csusports.com"), ("Gardner-Webb", "gwusports.com"),
        ("High Point", "highpointpanthers.com"), ("Longwood", "longwoodlancers.com"),
        ("Presbyterian", "gobluehose.com"), ("Radford", "radfordathletics.com"),
        ("UNC Asheville", "uncabulldogs.com"), ("Winthrop", "winthropeagles.com"),
    ],
    "Southern": [
        ("Chattanooga", "gomocs.com"), ("The Citadel", "citadelsports.com"),
        ("East Tennessee State", "etsubucs.com"), ("Furman", "furmanpaladins.com"),
        ("Mercer", "mercerbears.com"), ("Samford", "samfordsports.com"),
        ("UNC Greensboro", "uncgspartans.com"), ("VMI", "vmikeydets.com"),
        ("Western Carolina", "catamountsports.com"), ("Wofford", "woffordterriers.com"),
    ],
    "ASUN": [
        ("Austin Peay", "letsgopeay.com"), ("Bellarmine", "athletics.bellarmine.edu"),
        ("Central Arkansas", "ucasports.com"), ("Eastern Kentucky", "ekusports.com"),
        ("Florida Gulf Coast", "fgcuathletics.com"), ("Jacksonville", "judolphins.com"),
        ("Lipscomb", "lipscombsports.com"), ("North Alabama", "roarlions.com"),
        ("Queens", "queensathletics.com"), ("Stetson", "gohatters.com"),
    ],
    "Horizon": [
        ("Cleveland State", "csuvikings.com"), ("Detroit Mercy", "detroittitans.com"),
        ("Milwaukee", "mkepanthers.com"), ("Northern Kentucky", "nkunorse.com"),
        ("Oakland", "goldengrizzlies.com"), ("Purdue Fort Wayne", "gomastodons.com"),
        ("Robert Morris", "rmucolonials.com"), ("Wright State", "wsuraiders.com"),
        ("Youngstown State", "ysusports.com"),
    ],
    "MAC": [
        ("Akron", "gozips.com"), ("Ball State", "ballstatesports.com"),
        ("Bowling Green", "bgsufalcons.com"), ("Buffalo", "ubbulls.com"),
        ("Eastern Michigan", "emueagles.com"), ("Kent State", "kentstatesports.com"),
        ("Miami (OH)", "miamiredhawks.com"), ("Northern Illinois", "niuhuskies.com"),
        ("Ohio", "ohiobobcats.com"), ("Toledo", "utrockets.com"),
        ("Western Michigan", "wmubroncos.com"),
    ],
    "Summit / MAAC / NEC / OVC": [
        ("Denver", "denverpioneers.com"), ("South Dakota", "goyotes.com"),
        ("South Dakota State", "gojacks.com"), ("North Dakota", "fightinghawks.com"),
        ("Omaha", "omavs.com"), ("Fairfield", "fairfieldstags.com"),
        ("Marist", "gomarist.com"), ("Quinnipiac", "quinnipiacbobcats.com"),
        ("Rider", "gobroncs.com"), ("Siena", "sienasaints.com"),
        ("Iona", "icgaels.com"), ("Manhattan", "gojaspers.com"),
        ("Niagara", "purpleeagles.com"), ("Saint Peter's", "saintpeterspeacocks.com"),
        ("Wagner", "wagnerathletics.com"), ("Central Connecticut", "ccsubluedevils.com"),
        ("LIU", "liuathletics.com"), ("Fairleigh Dickinson", "fduknights.com"),
        ("Sacred Heart", "sacredheartpioneers.com"), ("Belmont", "belmontbruins.com"),
        ("Little Rock", "lrtrojans.com"), ("Lindenwood", "lindenwoodlions.com"),
        ("Morehead State", "msueagles.com"), ("SIU Edwardsville", "siuecougars.com"),
        ("Southeast Missouri State", "gosoutheast.com"), ("Tennessee State", "tsutigers.com"),
        ("Tennessee Tech", "ttusports.com"), ("UT Martin", "utmsports.com"),
    ],
    "Southland / WAC / Patriot / Big Sky / MEAC / SWAC": [
        ("Incarnate Word", "uiwcardinals.com"), ("Lamar", "lamarcardinals.com"),
        ("McNeese", "mcneesesports.com"), ("New Orleans", "unoprivateers.com"),
        ("Nicholls", "geauxcolonels.com"), ("Northwestern State", "nsudemons.com"),
        ("Southeastern Louisiana", "lionsports.net"), ("Texas A&M-Corpus Christi", "goislanders.com"),
        ("Abilene Christian", "acusports.com"), ("Grand Canyon", "gculopes.com"),
        ("Southern Utah", "suuthunderbirds.com"), ("Tarleton", "tarletonsports.com"),
        ("UT Arlington", "utamavs.com"), ("Utah Tech", "utahtechtrailblazers.com"),
        ("Utah Valley", "gouvu.com"), ("Army", "goarmywestpoint.com"),
        ("Boston University", "goterriers.com"), ("Bucknell", "bucknellbison.com"),
        ("Colgate", "gocolgateraiders.com"), ("Lafayette", "goleopards.com"),
        ("Lehigh", "lehighsports.com"), ("Loyola Maryland", "loyolagreyhounds.com"),
        ("Navy", "navysports.com"), ("Eastern Washington", "goeags.com"),
        ("Idaho", "govandals.com"), ("Montana", "gogriz.com"),
        ("Montana State", "msubobcats.com"), ("Portland State", "goviks.com"),
        ("Sacramento State", "hornetsports.com"), ("Weber State", "weberstatesports.com"),
        ("Florida A&M", "famuathletics.com"), ("Norfolk State", "nsuspartans.com"),
        ("North Carolina Central", "nccueaglepride.com"), ("South Carolina State", "scsuathletics.com"),
        ("Alabama A&M", "aamusports.com"), ("Alabama State", "bamastatesports.com"),
        ("Jackson State", "gojsutigers.com"), ("Prairie View A&M", "pvpanthers.com"),
        ("Southern", "gojagsports.com"), ("Texas Southern", "tsusports.com"),
    ],
    "Independents / other": [
        ("UT Rio Grande Valley", "goutrgv.com"), ("Chicago State", "gocsucougars.com"),
        ("Cal Baptist", "cbulancers.com"), ("Seattle U", "goseattleu.com"),
        ("Binghamton", "binghamtonbearcats.com"), ("UMBC", "umbcretrievers.com"),
        ("New Hampshire", "unhwildcats.com"), ("Vermont", "uvmathletics.com"),
        ("Albany", "ualbanysports.com"), ("Stony Brook", "stonybrookathletics.com"),
        ("Bryant", "bryantbulldogs.com"), ("Merrimack", "merrimackathletics.com"),
    ],
}

SCHOOLS = [
    {"school": name, "host": host, "conference": conf}
    for conf, members in _CONF.items()
    for name, host in members
]

SPORTS = ["mens-tennis", "womens-tennis"]

# roster year -> SIDEARM season label ("2024-25" season == roster year 2025)
SEASONS = {
    2016: "2015-16",
    2017: "2016-17",
    2018: "2017-18",
    2019: "2018-19",
    2020: "2019-20",
    2021: "2020-21",
    2022: "2021-22",
    2023: "2022-23",
    2024: "2023-24",
    2025: "2024-25",
    2026: None,  # current roster (no label)
}
