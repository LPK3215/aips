from app.schemas.images import CustomSize, DimensionUnit


def resolve_output_size(size: CustomSize) -> tuple[int, int]:
    if size.unit == DimensionUnit.PX:
        return max(1, round(size.width)), max(1, round(size.height))

    if size.unit == DimensionUnit.CM:
        width_inch = size.width / 2.54
        height_inch = size.height / 2.54
    elif size.unit == DimensionUnit.MM:
        width_inch = size.width / 25.4
        height_inch = size.height / 25.4
    elif size.unit == DimensionUnit.INCH:
        width_inch = size.width
        height_inch = size.height
    else:  # pragma: no cover - enum already guards this
        raise ValueError(f"不支持的尺寸单位: {size.unit}")

    return max(1, round(width_inch * size.dpi)), max(1, round(height_inch * size.dpi))
