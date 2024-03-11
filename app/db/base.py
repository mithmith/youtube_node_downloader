from typing import Generic, Type, TypeVar
from uuid import UUID

from loguru import logger
from sqlalchemy import MetaData, create_engine, orm
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, select

from app.config import settings

engine = create_engine(settings.database_url, echo=True)
Session = orm.sessionmaker(engine, expire_on_commit=False)


class Base(SQLModel, table=False):
    metadata = MetaData(schema=settings.db_schema)

    class Config:
        arbitrary_types_allowed = True


T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, session: orm.Session) -> None:
        self._session = session

    @property
    def session(self) -> orm.Session:
        return self._session

    def get_by_params(self, params: dict) -> list[T]:
        try:
            result = self._session.query(self.model).filter_by(**params).all()
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error querying {self.model.__name__} with params {params}: {e}")
            raise

    def commit(self, commit: bool = True):
        try:
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except SQLAlchemyError as e:
            logger.error(f"Error on commit: {e}")
            self._session.rollback()
            raise

    def list(self) -> list[T]:
        try:
            return self._session.execute(select(self.model)).scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error listing {self.model.__name__}: {e}")
            raise

    def get(self, pk: UUID) -> T | None:
        try:
            entity = self._session.get(self.model, str(pk))
            if entity is None:
                logger.warning(f"{self.model.__name__} with PK {pk} not found.")
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} with PK {pk}: {e}")
            raise

    def add(self, entity: T, commit: bool = True) -> T:
        self._session.add(entity)
        self.commit(commit=commit)
        return entity

    def update(self, entity: T, params: dict) -> T:
        try:
            for attr, value in params.items():
                setattr(entity, attr, value)
            self._session.commit()
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Error updating {entity}: {e}")
            self._session.rollback()
            raise

    def delete(self, pk: UUID) -> None:
        try:
            entity = self._session.get(self.model, str(pk))
            if entity:
                self._session.delete(entity)
                self._session.commit()
            else:
                logger.warning(f"{self.model.__name__} with PK {pk} not found for deletion.")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} with PK {pk}: {e}")
            self._session.rollback()
            raise
