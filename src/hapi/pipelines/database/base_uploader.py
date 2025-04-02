from abc import ABC, abstractmethod

from hdx.database import Database


class BaseUploader(ABC):
    def __init__(self, database: Database):
        self._database = database
        self._session = database.get_session()

    @abstractmethod
    def populate(self) -> None:
        """
        Populate database. Must be overridden.

        Returns:
            None
        """
        pass
