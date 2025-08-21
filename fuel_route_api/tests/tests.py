from unittest.mock import AsyncMock, patch

import pytest
from ninja.testing import TestAsyncClient

from fuel_route_api.models import FuelStation
from fuel_route_api.register_controller import api
from fuel_route_api.tasks import calculate_route_task


@pytest.mark.django_db
@pytest.mark.asyncio
class TestRouteAPI:
    @pytest.fixture
    async def client(self):
        return TestAsyncClient(api)

    @pytest.fixture
    def fuel_station(self):
        return FuelStation.objects.create(
            opis_truckstop_id=7,
            truckstop_name="WOODSHED OF BIG CABIN",
            address="I-44, EXIT 283 & US-69",
            city="Big Cabin",
            state="OK",
            rack_id=307,
            retail_price=3.00733333,
            latitude=36.5381,
            longitude=-95.2214,
        )

    async def test_trigger_route_calculation(self, client):
        response = await client.post(
            "/route/calculate",
            json={
                "start": {"latitude": 36.5381, "longitude": -95.2214},
                "finish": {"latitude": 44.0247, "longitude": -91.6393},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["PENDING", "STARTED"]

    async def test_invalid_coordinates(self, client):
        response = await client.post(
            "/route/calculate",
            json={
                "start": {"latitude": 0, "longitude": 0},
                "finish": {"latitude": 44.0247, "longitude": -91.6393},
            },
        )
        assert response.status_code == 400
        assert "Locations must be within the USA" in response.json().get("detail", "")

    async def test_get_task_result_success(self, client, fuel_station):
        tomtom_response = {
            "routes": [
                {
                    "summary": {"lengthInMeters": 1609340},
                    "legs": [
                        {
                            "points": [
                                {"latitude": 36.5381, "longitude": -95.2214},
                                {"latitude": 44.0247, "longitude": -91.6393},
                            ]
                        }
                    ],
                }
            ]
        }
        with patch("aiohttp.ClientSession.get", new=AsyncMock()) as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=tomtom_response
            )

            response = await client.post(
                "/route/calculate",
                json={
                    "start": {"latitude": 36.5381, "longitude": -95.2214},
                    "finish": {"latitude": 44.0247, "longitude": -91.6393},
                },
            )
            task_id = response.json()["task_id"]

            calculate_route_task.apply(
                args=[36.5381, -95.2214, 44.0247, -91.6393]
            ).get()

            response = await client.get(f"/route/task/{task_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "SUCCESS"
            assert data["result"]["total_distance_miles"] == 1000.0
            assert len(data["result"]["fuel_stops"]) >= 1
            assert "route" in data["result"]
            assert "total_fuel_cost" in data["result"]

    async def test_task_result_caching(self, client, fuel_station):
        tomtom_response = {
            "routes": [
                {
                    "summary": {"lengthInMeters": 482803},
                    "legs": [
                        {
                            "points": [
                                {"latitude": 36.5381, "longitude": -95.2214},
                                {"latitude": 44.0247, "longitude": -91.6393},
                            ]
                        }
                    ],
                }
            ]
        }
        with patch("aiohttp.ClientSession.get", new=AsyncMock()) as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=tomtom_response
            )

            response1 = await client.post(
                "/route/calculate",
                json={
                    "start": {"latitude": 36.5381, "longitude": -95.2214},
                    "finish": {"latitude": 44.0247, "longitude": -91.6393},
                },
            )
            task_id = response1.json()["task_id"]

            calculate_route_task.apply(
                args=[36.5381, -95.2214, 44.0247, -91.6393]
            ).get()

            response2 = await client.get(f"/route/task/{task_id}")
            response3 = await client.get(f"/route/task/{task_id}")
            assert response2.status_code == 200
            assert response3.status_code == 200
            assert response2.json() == response3.json()
            assert mock_get.call_count == 1

    async def test_throttling(self, client):
        for _ in range(101):
            response = await client.post(
                "/route/calculate",
                json={
                    "start": {"latitude": 36.5381, "longitude": -95.2214},
                    "finish": {"latitude": 44.0247, "longitude": -91.6393},
                },
            )
            if response.status_code == 429:
                assert "Request limit exceeded" in response.json().get("detail", "")
                break
        else:
            pytest.fail("Throttling did not trigger")

    async def test_task_failure(self, client):
        with patch("aiohttp.ClientSession.get", new=AsyncMock()) as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 500
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value={}
            )

            response = await client.post(
                "/route/calculate",
                json={
                    "start": {"latitude": 36.5381, "longitude": -95.2214},
                    "finish": {"latitude": 44.0247, "longitude": -91.6393},
                },
            )
            task_id = response.json()["task_id"]

            with pytest.raises(Exception):
                calculate_route_task.apply(
                    args=[36.5381, -95.2214, 44.0247, -91.6393]
                ).get()

            response = await client.get(f"/route/task/{task_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "FAILURE"
            assert response.json()["result"] is None
