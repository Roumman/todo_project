from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, Integer, String, Boolean, desc, asc, create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

# Настройка SQLAlchemy
Base = declarative_base()

class Item(Base):
    """
    Модель базы данных для хранения задач.
    """
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)  # Уникальное название задачи
    description = Column(String, nullable=True)  # Описание задачи (необязательно)
    completed = Column(Boolean, default=False)  # Статус выполнения задачи
    priority = Column(Integer, default=1)  # Приоритет задачи (1, 2 или 3)

# Настройка базы данных
engine = create_engine("sqlite:///./todo_project.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Модели Pydantic
class ItemCreate(BaseModel):
    """
    Модель для валидации данных при создании новой задачи.
    """
    title: str  # Название задачи
    description: Optional[str] = None  # Описание задачи
    completed: bool = False  # Статус выполнения (по умолчанию False)
    priority: int = Field(1)  # Приоритет (по умолчанию 1)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value):
        """
        Проверка приоритета. Допустимые значения: 1, 2, 3.
        """
        if value not in (1, 2, 3):
            raise ValueError("Priority must be 1 (Low), 2 (Medium), or 3 (High)")
        return value

class ItemOut(BaseModel):
    """
    Модель для отображения задачи в ответах API.
    """
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    priority: int

    class Config:
        from_attributes = True  # Указание на использование SQLAlchemy объектов

# Зависимость для получения сессии базы данных
def get_db():
    """
    Создание и закрытие сессии базы данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Эндпоинты
@app.post("/items/", response_model=ItemOut)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Создание новой задачи.

    :param item: Данные задачи из тела запроса
    :param db: Сессия базы данных
    :return: Созданная задача
    """
    # Проверка на уникальность названия
    if db.query(Item).filter(Item.title == item.title).first():
        raise HTTPException(status_code=400, detail="Item with this title already exists")
    db_item = Item(
        title=item.title,
        description=item.description,
        completed=item.completed,
        priority=item.priority,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[ItemOut])
def get_items(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    sort_by: str = Query("id", pattern="^(id|title|completed|priority)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
):
    """
    Получение списка задач с возможностью сортировки и пагинации.

    :param db: Сессия базы данных
    :param skip: Количество пропускаемых записей
    :param limit: Максимальное количество возвращаемых записей
    :param sort_by: Поле для сортировки
    :param sort_order: Порядок сортировки (asc или desc)
    :return: Список задач
    """
    query = db.query(Item)

    # Применяем сортировку
    if sort_order == "asc":
        query = query.order_by(asc(getattr(Item, sort_by)))
    else:
        query = query.order_by(desc(getattr(Item, sort_by)))

    # Применяем пагинацию
    items = query.offset(skip).limit(limit).all()
    return items

@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """
    Получение задачи по ID.

    :param item_id: Идентификатор задачи
    :param db: Сессия базы данных
    :return: Задача
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    """
    Обновление существующей задачи.

    :param item_id: Идентификатор задачи
    :param item: Обновленные данные задачи
    :param db: Сессия базы данных
    :return: Обновленная задача
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.title = item.title
    db_item.description = item.description
    db_item.completed = item.completed
    db_item.priority = item.priority
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Удаление задачи по ID.

    :param item_id: Идентификатор задачи
    :param db: Сессия базы данных
    :return: Сообщение об успешном удалении
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted"}

@app.get("/")
async def root():
    """
    Приветственная страница API.
    """
    return {"message": "Welcome to the To-Do List API"}
