import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.categories import CategoryCreate, CategoryUpdate

# Default system categories: (name, color, icon, subcategories)
_DEFAULT_CATEGORIES: list[tuple[str, str, str, list[tuple[str, str, str]]]] = [
    ("Alimentación", "#4CAF50", "🛒", [
        ("Supermercado", "#66BB6A", "🏪"),
        ("Restaurantes", "#81C784", "🍽️"),
        ("Cafeterías", "#A5D6A7", "☕"),
    ]),
    ("Transporte", "#2196F3", "🚗", [
        ("Gasolina", "#42A5F5", "⛽"),
        ("Transporte público", "#64B5F6", "🚌"),
        ("Taxi/Uber", "#90CAF9", "🚕"),
    ]),
    ("Hogar", "#FF9800", "🏠", [
        ("Alquiler/Hipoteca", "#FFA726", "🏡"),
        ("Suministros", "#FFB74D", "💡"),
        ("Mantenimiento", "#FFCC02", "🔧"),
    ]),
    ("Salud", "#F44336", "❤️", [
        ("Farmacia", "#EF5350", "💊"),
        ("Médico", "#E57373", "🏥"),
        ("Seguro médico", "#EF9A9A", "🩺"),
    ]),
    ("Ocio", "#9C27B0", "🎉", [
        ("Entretenimiento", "#AB47BC", "🎬"),
        ("Viajes", "#BA68C8", "✈️"),
        ("Deporte", "#CE93D8", "⚽"),
    ]),
    ("Educación", "#00BCD4", "📚", [
        ("Libros", "#26C6DA", "📖"),
        ("Cursos", "#4DD0E1", "🎓"),
    ]),
    ("Ropa y calzado", "#FF5722", "👕", []),
    ("Tecnología", "#607D8B", "💻", []),
    ("Seguros", "#795548", "🛡️", []),
    ("Ingresos", "#8BC34A", "💰", [
        ("Nómina", "#9CCC65", "💼"),
        ("Freelance", "#AED581", "🖥️"),
        ("Intereses/Dividendos", "#C5E1A5", "📈"),
    ]),
    ("Otros", "#9E9E9E", "📦", []),
]


async def seed_default_categories(db: AsyncSession) -> None:
    """Insert system categories if none exist. Idempotent."""
    result = await db.execute(
        select(func.count()).select_from(Category).where(Category.is_system.is_(True))
    )
    if result.scalar_one() > 0:
        return

    for name, color, icon, subcategories in _DEFAULT_CATEGORIES:
        parent = Category(name=name, color=color, icon=icon, is_system=True, user_id=None)
        db.add(parent)
        await db.flush()

        for sub_name, sub_color, sub_icon in subcategories:
            child = Category(
                name=sub_name,
                color=sub_color,
                icon=sub_icon,
                is_system=True,
                user_id=None,
                parent_id=parent.id,
            )
            db.add(child)

    await db.flush()


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, data: CategoryCreate
) -> Category:
    if data.parent_id is not None:
        # Verify parent exists and is accessible
        await get_category(db, user_id, data.parent_id)

    category = Category(
        user_id=user_id,
        name=data.name,
        parent_id=data.parent_id,
        color=data.color,
        icon=data.icon,
        is_system=False,
    )
    db.add(category)
    await db.flush()
    return category


async def get_categories(db: AsyncSession, user_id: uuid.UUID) -> list[Category]:
    result = await db.execute(
        select(Category).where(
            or_(Category.user_id == user_id, Category.is_system.is_(True))
        )
    )
    return list(result.scalars().all())


async def get_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> Category:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == user_id, Category.is_system.is_(True)),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


async def update_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID, data: CategoryUpdate
) -> Category:
    category = await get_category(db, user_id, category_id)
    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System categories cannot be modified",
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    return category


async def delete_category(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    category = await get_category(db, user_id, category_id)
    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System categories cannot be deleted",
        )
    await db.delete(category)
    await db.flush()
