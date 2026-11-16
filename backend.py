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
            raise InvalidTransactionError(f"Invalid amount '{value}'.")
        if number <= 0:
            raise InvalidTransactionError(f"Amount must be greater than 0 (got {number:g}).")
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

    def __repr__(self):
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
                    line_no += 1
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


class FinPayEngine:
    EXPORT_FILE = "exported_transactions.csv"
    AUDIT_FILE = "audit_log.txt"
 
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        self.ingestion_queue = IngestionQueue()      
        self.transactions = []                       
        self.visible = []                            
        self.unique_cities = set()                   
        self.unique_dates = set()                    
        self.filter_stack = FilterHistoryStack()     
        self.audit_log = ExportAuditLinkedList()     
        self.current_filters = self._empty_filters()
        self.skipped_rows = []
        self.loaded_file = None
 
    
    @staticmethod
    def _empty_filters() -> dict:
        return {"city": "All", "date": "All", "type": "All",
                "time_from": "", "time_to": ""}
 
    @staticmethod
    def _net(transactions: list) -> float:
        total = 0.0
        for t in transactions:
            total += t.get_net_impact()
        return round(total, 2)
 
    def _log(self, action_type: str, transactions: list):
        entry = (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 action_type, len(transactions), self._net(transactions))
        self.audit_log.append(entry)
 
    @staticmethod
    def _norm_time(value) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        raise InvalidTransactionError(f"Invalid time '{value}'. Use HH:MM (24-hour).")
 
    # ---------------- loading ----------------
    def load_data(self, filepath: str) -> int:
        loader = get_loader(filepath)
        parsed = loader.parse_file(filepath)
        self.skipped_rows = list(loader.skipped)
 
        for item in parsed:
            self.ingestion_queue.enqueue(item)
        validated = []
        while not self.ingestion_queue.is_empty():
            item = self.ingestion_queue.dequeue()
            if item.amount <= 0:
                self.skipped_rows.append(f"Rejected {item!r}: amount <= 0")
                continue
            validated.append(item)
 
        self.transactions = validated
 
        self.unique_cities = set()
        self.unique_dates = set()
        for t in self.transactions:
            self.unique_cities.add(t.city)
            self.unique_dates.add(t.date)
 
        self.filter_stack.clear()
        self.current_filters = self._empty_filters()
        self.visible = list(self.transactions)
        self.loaded_file = filepath
        self._log("LOAD", self.visible)
        return len(self.transactions)
 
    def get_city_options(self) -> list:
        return ["All"] + sorted(self.unique_cities)
 
    def get_date_options(self) -> list:
        return ["All"] + sorted(self.unique_dates, reverse=True)
 
    def _matches(self, t: Transaction, f: dict) -> bool:
        if f["city"] != "All" and t.city != f["city"]:
            return False
        if f["date"] != "All" and t.date != f["date"]:
            return False
        if f["type"] != "All" and t.get_type() != f["type"]:
            return False
        if f["time_from"] and t.time < f["time_from"]:
            return False
        if f["time_to"] and t.time > f["time_to"]:
            return False
        return True
 
    def _filter_with(self, f: dict) -> list:
        result = []
        for t in self.transactions:
            if self._matches(t, f):
                result.append(t)
        return result
 
    def apply_filters(self, city="All", date="All", ttype="All",
                      time_from="", time_to="") -> list:
        new_filters = {
            "city": city or "All",
            "date": date or "All",
            "type": ttype or "All",
            "time_from": self._norm_time(time_from),
            "time_to": self._norm_time(time_to),
        }
        if (new_filters["time_from"] and new_filters["time_to"]
                and new_filters["time_from"] > new_filters["time_to"]):
            raise InvalidTransactionError("'From' time cannot be after 'To' time.")
 
        self.filter_stack.push(self.current_filters)
        self.current_filters = new_filters
        self.visible = self._filter_with(new_filters)
        self._log("FILTER", self.visible)
        return self.visible
 
    def revert_last_filter(self) -> list:
        if self.filter_stack.is_empty():
            raise IndexError("There is no earlier filter to revert to.")
        self.current_filters = self.filter_stack.pop()
        self.visible = self._filter_with(self.current_filters)
        self._log("REVERT", self.visible)
        return self.visible
 
    def clear_filters(self) -> list:
        self.filter_stack.clear()
        self.current_filters = self._empty_filters()
        self.visible = list(self.transactions)
        self._log("CLEAR", self.visible)
        return self.visible
 
    # ---------------- UI data ----------------
    def get_ui_rows(self) -> list:
        rows = []
        for t in self.visible:
            rows.append(t.to_ui_row())
        return rows
 
    def get_summary(self) -> dict:
        credits = debits = 0.0
        for t in self.visible:
            if t.get_type() == "Credit":
                credits += t.amount
            else:
                debits += t.amount
        net = self._net(self.visible)
        if abs(net - round(credits - debits, 2)) > 0.01:
            raise InvalidTransactionError("Balance mismatch detected.")
        return {"count": len(self.visible), "total_loaded": len(self.transactions),
                "credits": round(credits, 2), "debits": round(debits, 2), "net": net}
 
    # ---------------- export ----------------
    def export(self) -> tuple:
        if not self.visible:
            raise InvalidTransactionError("There are no transactions to export.")
        export_path = os.path.join(self.output_dir, self.EXPORT_FILE)
        audit_path = os.path.join(self.output_dir, self.AUDIT_FILE)
        try:
            with open(export_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["City", "Date", "Time", "Type", "Amount", "Status"])
                for t in self.visible:
                    writer.writerow(t.to_export_row())
            self._log("EXPORT", self.visible)
            self.audit_log.write_to_file(audit_path)
        except OSError as e:
            raise FileLoadError(f"Export failed: {e}")
        return export_path, audit_path
 
 

if __name__ == "__main__":
    import sys
 
    if len(sys.argv) < 2:
        print("Usage: python backend.py <transactions.csv|json|txt>")
        sys.exit(1)
 
    engine = FinPayEngine()
    count = engine.load_data(sys.argv[1])
    print(f"Loaded {count} valid transactions; skipped {len(engine.skipped_rows)}")
    for msg in engine.skipped_rows:
        print("  skipped ->", msg)
    print("Cities:", engine.get_city_options())
    print("Dates :", engine.get_date_options())
    print("Summary:", engine.get_summary())
    engine.apply_filters(date="2026-10-19", ttype="Credit")
    for row in engine.get_ui_rows():
        print("  ", row)
    engine.revert_last_filter()
    print("After revert:", engine.get_summary()["count"], "rows")
    print("Exported:", engine.export())




