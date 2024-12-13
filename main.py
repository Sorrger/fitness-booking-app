from fastapi import FastAPI, HTTPException
from typing import List
from models import User, Trainer, Session, Equipment, Booking, Review
import mysql.connector


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

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the API!",
        "endpoints": ["/users", "/sessions", "/equipment"]
    }


@app.get("/users", response_model=List[User])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{id}", response_model=User)
def get_user(id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE id = %s", (id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users", response_model=User)
def create_user(user: User):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (e_mail, password, name, surname, role_id) VALUES (%s, %s, %s, %s, %s)",
            (user.email, user.password, user.name, user.surname, user.role_id)
        )
        conn.commit()
        user.id = cursor.lastrowid
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=List[Session])
def get_sessions():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sessions")
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{id}", response_model=Session)
def get_session(id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sessions WHERE id = %s", (id,))
        session = cursor.fetchone()
        cursor.close()
        conn.close()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/equipment", response_model=List[Equipment])
def get_equipment():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM equipment")
        equipment = cursor.fetchall()
        cursor.close()
        conn.close()
        return equipment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

