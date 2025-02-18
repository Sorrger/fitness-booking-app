from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from io_app.database import get_db_connection, get_user_details, get_user_role, get_current_user
from datetime import datetime
import traceback

router = APIRouter(tags=["sessions"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
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
    
@router.get("/my-sessions", response_class=HTMLResponse)
def my_sessions(request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_details(current_user_id)
    user_role = get_user_role(current_user_id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.id, s.title, s.date, s.location, s.category
            FROM session s
            JOIN booking b ON s.id = b.session_id
            WHERE b.user_id = %s
        """, (current_user_id,))
        booked_sessions = cursor.fetchall()

        created_sessions = []
        if user_role == 3:
            cursor.execute("""
                SELECT id, title, date, location, category
                FROM session
                WHERE trainer_id = %s
            """, (current_user_id,))
            created_sessions = cursor.fetchall()

        cursor.close()
        conn.close()

        return templates.TemplateResponse("my_sessions.html", {
            "request": request,
            "booked_sessions": booked_sessions,
            "created_sessions": created_sessions,
            "is_trainer": user_role == 3,
            "logged_in": True,
            "user": user,
            "user_role": user_role
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/create-session", response_class=HTMLResponse)
def create_session_page(request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_details(current_user_id) if current_user_id else None 

    return templates.TemplateResponse("create_session.html", {
        "request": request,
        "logged_in": True,
        "current_user_id": current_user_id, 
        "user": user  
    })
@router.post("/create-session")
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
        print(f"Error in create_session: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/sessions/{id}", response_class=HTMLResponse)
def view_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    user = get_user_details(current_user_id) if current_user_id else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

@router.post("/sessions/{id}/book")
def book_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Musisz być zalogowany, aby się zapisać.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

        cursor.execute("""
            SELECT * FROM booking
            WHERE user_id = %s AND session_id = %s
        """, (current_user_id, id))
        existing_booking = cursor.fetchone()
        if existing_booking:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Jesteś już zapisany na tę sesję.")

        cursor.execute("""
            INSERT INTO booking (user_id, session_id, status)
            VALUES (%s, %s, %s)
        """, (current_user_id, id, 'confirmed'))

        cursor.execute("""
            UPDATE session
            SET avaible_slots = avaible_slots - 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        cursor.close()
        conn.close()

        return RedirectResponse(url=f"/sessions/{id}", status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{id}/unregister")
def unregister_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        return JSONResponse(status_code=401, content={"error": "Musisz być zalogowany, aby się wypisać."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM booking WHERE user_id = %s AND session_id = %s", (current_user_id, id))
        booking = cursor.fetchone()

        if not booking:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=400, content={"error": "Nie jesteś zapisany na tę sesję."})

        cursor.execute("DELETE FROM booking WHERE user_id = %s AND session_id = %s", (current_user_id, id))

        cursor.execute("UPDATE session SET avaible_slots = avaible_slots + 1 WHERE id = %s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

        return JSONResponse(status_code=200, content={"success": True, "session_id": id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{id}/delete")
def delete_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        return JSONResponse(status_code=401, content={"error": "Musisz być zalogowany, aby usunąć sesję."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT trainer_id FROM session WHERE id = %s", (id,))
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=404, content={"error": "Sesja nie istnieje."})

        if session["trainer_id"] != current_user_id:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=403, content={"error": "Nie możesz usunąć tej sesji."})

        cursor.execute("DELETE FROM session WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()

        return JSONResponse(status_code=200, content={"success": True, "session_id": id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{id}/edit", response_class=HTMLResponse)
def edit_session(id: int, request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        return RedirectResponse(url="/login", status_code=303)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM session WHERE id = %s", (id,))
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Sesja nie istnieje.")

        if session["trainer_id"] != current_user_id:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=403, detail="Nie możesz edytować tej sesji.")

        cursor.close()
        conn.close()

        return templates.TemplateResponse("edit_session.html", {
            "request": request,
            "session": session
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{id}/update")
async def update_session(
    id: int,
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
    if not current_user_id:
        return JSONResponse(status_code=401, content={"error": "Musisz być zalogowany, aby edytować sesję."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT trainer_id, capacity, avaible_slots FROM session WHERE id = %s", (id,))
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=404, content={"error": "Sesja nie istnieje."})

        if session["trainer_id"] != current_user_id:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=403, content={"error": "Nie możesz edytować tej sesji."})

        cursor.execute("SELECT COUNT(*) AS enrolled FROM booking WHERE session_id = %s", (id,))
        enrolled_data = cursor.fetchone()
        enrolled_users = enrolled_data["enrolled"]

        if capacity < enrolled_users:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=400, content={"error": "Nowa pojemność nie może być mniejsza niż liczba zapisanych użytkowników."})

        cursor.execute("""
            UPDATE session
            SET title = %s, description = %s, category = %s, date = %s, location = %s, cost = %s, capacity = %s, avaible_slots = %s
            WHERE id = %s
        """, (title, description, category, date, location, cost, capacity, capacity - enrolled_users, id))

        conn.commit()
        cursor.close()
        conn.close()

        return RedirectResponse(url=f"/sessions/{id}/edit", status_code=303)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
