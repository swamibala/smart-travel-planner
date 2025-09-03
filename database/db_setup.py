import sqlite3

DATABASE_PATH = "itinerary.db"

def create_table():
    """
    Creates the 'itinerary' table if it doesn't exist.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itinerary (
            id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_itinerary(thread_id, itinerary_data):
    """
    Saves or updates itinerary data for a given thread_id.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO itinerary (id, data) VALUES (?, ?)
    ''', (thread_id, itinerary_data))
    conn.commit()
    conn.close()

def get_itinerary(thread_id):
    """
    Retrieves itinerary data for a given thread_id.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT data FROM itinerary WHERE id = ?', (thread_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
