"""首次启动种子：39 个工具配置与站点设置。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import TOOLS
from app.db.models import SiteSetting, ToolConfig
from app.services.config_service import SITE_DEFAULTS


async def seed_database(session: AsyncSession) -> None:
    configs = {row.code: row for row in (await session.scalars(select(ToolConfig))).all()}

    for tool in TOOLS:
        existing = configs.get(tool.code)
        if existing is not None:
            # 历史上由种子写入、从未被维护者修改过的配置：工具实现后自动上线
            if tool.implemented and not existing.online and existing.updated_by is None:
                existing.online = True
            if tool.accepts_files and existing.max_file_mb is None and existing.updated_by is None:
                existing.max_file_mb = tool.default_max_file_mb
            continue
        session.add(
            ToolConfig(
                code=tool.code,
                online=tool.implemented,
                server_enabled=tool.engine in {"dual", "server"},
                max_file_mb=tool.default_max_file_mb,
                max_count=tool.default_max_count,
            )
        )

    settings = {row.key for row in (await session.scalars(select(SiteSetting))).all()}
    for key, value in SITE_DEFAULTS.items():
        if key not in settings:
            session.add(SiteSetting(key=key, value=value))

    await session.commit()
