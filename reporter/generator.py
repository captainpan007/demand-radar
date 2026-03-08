"""HTML 报告生成"""
from datetime import datetime
from pathlib import Path

from jinja2 import Template
from models import DemandItem


def generate_report(
    items: list[DemandItem],
    total_raw: int = 0,
    output_dir: str | Path = "output",
) -> str:
    """生成 HTML 报告，返回文件路径"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template_path = Path(__file__).parent / "template.html"
    template = Template(template_path.read_text(encoding="utf-8"))

    date_str = datetime.now().strftime("%Y-%m-%d")
    html = template.render(
        date=date_str,
        total=total_raw,
        count=len(items),
        items=items,
    )

    out_path = output_dir / f"demand-radar-{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)
