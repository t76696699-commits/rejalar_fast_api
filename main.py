from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Ma'lumotlar bazasini sozlash (SQLite)
DATABASE_URL = "sqlite:///./todos.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Sirtqi vazifalar jadvali
class MainTaskDB(Base):
    __tablename__ = "main_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_completed = Column(Boolean, default=False)
    subtasks = relationship("SubTaskDB", back_populates="main_task", cascade="all, delete-orphan")


# Ichki vazifalar jadvali
class SubTaskDB(Base):
    __tablename__ = "subtasks"
    id = Column(Integer, primary_key=True, index=True)
    main_task_id = Column(Integer, ForeignKey("main_tasks.id"))
    title = Column(String, index=True)
    is_done = Column(Boolean, default=False)
    main_task = relationship("MainTaskDB", back_populates="subtasks")


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MainTaskCreate(BaseModel):
    title: str


class SubTaskCreate(BaseModel):
    main_task_id: int
    title: str


# 1. Asosiy sahifani ochish
@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    main_tasks = db.query(MainTaskDB).all()
    return templates.TemplateResponse(request, "index.html", {"request": request, "main_tasks": main_tasks})


# 2. Sirtqi vazifa qo'shish
@app.post("/api/main-task/add")
def add_main_task(task: MainTaskCreate, db: Session = Depends(get_db)):
    new_task = MainTaskDB(title=task.title, is_completed=False)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"id": new_task.id, "title": new_task.title}


# 3. Sirtqi vazifani o'chirish
@app.delete("/api/main-task/delete/{main_id}")
def delete_main_task(main_id: int, db: Session = Depends(get_db)):
    task = db.query(MainTaskDB).filter(MainTaskDB.id == main_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topilmadi")
    db.delete(task)
    db.commit()
    return {"status": "success"}


# 4. Sirtqi vazifa statusini o'zgartirish (Belgilash)
@app.post("/api/main-task/toggle/{main_id}")
def toggle_main_task(main_id: int, db: Session = Depends(get_db)):
    task = db.query(MainTaskDB).filter(MainTaskDB.id == main_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topilmadi")
    task.is_completed = not task.is_completed
    db.commit()
    return {"id": task.id, "is_completed": task.is_completed}


# 5. Sirtqiga tegishli ichki vazifalarni olish
@app.get("/api/main-task/{main_id}/subtasks")
def get_subtasks(main_id: int, db: Session = Depends(get_db)):
    task = db.query(MainTaskDB).filter(MainTaskDB.id == main_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topilmadi")
    subtasks_list = [{"id": s.id, "title": s.title, "is_done": s.is_done} for s in task.subtasks]
    return {
        "main_title": task.title,
        "is_completed": task.is_completed,
        "subtasks": subtasks_list
    }


# 6. Ichki vazifa qo'shish
@app.post("/api/subtask/add")
def add_subtask(sub: SubTaskCreate, db: Session = Depends(get_db)):
    new_sub = SubTaskDB(main_task_id=sub.main_task_id, title=sub.title, is_done=False)
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    main_task = db.query(MainTaskDB).filter(MainTaskDB.id == sub.main_task_id).first()
    return {
        "id": new_sub.id,
        "title": new_sub.title,
        "is_done": new_sub.is_done,
        "main_task_id": new_sub.main_task_id,
        "main_is_completed": main_task.is_completed
    }


# 7. Ichki vazifani belgilash
@app.post("/api/subtask/toggle/{sub_id}")
def toggle_subtask(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(SubTaskDB).filter(SubTaskDB.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Topilmadi")
    sub.is_done = not sub.is_done
    db.commit()
    return {
        "id": sub.id,
        "is_done": sub.is_done,
        "main_task_id": sub.main_task_id,
        "main_is_completed": sub.main_task.is_completed
    }


# 8. Ichki vazifani o'chirish
@app.delete("/api/subtask/delete/{sub_id}")
def delete_subtask(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(SubTaskDB).filter(SubTaskDB.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Topilmadi")
    main_id = sub.main_task_id
    main_task = sub.main_task
    db.delete(sub)
    db.commit()
    return {
        "status": "success",
        "main_task_id": main_id,
        "main_is_completed": main_task.is_completed
    }