import mysql.connector
from datetime import datetime
import config

def get_connection():
    """Tạo kết nối tới MySQL"""
    try:
        return mysql.connector.connect(**config.DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kết nối MySQL: {err}")
        return None

# --- PHẦN 1: XỬ LÝ USER DISCORD (XP, LEVEL, GAME) ---
async def get_user_data(user_id):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        # Chỉ lấy từ bảng discord_users
        cursor.execute("SELECT * FROM discord_users WHERE discord_id = %s", (str(user_id),))
        row = cursor.fetchone()
        if row:
            return row # Trả về đúng các cột trong bảng discord_users
        
        # Nếu chưa có thì trả về data mặc định
        return {
            'discord_id': str(user_id), 'fund': 0, 'coupon': 0, 
            'xp': 0, 'level': 1, 'role_group': None, 
            'language': 'vi', 'last_daily': None, 'last_xp_message': None
        }
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

async def save_user_data(user_id, data):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT discord_id FROM discord_users WHERE discord_id = %s", (str(user_id),))
        exists = cursor.fetchone()
        
        vals = (
            data.get('fund', 0), data.get('coupon', 0), 
            data.get('xp', 0), data.get('level', 1),
            data.get('role_group'), data.get('language', 'vi'),
            data.get('last_daily'), data.get('last_xp_message'),
            str(user_id)
        )

        if exists:
            sql = """UPDATE discord_users SET fund=%s, coupon=%s, xp=%s, level=%s, 
                     role_group=%s, language=%s, last_daily=%s, last_xp_message=%s 
                     WHERE discord_id=%s"""
            cursor.execute(sql, vals)
        else:
            sql = """INSERT INTO discord_users (fund, coupon, xp, level, role_group, language, last_daily, last_xp_message, discord_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, vals)
            
        conn.commit()
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# --- PHẦN 2: XỬ LÝ USER WEB (CHO ADMIN) ---
async def get_web_user(username):
    """Tìm user web theo username"""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

async def update_web_balance(username, amount):
    """Cộng/Trừ tiền user web"""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # amount có thể là số âm (trừ tiền) hoặc dương (cộng tiền)
        cursor.execute("UPDATE users SET balance = balance + %s WHERE username = %s", (amount, username))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# --- PHẦN 3: CẤU HÌNH BOT (REACTION ROLES) ---
async def get_reaction_message_ids():
    """Lấy cấu hình Reaction Role từ MySQL"""
    conn = get_connection()
    if not conn: return {}
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM bot_config")
        rows = cursor.fetchall()
        
        # Chuyển đổi format MySQL sang Dictionary để Reaction Roles Cog dễ đọc
        config_data = {}
        for row in rows:
            config_data[row['guild_id']] = {
                'message_id': row['message_id'],
                'channel_id': row['channel_id']
            }
        return config_data
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

async def save_reaction_message_id(guild_id, message_id, channel_id):
    """Lưu cấu hình Reaction Role vào MySQL"""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        # Dùng ON DUPLICATE KEY UPDATE để tự sửa nếu đã tồn tại
        sql = """
            INSERT INTO bot_config (guild_id, message_id, channel_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE message_id = VALUES(message_id), channel_id = VALUES(channel_id)
        """
        cursor.execute(sql, (str(guild_id), str(message_id), str(channel_id)))
        conn.commit()
    except Exception as e:
        print(f"❌ Lỗi lưu config: {e}")
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# Hàm cũ không dùng nữa
def initialize_firestore(): pass
