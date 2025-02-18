from fastapi import APIRouter, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from io_app.database import get_db_connection, get_user_details, get_user_role, get_current_user
from io_app.models import UserResponse

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="Templates")


@router.get("/", response_class=HTMLResponse)
def list_users(request: Request):
    current_user_id = get_current_user(request)
    current_user = get_user_details(current_user_id) if current_user_id else None
    user_role = get_user_role(current_user_id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, surname, role_id, e_mail FROM user")
        users = [UserResponse(**row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        template_context = {
            "request": request,
            "users": users,
            "logged_in": current_user_id is not None,
            "user_role": user_role,
            "title": "User List"
        }

        if current_user:
            template_context["current_user"] = current_user
            template_context["user"] = current_user
        else:
            template_context["user"] = None

        return templates.TemplateResponse("users.html", template_context)

    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        return templates.TemplateResponse("error.html", {"request": request, "error_message": str(e)})


@router.get("/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: int):
    current_user_id = get_current_user(request)
    current_user = get_user_details(current_user_id) if current_user_id else None
    user_role = get_user_role(current_user_id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, name, surname, role_id, e_mail FROM user WHERE id = %s", (user_id,))
        profile_user_data = cursor.fetchone()

        if not profile_user_data:
            raise HTTPException(status_code=404, detail="User not found")

        profile_user = UserResponse(**profile_user_data)

        cursor.execute("""
            SELECT o.rating, o.comment, u.name as reviewer_name, u.surname as reviewer_surname
            FROM opinion o
            JOIN user u ON o.user_id = u.id
            WHERE o.trainer_id = %s
        """, (user_id,))
        reviews = cursor.fetchall()

        user_review = None
        if current_user_id:
            cursor.execute("SELECT rating, comment FROM opinion WHERE user_id = %s AND trainer_id = %s", (current_user_id, user_id))
            user_review = cursor.fetchone()

        cursor.close()
        conn.close()

        template_context = {
            "request": request,
            "profile_user": profile_user,
            "reviews": reviews,
            "user_review": user_review,
            "logged_in": current_user_id is not None,
            "user_role": user_role,
            "title": f"User Profile - {profile_user.name} {profile_user.surname}"
        }

        if current_user:
            template_context["current_user"] = current_user
            template_context["user"] = current_user
        else:
            template_context["user"] = None

        return templates.TemplateResponse("user_profile.html", template_context)

    except Exception as e:
        print(f"Error in user_profile: {e}") 
        return templates.TemplateResponse("error.html", {"request": request, "error_message": str(e)})



@router.post("/{id}/review")
def add_or_update_review(id: int, request: Request, rating: int = Form(...), comment: str = Form(...)):
    current_user_id = get_current_user(request)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Musisz być zalogowany, aby dodać opinię.")
    if current_user_id == id:
        raise HTTPException(status_code=400, detail="Nie możesz ocenić samego siebie.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM opinion WHERE user_id = %s AND trainer_id = %s", (current_user_id, id))
        existing_review = cursor.fetchone()

        if existing_review:
            cursor.execute("UPDATE opinion SET rating = %s, comment = %s WHERE id = %s", (rating, comment, existing_review["id"]))
        else:
            cursor.execute("INSERT INTO opinion (user_id, trainer_id, rating, comment) VALUES (%s, %s, %s, %s)", (current_user_id, id, rating, comment))

        conn.commit()
        cursor.close()
        conn.close()

        return RedirectResponse(url=f"/users/{id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}/review")
def delete_review(id: int, request: Request):
    current_user_id = get_current_user(request)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Musisz być zalogowany, aby usunąć opinię.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM opinion WHERE user_id = %s AND trainer_id = %s", (current_user_id, id))
        review = cursor.fetchone()

        if not review:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Nie znaleziono opinii do usunięcia.")

        cursor.execute("DELETE FROM opinion WHERE id = %s", (review["id"],))
        conn.commit()

        cursor.close()
        conn.close()

        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))