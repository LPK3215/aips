from app.services.rate_limit_service import RateLimitService


def test_rate_limit_service_prunes_stale_identifiers_across_clients() -> None:
    service = RateLimitService()

    service.check("upload", "client-a", now=0)
    service.check("upload", "client-b", now=0)

    assert len(service._requests) == 2

    service.check("upload", "client-c", now=61)

    assert len(service._requests) == 1
    assert ("upload", "client-c") in service._requests
