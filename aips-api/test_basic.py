from pathlib import Path
from PIL import Image

from app.schemas.images import (
    Adjustments,
    CustomSize,
    OutputOptions,
    ProcessRequest,
    RenderState,
)
from app.services.image_service import image_service


def test_basic_image_processing():
    """测试基本的图像处理功能"""
    # 创建临时测试图像
    source_path = Path("test_image.png")
    source = Image.new("RGB", (1200, 1600), "#d4c8b8")
    source.save(source_path, format="PNG")
    
    # 创建测试请求
    request = ProcessRequest(
        file_id="test",
        custom_size=CustomSize(width=413, height=626, unit="px", dpi=300),
        render=RenderState(
            viewport_width=320,
            viewport_height=486,
            scale=0.32,
            offset_x=0,
            offset_y=0,
            fit_mode="fill",
        ),
        adjustments=Adjustments(sharpness=20),
        output=OutputOptions(
            format="jpg",
            dpi=300,
            quality=90,
            filename="test-output.jpg",
            background_color="#f5f1e8",
        ),
    )
    
    # 创建输出目录
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # 处理图像
        artifact = image_service.process_image(source_path, request, output_dir, preset_name="测试")
        
        # 验证结果
        assert artifact.output_path.exists(), "输出文件不存在"
        assert artifact.meta.width_px == 413, f"宽度不符合预期: {artifact.meta.width_px}"
        assert artifact.meta.height_px == 626, f"高度不符合预期: {artifact.meta.height_px}"
        assert artifact.meta.format == "jpg", f"格式不符合预期: {artifact.meta.format}"
        
        # 验证图像文件
        with Image.open(artifact.output_path) as result:
            assert result.size == (413, 626), f"图像尺寸不符合预期: {result.size}"
            assert result.format == "JPEG", f"图像格式不符合预期: {result.format}"
        
        print("✅ 基本图像处理测试通过！")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 清理临时文件
        if source_path.exists():
            source_path.unlink()
        if output_dir.exists():
            for file in output_dir.iterdir():
                file.unlink()
            output_dir.rmdir()


if __name__ == "__main__":
    test_basic_image_processing()