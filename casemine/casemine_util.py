from collections import namedtuple
from datetime import datetime

# Initialize proxy index
Proxy = namedtuple("Proxy", ["ip", "port"])

# List of US proxies
US_PROXIES = [
    Proxy("192.126.183.51", 8800),
    Proxy("192.126.181.9", 8800),
    Proxy("192.126.183.255", 8800),
    Proxy("192.126.183.131", 8800),
    Proxy("192.126.181.216", 8800),
]
us_proxy_index = -1

class CasemineUtil:

    @staticmethod
    def get_us_proxy():
        global us_proxy_index
        if us_proxy_index >= len(US_PROXIES) - 1:
            us_proxy_index = 0
        else:
            us_proxy_index += 1
        return US_PROXIES[us_proxy_index]

    @staticmethod
    def compare_date(date: str, craw_date: str) -> int:
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d/%b/%Y"]
        date1 = None
        date2 = None
        # Try parsing the dates with different formats
        for fmt in formats:
            try:
                date1 = datetime.strptime(date, fmt)
                date2 = datetime.strptime(craw_date, fmt)
                return (date1 > date2) - (
                        date1 < date2)  # 1 if date1 > date2, -1 if date1 < date2, 0 if equal
            except ValueError:
                continue  # Try the next format
        # Log the error if no formats matched
        print(f"Error while parsing the dates: {date}, {craw_date}")
        return 0  # Return 0 if no valid format was found