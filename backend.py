from abc import ABC, abstractmethod
from datetime import datetime
import csv
import os
import json


class InvalidTransactionError(Exception):
    pass

class FileLoadError(Exception):
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

    @abstractmethod
    def get_net_impact(self) -> str:
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    def display_time(self) -> str:
        return datetime.strptime(self._time, "%H:%M:%S").strftime("%I:%M %p")

    def display_amount(self) -> str:
        sign = "+" if self.get_net_impact() > 0 else "-"
        return f"{sign} Rs. {self.amount:,.2f}"

    def to_ui_row(self) -> tuple:
        return (self.city, self.date, self.display_time(), self.get_type(), self.display_amount())

    def to_export_row(self) -> list:
        return [self.city, self.date, self.time, self.get_type(), f"{self.amount:.2f}", self.status]

    def __repr__self(self):
        return (f"{type(self).__name__}({self.city}, {self.date}, "f"{self.time}, {self.amount:.2f}, {self.status})")


class CreditTransaction(Transaction):
    def __init__(self, city, date, time, amount, status="Completed"):
        super().__init__(city, date, time, amount, status)

    def get_net_impact(self) -> float:
        return +self.amount

    def get_type(self) -> str:
        return "Credit"



class DebitTransaction(Transaction):
    def __init__(self, city, date, time, amount, status="Completed"):
        super().__init__(city, date, time, amount, status)

    def get_net_impact(self) -> float:
        return -self.amount

    def get_type(self) -> str:
        return "Debit"


def build_transaction(record:dict) -> Transaction:
    ttype = str(record.get("type", "")).strip().lower()
    args = (record.get("city"), record.get("date"), record.get("time"), record.get("amount"), record.get("status"))

    if ttype == "credit":
        return CreditTransaction(*args)
    if ttype == "debit":
        return DebitTransaction(*args)
    raise InvalidTransactionError(f"Unknown Transaction Type '{ttype}'.")


class FileLoader(ABC):
    @abstractmethod
    def parse_file(self, filepath: str) -> list:
        pass

    def _try_add(self, record, results: list, label: str):
        try:
            if not isinstance(record, dict):
                raise InvalidTransactionError("Record is not a key/value object.")
            clean = {str(k).strip().lower(): v for k, v in record.items()
                     if k is not None}
            results.append(build_transaction(clean))
        except InvalidTransactionError as e:
            self.skipped.append(f"{label}: {e}")
        except Exception as e:
            self.skipped.append(f"{label}: unexpected error ({e})")


class CSVLoader(FileLoader):
    def parse_file(self, filepath: str) -> list:
        self.skipped = []
        results = []
        try:
            with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                line_no = 1
                for row in reader:
                    Line_no += 1
                    try:
                        self._try_add(row, results, f"Line {line_no}")
                    except Exception as e:
                        self.skipped.append(f"Line {line_no}: {e}")
        except (OSError, csv.Error, UnicodeDecodeError) as e:
            raise FileLoadError(f"Could not read '{os.path.basename(filepath)}': {e}")
        return results
        

class JSONLoader(FileLoader):
    def parse_file(self, filepath: str) -> list:
        self.skipped = []
        results = []
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise FileLoadError(f"Could not read '{os.path.basename(filepath)}': {e}")
 
        if isinstance(data, dict):
            data = data.get("transactions", [])
        if not isinstance(data, list):
            raise FileLoadError("JSON file must contain a list of transactions.")
 
        index = 0
        for item in data:
            index += 1
            self._try_add(item, results, f"Record {index}")
        return results
 
 
def get_loader(filepath: str) -> FileLoader:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".csv", ".txt"):
        return CSVLoader()
    if ext == ".json":
        return JSONLoader()
    raise FileLoadError(f"Unsupported file type '{ext}'. Use .csv or .json only.")


class IngestionQueue:
 
    def __init__(self):
        self._items = []
 
    def enqueue(self, item):
        self._items.append(item)
 
    def dequeue(self):
        if self.is_empty():
            raise IndexError("dequeue from empty IngestionQueue")
        return self._items.pop(0)
 
    def is_empty(self) -> bool:
        return len(self._items) == 0
 
    def __len__(self):
        return len(self._items)
 
 
class FilterHistoryStack:
 
    def __init__(self):
        self._items = []
 
    def push(self, state: dict):
        self._items.append(dict(state))
 
    def pop(self) -> dict:
        if self.is_empty():
            raise IndexError("pop from empty FilterHistoryStack")
        return self._items.pop()
 
    def peek(self):
        return dict(self._items[-1]) if self._items else None
 
    def is_empty(self) -> bool:
        return len(self._items) == 0
 
    def clear(self):
        self._items = []
 
    def __len__(self):
        return len(self._items)
 
 
class AuditNode:
 
    def __init__(self, data: tuple):
        if not isinstance(data, tuple) or len(data) != 4:
            raise ValueError("AuditNode requires a 4-element tuple.")
        self.data = data
        self.next = None
 
 
class ExportAuditLinkedList:
 
    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0
 
    def append(self, data: tuple):
        node = AuditNode(data)
        if self.head is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self._size += 1
 
    def traverse(self) -> list:
        entries = []
        current = self.head
        while current is not None:
            entries.append(current.data)
            current = current.next
        return entries
 
    def write_to_file(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("FINPAY AUDIT LOG\n")
            f.write("=" * 72 + "\n")
            f.write(f"{'Timestamp':<21}{'Action':<16}{'Records':>9}{'Net Amount (Rs.)':>20}\n")
            f.write("-" * 72 + "\n")
            current = self.head
            while current is not None:
                timestamp, action, count, net = current.data
                f.write(f"{timestamp:<21}{action:<16}{count:>9}{net:>20,.2f}\n")
                current = current.next
 
    def __len__(self):
        return self._size



