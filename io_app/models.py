from pydantic import BaseModel
from typing import  Optional, List

class User(BaseModel):
    id: Optional[int]
    e_mail: str
    password: str
    name: str
    surname: str
    role_id: int

class UserResponse(BaseModel):
    id: int
    name: str
    surname: str
    role_id: int
    e_mail: str
    class Config:
        orm_mode = True 

class Trainer(BaseModel):
    id: Optional[int]
    name: str
    category: str

class Session(BaseModel):
    id: Optional[int]
    trainer_id: int
    title: str
    description: str
    category: str
    date: str
    location: str
    cost: float
    capacity: int
    avaible_slots: int

class Equipment(BaseModel):
    equipment_id: Optional[int]
    session_id: int
    category_type: str

class Booking(BaseModel):
    id: Optional[int]
    user_id: int
    session_id: int
    status: str
    booking_time: str
    payment_status: str
    amount_paid: float

class Review(BaseModel):
    id: Optional[int]
    trainer_id: int
    user_id: int
    created_at: str
    rating: int
    comment: str