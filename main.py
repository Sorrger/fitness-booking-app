from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import User, Trainer, Session, Equipment, Booking, Review, UserResponse
import mysql.connector

# Initialize FastAPI app
app = FastAPI()

templates = Jinja2Templates(directory="Templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database connection function
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

# Function to retrieve the current user ID from session cookies
def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    return int(user_id) if user_id else None

# Function to fetch user details
def get_user_details(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM user WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception:
        return None

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch user by email and password
        cursor.execute("SELECT * FROM user WHERE e_mail = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Set session cookie
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="user_id", value=str(user["id"]), httponly=True)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("user_id")
    return response

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    return templates.TemplateResponse("main.html", {
        "request": request,
        "title": "Główna Strona",
        "logged_in": current_user_id is not None,
        "user": user
    })

@app.get("/users", response_class=HTMLResponse)
def get_users(request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, surname, role_id FROM user")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return templates.TemplateResponse("users.html", {
            "request": request,
            "users": users,
            "title": "Users List",
            "logged_in": current_user_id is not None,
            "user": user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{id}", response_class=HTMLResponse)
def get_user_profile(id: int, request: Request):
    current_user_id = get_current_user(request)
    current_user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE id = %s", (id,))
        profile_user = cursor.fetchone()

        # Fetch reviews
        cursor.execute("""
            SELECT r.rating, r.comment, u.name AS reviewer_name, u.surname AS reviewer_surname
            FROM opinion r
            JOIN user u ON r.user_id = u.id
            WHERE r.trainer_id = %s
        """, (id,))
        reviews = cursor.fetchall()

        cursor.close()
        conn.close()

        if not profile_user:
            raise HTTPException(status_code=404, detail="User not found")

        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "profile_user": profile_user,  
            "reviews": reviews,
            "logged_in": current_user_id is not None,
            "current_user": current_user 
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions", response_class=HTMLResponse)
def list_sessions(request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, title, category, date, location, capacity, capacity - avaible_slots AS occupied_slots
            FROM session
        """)
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return templates.TemplateResponse("sessions.html", {
            "request": request,
            "sessions": sessions,
            "logged_in": current_user_id is not None,
            "user": user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{id}", response_class=HTMLResponse)
def view_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM session WHERE id = %s", (id,))
        session = cursor.fetchone()
        cursor.close()
        conn.close()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return templates.TemplateResponse("session_detail.html", {
            "request": request,
            "session": session,
            "logged_in": current_user_id is not None,
            "user": user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
