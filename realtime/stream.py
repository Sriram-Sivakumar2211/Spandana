import json
import urllib.request
import urllib.error

class StreamClient:
    """
    Client for transmitting streamed machine sensor window records to backend endpoints.
    """
    def __init__(self, endpoint_url: str = "http://localhost:8000/api/v1/sensor-stream"):
        self.endpoint_url = endpoint_url

    def post_window(self, window_record: dict, timeout: float = 2.0) -> bool:
        """
        POSTs a single standardized window record to the target backend API endpoint.
        Returns True if successful, False if endpoint is unreachable.
        """
        payload_bytes = json.dumps(window_record).encode('utf-8')
        req = urllib.request.Request(
            self.endpoint_url,
            data=payload_bytes,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 201, 202)
        except (urllib.error.URLError, TimeoutError, OSError):
            # Gracefully ignore connection errors when backend dev server is offline
            return False

if __name__ == "__main__":
    client = StreamClient()
    dummy_payload = {
        "machine_id": "MOTOR_001",
        "timestamp": "2026-07-21T10:30:00Z",
        "source": "metropt3",
        "window_id": "window_0001",
        "features": {
            "rms": 0.42, "kurtosis": 3.8, "skewness": 0.2, "crest_factor": 4.1,
            "dominant_frequency": 120.5, "temperature": 65.2, "current": 4.2, "rpm": 1480.0
        },
        "label": "healthy"
    }
    success = client.post_window(dummy_payload)
    print(f"Post payload status: {success}")
