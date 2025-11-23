import discord
from discord import app_commands

# --- ID QUAN TRỌNG ---
GUILD_ID = 1378364111653703690  # ID Server của bạn
OWNER_ID = 164479846884442112   # <--- THAY ID CỦA BẠN VÀO ĐÂY

# --- CẤU HÌNH DATABASE ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'trmwool_jcatengu',      
    'password': 'Clmmnguthe1@',  
    'database': 'trmwool_game_shop',
    'raise_on_warnings': True
}

# --- CẤU HÌNH API ---
API_KEY = "233|aRsy1mo82NxcmbLQreaNOPyIKBMY1vJ2HnDCy45B"
SECRET_KEY = "KP2aAeq0ljzE9W08UMXH89NlS0fA60Uu"
API_URL_ORDER = "https://tokowendigg.com/api/prepaid/transaction/create"

# --- CẤU HÌNH ROLE & GAME (Giữ nguyên như cũ) ---
ROLE_IDS = {
    "HERO_GROUP": 1428605131372494888, 
    "MONSTER_GROUP": 1428606008678289418,
    "HERO_C": 1428609299550175293,
    "HERO_B": 1428609397906477116,
    "HERO_A": 1428609426117492756,
    "HERO_S": 1428609449173454859,
    "M_TIGER_LOW": 1428609481549414493,
    "M_TIGER_MID": 1428609524826112121,
    "M_TIGER_HIGH": 1428609554794418267,
    "M_DEMON_LOW": 1428609624952799262,
    "M_DEMON_MID": 1428609662466527272,
    "M_DEMON_HIGH": 1428609686843953236,
    "M_DRAGON_LOW": 1428609714521903186,
    "M_DRAGON_MID": 1428655205951602759,
    "M_DRAGON_HIGH": 1428655242936975392,
    "M_GOD": 1428609742116225034,
    "FUND_EMOJI": "<:fund:1378705631426646016>",
    "COUPON_EMOJI": "<:coupon:1428342053548462201>",
}

LEVEL_TIERS = {
    "HERO": {1: "HERO_C", 5: "HERO_B", 10: "HERO_A", 15: "HERO_S"},
    "MONSTER": {
        1: "M_TIGER_LOW", 3: "M_TIGER_MID", 5: "M_TIGER_HIGH",
        7: "M_DEMON_LOW", 9: "M_DEMON_MID", 11: "M_DEMON_HIGH",
        13: "M_DRAGON_LOW", 15: "M_DRAGON_MID", 17: "M_DRAGON_HIGH",
        20: "M_GOD"
    }
}
BASE_XP_TO_LEVEL = 100
XP_SCALING = 1.5
XP_COOLDOWN_SECONDS = 5
CURRENCY_CHOICES = [
    app_commands.Choice(name="Fund", value="fund"),
    app_commands.Choice(name="Coupon", value="coupon"),
]
