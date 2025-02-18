import mysql.connector
from fastapi import HTTPException, Request

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="io"
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise HTTPException(status_code=500, detail="Database connection failed.")
    
if __name__ == "__main__":
    test_db_connection()
    
def test_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",  
            user="root",        
            password="",     
            database="io" 
        )
        print("Database connection successful!")
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return False

def get_user_details(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, surname FROM user WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_role(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM user WHERE id = %s", (user_id,))
    role = cursor.fetchone()
    cursor.close()
    conn.close()
    return role[0] if role else None

def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    return int(user_id) if user_id else None