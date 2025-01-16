from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import User, Trainer, Session, Equipment, Booking, Review, UserResponse
from datetime import datetime
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
    
def get_user_details(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM user WHERE id = %s", (user_id,))
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

# Function to retrieve the current user ID from session cookies
def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    return int(user_id) if user_id else None


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

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Wyświetla stronę rejestracji."""
    return templates.TemplateResponse("register.html", {"request": request, "title": "Rejestracja"})


@app.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role_id: int = Form(...)
):
    """Rejestruje nowego użytkownika jako trener (role_id=3) lub zwykły użytkownik (role_id=2)."""

    # Walidacja haseł
    if password != confirm_password:
        return JSONResponse(status_code=400, content={"error": "Hasła się nie zgadzają."})

    # Walidacja roli
    if role_id not in [2, 3]:
        return JSONResponse(status_code=400, content={"error": "Nieprawidłowa rola użytkownika."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Sprawdzenie, czy użytkownik już istnieje
        cursor.execute("SELECT id FROM user WHERE e_mail = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=400, content={"error": "Użytkownik z takim e-mailem już istnieje."})

        # Wstawienie nowego użytkownika do bazy danych
        cursor.execute(
            "INSERT INTO user (name, surname, e_mail, password, role_id) VALUES (%s, %s, %s, %s, %s)",
            (name, surname, email, password, role_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return JSONResponse(status_code=200, content={"success": "Rejestracja zakończona sukcesem! Możesz się zalogować."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})




@app.get("/", response_class=HTMLResponse)
def list_sessions(request: Request, search: str = None, category: str = None):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None
    user_role = get_user_role(current_user_id)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT id, title, category, date, location, capacity, capacity - avaible_slots AS occupied_slots
            FROM session
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND title LIKE %s"
            params.append(f"%{search}%")
        
        if category:
            query += " AND category = %s"
            params.append(category)

        cursor.execute(query, params)
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return templates.TemplateResponse("sessions.html", {
            "request": request,
            "sessions": sessions,
            "logged_in": current_user_id is not None,
            "user": user,
            "user_role": user_role,
            "search": search,
            "category": category
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users", response_class=HTMLResponse)
def get_users(request: Request, query: str = None):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql_query = "SELECT id, name, surname, role_id FROM user WHERE role_id = 3"
        params = []
        
        if query:
            sql_query += " AND (surname LIKE %s)"
            params.extend([f"%{query}%"])
        
        cursor.execute(sql_query, params)
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return templates.TemplateResponse("users.html", {
            "request": request,
            "users": users,
            "title": "Users List",
            "logged_in": current_user_id is not None,
            "user": user,
            "query": query  # przekazujemy zapytanie do szablonu
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

        # Pobierz dane użytkownika
        cursor.execute("SELECT * FROM user WHERE id = %s", (id,))
        profile_user = cursor.fetchone()

        if not profile_user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Pobierz opinie na temat użytkownika
        cursor.execute("""
            SELECT r.rating, r.comment, u.name AS reviewer_name, u.surname AS reviewer_surname
            FROM opinion r
            JOIN user u ON r.user_id = u.id
            WHERE r.trainer_id = %s
        """, (id,))
        reviews = cursor.fetchall()

        # Oblicz średnią ocenę
        if reviews:
            average_rating = sum([review['rating'] for review in reviews]) / len(reviews)
        else:
            average_rating = None  # Brak ocen

        cursor.close()
        conn.close()

        # Przekaż dane do szablonu
        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "profile_user": profile_user,  
            "reviews": reviews,
            "average_rating": average_rating,  # Dodano średnią ocenę
            "logged_in": current_user_id is not None,
            "current_user": current_user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/create-session", response_class=HTMLResponse)
def create_session_page(request: Request):
    return templates.TemplateResponse("create_session.html", {"request": request})

# Obsługa formularza i zapis do bazy danych
@app.post("/create-session")
def create_session(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    cost: float = Form(...),
    capacity: int = Form(...)
):
    current_user_id = get_current_user(request)

    # Sprawdzenie poprawności danych
    if len(title) > 30 or len(category) > 30:
        raise HTTPException(status_code=400, detail="Tytuł i kategoria nie mogą przekraczać 30 znaków.")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format daty.")
    if cost < 0 or capacity < 1:
        raise HTTPException(status_code=400, detail="Koszt musi być nieujemny, a pojemność większa od 0.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO session (trainer_id, title, description, category, date, location, cost, capacity, avaible_slots) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (current_user_id, title, description, category, date, location, cost, capacity, capacity)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{id}", response_class=HTMLResponse)
def view_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Pobierz dane sesji, w tym ID trenera
        cursor.execute("SELECT * FROM session WHERE id = %s", (id,))
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")

        is_registered = False
        if current_user_id:
            cursor.execute("""
                SELECT * FROM booking
                WHERE user_id = %s AND session_id = %s
            """, (current_user_id, id))
            booking = cursor.fetchone()
            is_registered = booking is not None

        cursor.close()
        conn.close()

        # Przekaż dane do szablonu
        return templates.TemplateResponse("session_detail.html", {
            "request": request,
            "session": session,
            "is_registered": is_registered,  
            "logged_in": current_user_id is not None,
            "user": user,
            "trainer_id": session["trainer_id"]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/sessions/{id}/book")
def book_session(id: int, request: Request):
    # Sprawdź, czy użytkownik jest zalogowany
    current_user_id = get_current_user(request)
    if not current_user_id:
        # Jeśli nie jest zalogowany, zwróć błąd lub przekieruj na login
        raise HTTPException(
            status_code=401,
            detail="Musisz być zalogowany, aby się zapisać."
        )

    try:
        # Połącz się z bazą
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Sprawdź, czy sesja istnieje i ma wolne miejsca
        cursor.execute("SELECT * FROM session WHERE id = %s", (id,))
        session_data = cursor.fetchone()

        if not session_data:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Taka sesja nie istnieje.")

        if session_data["avaible_slots"] <= 0:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Brak wolnych miejsc w tej sesji.")

        # (Opcjonalnie) sprawdź, czy użytkownik już zapisał się na tę sesję
        # Można to rozwiązać np. przez unikalny klucz (user_id, session_id) w tabeli rezerwacji
        cursor.execute("""
            SELECT * FROM booking
            WHERE user_id = %s AND session_id = %s
        """, (current_user_id, id))
        existing_booking = cursor.fetchone()
        if existing_booking:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Jesteś już zapisany na tę sesję.")

        # Dodaj nowy rekord w tabeli booking (rezerwacje)
        cursor.execute("""
            INSERT INTO booking (user_id, session_id, status)
            VALUES (%s, %s, %s)
        """, (current_user_id, id, 'confirmed'))

        # Zmniejsz liczbę wolnych miejsc w sesji
        cursor.execute("""
            UPDATE session
            SET avaible_slots = avaible_slots - 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        cursor.close()
        conn.close()

        # Przekieruj z powrotem do strony sesji (lub np. do listy sesji)
        return RedirectResponse(url=f"/sessions/{id}", status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sessions/{id}/unregister")
def unregister_session(id: int, request: Request):
    # Check if the user is logged in
    current_user_id = get_current_user(request)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Musisz być zalogowany, aby się wypisać."
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if the user is registered for the session
        cursor.execute("""
            SELECT * FROM booking
            WHERE user_id = %s AND session_id = %s
        """, (current_user_id, id))
        booking = cursor.fetchone()

        if not booking:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Nie jesteś zapisany na tę sesję.")

        # Remove the booking
        cursor.execute("""
            DELETE FROM booking
            WHERE user_id = %s AND session_id = %s
        """, (current_user_id, id))

        # Increase the available slots for the session
        cursor.execute("""
            UPDATE session
            SET avaible_slots = avaible_slots + 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        cursor.close()
        conn.close()

        # Redirect to the session details page
        return RedirectResponse(url=f"/sessions/{id}", status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
