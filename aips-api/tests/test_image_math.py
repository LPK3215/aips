from app.schemas.images import CustomSize, DimensionUnit
from app.utils.image_math import resolve_output_size


def test_resolve_centimeter_output_size() -> None:
    size = CustomSize(width=3.5, height=5.3, unit=DimensionUnit.CM, dpi=300)
    assert resolve_output_size(size) == (413, 626)


def test_resolve_pixel_output_size() -> None:
    size = CustomSize(width=295, height=413, unit=DimensionUnit.PX, dpi=300)
    assert resolve_output_size(size) == (295, 413)

