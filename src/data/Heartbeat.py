from dataclasses import dataclass
from datetime import datetime
import psutil

@dataclass
class Heartbeat:
    timestamp: datetime
    status: str
    version: str
    cpu_load: list  
    memory_usage: float
    custom_message: str = ""

    @staticmethod
    def collect_system_metrics():
        # Pobranie aktualnych danych systemowych
        cpu_per_core = psutil.cpu_percent(percpu=True, interval=1)  # Zużycie CPU na każdy rdzeń
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.used / (1024 ** 2)  # Zużycie pamięci w MB

        return {
            "cpu_per_core": cpu_per_core,
            "memory_usage": memory_usage
        }
    


# Przykład inicjalizacji z dynamicznym pobraniem danych systemowych
system_metrics = Heartbeat.collect_system_metrics()

heartbeat = Heartbeat(
    timestamp=datetime.now(),
    status="OK",
    version="1.0.0",
    cpu_load=system_metrics["cpu_per_core"],
    memory_usage=system_metrics["memory_usage"],
    custom_message="All systems operational"
)

# Wyświetlenie wyników
print(f"Timestamp: {heartbeat.timestamp}")
print(f"Status: {heartbeat.status}")
print(f"Wersja: {heartbeat.version}")
print(f"Zużycie CPU na rdzeń: {heartbeat.cpu_load}")
print(f"Zużycie pamięci: {heartbeat.memory_usage:.2f} MB")
print(f"Custom message: {heartbeat.custom_message}")
