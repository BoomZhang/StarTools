"""工具配置读取与公开视图组装。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import CATEGORY_MAP, CODE_MAP, TOOLS, ToolDef, tool_payload
from app.db.models import SiteSetting, ToolConfig
from app.services.common import disk_accepts_tasks, disk_usage_percent
from app.services.images import available_output_formats
from app.services.runner import availability

SITE_DEFAULTS = {
    "site_name": "随手工具箱",
    "logo_text": "随",
    "feedback_enabled": "true",
    "privacy_links_enabled": "true",
    "upload_consent_enabled": "true",
    "show_engine_badge": "true",
    "site_announcement": "",
}


def site_setting(settings: dict[str, str], key: str) -> str:
    return settings.get(key, SITE_DEFAULTS.get(key, ""))


def setting_bool(settings: dict[str, str], key: str) -> bool:
    return site_setting(settings, key) == "true"


async def load_configs(session: AsyncSession) -> dict[str, ToolConfig]:
    rows = (await session.scalars(select(ToolConfig))).all()
    return {row.code: row for row in rows}


async def get_site_settings(session: AsyncSession) -> dict[str, str]:
    rows = (await session.scalars(select(SiteSetting))).all()
    return {row.key: row.value for row in rows}


def effective_engine(tool: ToolDef, config: ToolConfig) -> str:
    if tool.engine == "server":
        return "server"
    if tool.engine == "local":
        return "local"
    return "server" if config.server_enabled else "local"


def public_tool(tool: ToolDef, config: ToolConfig) -> dict:
    payload = tool_payload(tool)
    available, reason = availability(tool)
    engine = effective_engine(tool, config)
    if engine == "server" and not disk_accepts_tasks():
        available, reason = False, "服务端任务暂不可用，前端工具正常"
    payload.update(
        {
            "online": config.online,
            "engine": engine,
            "server_enabled": config.server_enabled,
            "max_file_mb": config.max_file_mb,
            "max_count": config.max_count,
            "available": available,
            "unavailable_reason": reason,
        }
    )
    return payload


async def site_payload(session: AsyncSession) -> dict:
    configs = await load_configs(session)
    settings = await get_site_settings(session)
    online_tools = [
        public_tool(tool, configs[tool.code])
        for tool in TOOLS
        if tool.implemented and configs.get(tool.code) and configs[tool.code].online
    ]
    return {
        "site": {
            "name": site_setting(settings, "site_name"),
            "logo_text": site_setting(settings, "logo_text"),
            "feedback_enabled": setting_bool(settings, "feedback_enabled"),
            "privacy_links_enabled": setting_bool(settings, "privacy_links_enabled"),
            "upload_consent_enabled": setting_bool(settings, "upload_consent_enabled"),
            "show_engine_badge": setting_bool(settings, "show_engine_badge"),
            "announcement": site_setting(settings, "site_announcement"),
            "total_tools": len(TOOLS),
            "online_tools": len(online_tools),
            "server_available": disk_accepts_tasks(),
            "disk_percent": disk_usage_percent(),
            "retention": {
                "raw_days": 30,
                "result_minutes": 60,
                "record_days": 90,
            },
            "capabilities": {
                "image_output_formats": available_output_formats(),
                "ocr_available": availability(CODE_MAP["OCR-01"])[0],
            },
        },
        "categories": [
            {
                "key": item.key,
                "name": item.name,
                "order": item.order,
                "blurb": item.blurb,
                "total": sum(1 for tool in TOOLS if tool.category == item.key),
            }
            for item in CATEGORY_MAP.values()
        ],
        "tools": online_tools,
    }


async def find_tool_by_slug(session: AsyncSession, slug: str) -> tuple[ToolDef | None, ToolConfig | None]:
    from app.catalog import SLUG_MAP

    tool = SLUG_MAP.get(slug)
    if tool is None:
        return None, None
    config = await session.scalar(select(ToolConfig).where(ToolConfig.code == tool.code))
    return tool, config
