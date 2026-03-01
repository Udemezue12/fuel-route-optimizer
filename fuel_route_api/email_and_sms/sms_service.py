import httpx

from fuel_route_api.core.env import TERMII_API_KEY, TERMII_BASE_URL, TERMII_SENDER_ID


class TermiiClient:
    def __init__(self):
        self.base_url = TERMII_BASE_URL
        self.api_key = TERMII_API_KEY
        self.async_client: httpx.AsyncClient | None = None
        self.sync_client: httpx.Client | None = None

    def sync_connect(self):
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=10,
        )

    def sync_close(self):
        if self.sync_client:
            self.sync_client.close()

    async def async_connect(self):
        self.async_client = httpx.AsyncClient(base_url=self.base_url, timeout=10)

    async def async_close(self):
        if self.async_client:
            await self.async_client.aclose()

    async def ping(self):
        if not self.async_client:
            raise RuntimeError("Termii client not connected")

        try:
            test_payload = {
                "to": "2340000000000",
                "from": TERMII_SENDER_ID,
                "sms": "Ping test",
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }
            response = await self.async_client.post("/api/sms/send", json=test_payload)
            if response.status_code == 200:
                print("Termii API ping successful!")
                return True
            else:
                print(
                    f"Termii API ping returned {response.status_code}:",
                    response.json(),
                )
                return False
        except Exception as e:
            print("Termii ping error:", e)
            return False

    def send_otp_sms(
        self,
        to: str,
        otp: str | None = None,
        message: str | None = None,
        name: str | None = None,
        sender_id=TERMII_SENDER_ID,
    ):
        try:
            self.sync_connect()
            if not message:
                if name:
                    message = (
                        f"Hello {name}, your OTP is {otp}. "
                        "This code expires in 5 minutes. Do not share it with anyone."
                    )
                else:
                    message = (
                        f"Your OTP is {otp}. "
                        "This code expires in 5 minutes. Do not share it with anyone."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.sync_client:
                raise RuntimeError("Termii client not connected")

            response = self.sync_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            self.sync_close()

    async def async_send_paid_sms(
        self,
        to: str,
        amount: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
            if not message:
                if name:
                    message = (
                        f"Hello {name}, we have received your payment of {amount}.\n\n"
                        "Thank you for your prompt payment."
                    )
                else:
                    message = (
                        f"We have received your payment of {amount}.\n\n"
                        "Thank you for your prompt payment."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    async def async_send_refund_sms(
        self,
        to: str,
        amount: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
            if not message:
                if name:
                    message = (
                        f"Hello {name}, we have issued a refund for payment of {amount}.\n\n"
                        "Thank you for your understanding."
                    )
                else:
                    message = (
                        f"We have issued a refund for the {amount}.\n\n"
                        "Thank you for your prompt understanding."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    def sync_send_refund_sms(
        self,
        to: str,
        amount: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=TERMII_SENDER_ID,
    ):
        try:
            self.sync_connect()
            if not message:
                if name:
                    message = (
                        f"Hello {name}, we have issued a refund for payment of {amount}.\n\n"
                        "Thank you for your understanding."
                    )
                else:
                    message = (
                        f"We have issued a refund for the {amount}.\n\n"
                        "Thank you for your prompt understanding."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = self.sync_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            self.sync_close()

    def sync_send_expired_sms(
        self,
        to: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=TERMII_SENDER_ID,
    ):
        try:
            self.sync_connect()
            if not message:
                if name:
                    message = (
                        f"Hello {name}, your subscription has expired.\n\n"
                        "Do well to renew your subscription and thanks for your continuous patronage."
                    )
                else:
                    message = (
                        "Hello your subscription has expired.\n\n"
                        "Do well to renew your subscription and thanks for your continuous patronage."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.sync_client:
                raise RuntimeError("Termii client not connected")

            response = self.sync_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            self.sync_close()


send_sms = TermiiClient()