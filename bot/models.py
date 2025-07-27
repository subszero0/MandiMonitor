"""SQLModel ORM classes for MandiMonitor Bot."""

from sqlmodel import SQLModel


class User(SQLModel, table=True):
    """User model for bot users."""

    pass


class Watch(SQLModel, table=True):
    """Watch model for price monitoring requests."""

    pass


class Price(SQLModel, table=True):
    """Price model for storing price history."""

    pass


class Click(SQLModel, table=True):
    """Click model for tracking affiliate link clicks."""

    pass
