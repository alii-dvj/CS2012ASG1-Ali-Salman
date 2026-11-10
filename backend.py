from abc import ABC, abstractmethod
from datetime import datetime

class InvalidTransactionError(Exception):
    pass

class Transaction(ABC):

    DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d")
    TIME_FORMATS = ("%H:%M:%S", "%H:%M")

    def __init__(self, city, date, time, amount, status = "completed"):
        self._city = None
        self._date = None
        self._time = None
        self._amount = None
        self._status = None
        self.city = city
        self.date = date
        self.time = time
        self.amount = amount
        self.status = status

    @property
    def city(self):
        return self._city

    @city.setter
    def city(self, value):
        value = value.strip()
        if not value:
            raise InvalidTransactionError("City cannot be empty.")
        self._city = value.title()

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        value = str(value if value is not None else "").strip()
        for fmt in self.DATE_FORMATS:
            try:
                self._date = datetime.strptime(value, fmt).strftime("%Y-%m-%d")
                return
            except ValueError:
                continue
        raise InvalidTransactionError(f"Invalid date '{value}'.")

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self,value):
        value = str(value if value is not None else "").strip()
        for fmt in self.TIME_FORMATS:
            try:
                self._time = datetime.strptime(value, fmt).strftime("%H:%M:%S")
                return
            except ValueError:
                continue
        raise InvalidTransactionError(f"Invalid time '{value}'.")

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self,value):
        if isinstance(value, bool):
            raise InvalidTransactionError(f"Invalid amount '{value}'.")
        try:
            number = float(str(value).replace(",", "").strip())
        except:
            raise InvalidTransactionError(f"Invalid amount '{value}'.")
        if number != number or number in (float("inf"), float("-inf")):
            raise InvalidTransactionError("Invalid amount '{value}'.")
        if number <= 0:
            raise InvalidTransactionError(f"Aount must be greater than 0 (got {number:g}).")
        self._amount = number

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        value = str(value if value is not None else "").strip()
        self._status = value.title() if value else "Completed"

