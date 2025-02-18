from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from io_app.database import get_db_connection

router = APIRouter(prefix="", tags=["authentication"])
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user_id = request.cookies.get("user_id")

    if user_id:
        return RedirectResponse(url="/sessions", status_code=303) 

    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@router.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM user WHERE e_mail = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        response = RedirectResponse(url="/", status_code=303) 
        response.set_cookie(
            key="user_id",
            value=str(user["id"]),
            httponly=True,
            samesite="Lax",
            secure=False 
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("user_id")
    return response

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Wyświetla stronę rejestracji."""
    return templates.TemplateResponse("register.html", {"request": request, "title": "Rejestracja"})

@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role_id: int = Form(...)
):
    """Rejestruje nowego użytkownika jako trenera (role_id=3) lub zwykłego użytkownika (role_id=2)."""

    if password != confirm_password:
        return JSONResponse(status_code=400, content={"error": "Hasła się nie zgadzają."})

    if role_id not in [2, 3]:
        return JSONResponse(status_code=400, content={"error": "Nieprawidłowa rola użytkownika."})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM user WHERE e_mail = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            conn.close()
            return JSONResponse(status_code=400, content={"error": "Użytkownik z takim e-mailem już istnieje."})

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