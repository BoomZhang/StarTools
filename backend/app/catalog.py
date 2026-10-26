"""39 个工具的静态目录：编号、slug、分类、引擎类型、默认限额与搜索别名。

这是前后端共用的唯一事实来源：管理台种子数据、公开工具目录与搜索结果都从这里生成。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CategoryDef:
    key: str
    name: str
    order: int
    blurb: str


CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef("image", "图片", 1, "轻量处理，服务端优先；可批量。"),
    CategoryDef("document", "文档与 PDF", 2, "合并、拆分了无痕迹；结果区会明确提示签名失效。"),
    CategoryDef("text", "文字", 3, "全部在浏览器本地执行，不发送文本内容。"),
    CategoryDef("encoding", "编码与生成", 4, "浏览器就是工作台；生成值不写入 URL 与本地存储。"),
    CategoryDef("qr", "二维码", 5, "内容直接编码进图形，不使用短链、不记录扫码内容。"),
    CategoryDef("ocr", "OCR", 6, "仅在服务端识别，支持图片与扫描件 PDF。"),
    CategoryDef("av", "音视频与语音", 7, "全部依赖服务端引擎；P1 能力上线后按同一规则运行。"),
)

CATEGORY_MAP = {item.key: item for item in CATEGORIES}


@dataclass(frozen=True)
class ToolDef:
    code: str
    slug: str
    name: str
    category: str
    engine: str  # dual | server | local
    priority: str  # P0 | P1
    summary: str
    formats: str
    pinyin: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)
    default_max_file_mb: int | None = None
    default_max_count: int = 1
    implemented: bool = True
    accepts_files: bool = True


TOOLS: tuple[ToolDef, ...] = (
    # ---------- 图片 ----------
    ToolDef(
        "IMG-01", "image-convert", "图片格式转换", "image", "dual", "P0",
        "HEIC、JPG、PNG、WebP、AVIF 等格式互转，统一移除拍摄信息。",
        "JPG · PNG · WEBP · AVIF · HEIC · TIFF · BMP · GIF", "tpgszh",
        ("heic转jpg", "jpg转png", "图片转换", "格式转换", "webp", "avif", "png转jpg", "tiff转jpg"),
        ("convert", "format", "image"), 50, 20,
    ),
    ToolDef(
        "IMG-02", "image-compress", "图片压缩", "image", "dual", "P0",
        "按质量或目标大小压缩，直接看到压缩率与前后体积。",
        "QUALITY · TARGET SIZE", "tpys",
        ("图片压缩", "压缩图片", "照片压缩", "减小图片"), ("compress", "quality", "size"), 50, 20,
    ),
    ToolDef(
        "IMG-03", "image-resize", "尺寸调整与裁剪", "image", "dual", "P0",
        "像素、百分比或常用尺寸，支持可视化裁剪、等比缩放与留白。",
        "PIXEL · RATIO · CROP", "ccdzylj",
        ("尺寸调整", "裁剪", "缩放", "resize", "改尺寸"), ("resize", "crop", "scale"), 50, 20,
    ),
    ToolDef(
        "IMG-04", "image-watermark", "图片加水印", "image", "dual", "P1",
        "文字或图片水印，九宫格定位、透明度与平铺，批量同一模板。",
        "TEXT · IMAGE · OPACITY", "tpjsy",
        ("加水印", "水印", "图片水印"), ("watermark",), 50, 20,
    ),
    ToolDef(
        "IMG-05", "image-stitch", "图片拼接", "image", "dual", "P1",
        "横向、纵向或 2×2 / 3×3 网格拼接，可拖拽排序并预览布局。",
        "HORIZONTAL · GRID · GAP", "tppj",
        ("拼图", "图片拼接", "长图"), ("stitch", "grid"), 50, 20,
    ),
    ToolDef(
        "IMG-06", "image-color-picker", "图片取色", "image", "local", "P1",
        "点选图片任意位置取色，输出 HEX、RGB、HSL 与六色主色板。",
        "HEX · RGB · HSL", "tpqs",
        ("取色", "吸色", "颜色", "色板"), ("color", "picker"), 50, 1,
    ),
    ToolDef(
        "IMG-07", "icon-generator", "图标生成", "image", "dual", "P1",
        "PNG / JPG 生成 16–256 px 多尺寸 PNG 与一个多尺寸 ICO。",
        "PNG · ICO · 6 SIZES", "tbsz",
        ("图标", "favicon", "ico", "图标生成"), ("icon", "favicon"), 50, 1,
    ),
    # ---------- 文档与 PDF ----------
    ToolDef(
        "DOC-01", "images-to-pdf", "图片转 PDF", "document", "dual", "P0",
        "多图排序后合成一个 PDF，支持 A4、Letter 或原图尺寸。",
        "A4 · LETTER · ORIGINAL", "tpzpdf",
        ("图片转pdf", "jpg转pdf", "照片转pdf", "多图合并pdf"), ("image", "pdf"), 50, 50,
    ),
    ToolDef(
        "DOC-02", "pdf-merge", "PDF 合并", "document", "dual", "P0",
        "多份 PDF 按列表顺序合并，保留每一页的原始尺寸。",
        "PDF · ORDER · MERGE", "pdfhb",
        ("pdf合并", "合并pdf", "多个pdf合并"), ("pdf", "merge", "combine"), 100, 20,
    ),
    ToolDef(
        "DOC-03", "pdf-split", "PDF 拆分", "document", "dual", "P0",
        "每页一份、每 N 页一份，或按自定义页码范围拆成多个文件。",
        "PAGE RANGE · ZIP", "pdfcf",
        ("pdf拆分", "拆分pdf", "pdf分页"), ("pdf", "split"), 100, 1,
    ),
    ToolDef(
        "DOC-04", "pdf-to-images", "PDF 转图片", "document", "dual", "P0",
        "以 72、144 或 300 DPI 将 PDF 页面批量导出为 PNG 或 JPG。",
        "PNG · JPG · 300 DPI", "pdfztp",
        ("pdf转图片", "pdf转jpg", "pdf转png"), ("pdf", "image", "png", "jpg"), 100, 1,
    ),
    ToolDef(
        "DOC-05", "pdf-pages", "PDF 页面管理", "document", "dual", "P1",
        "旋转、删除、拖拽排序或抽取页面，另存为新的 PDF。",
        "ROTATE · REORDER · EXTRACT", "pdfymgl",
        ("pdf页面", "页面管理", "pdf旋转", "pdf排序"), ("pdf", "rotate"), 100, 1,
    ),
    ToolDef(
        "DOC-06", "pdf-compress", "PDF 压缩", "document", "server", "P1",
        "轻、推荐、极致三档，图片降采样，文字仍保持可选中。",
        "LIGHT · BALANCED · MAX", "pdfys",
        ("pdf压缩", "压缩pdf"), ("pdf", "compress"), 100, 1,
    ),
    ToolDef(
        "DOC-07", "office-to-pdf", "Office 转 PDF", "document", "server", "P1",
        "DOCX、XLSX、PPTX 转 PDF，字体缺失会提示版式变化。",
        "DOCX · XLSX · PPTX", "officezpdf",
        ("office转pdf", "word转pdf", "excel转pdf", "ppt转pdf"), ("office", "word", "excel", "ppt"), 50, 1,
    ),
    ToolDef(
        "DOC-08", "pdf-to-word", "PDF 转 Word", "document", "server", "P1",
        "文本型 PDF 转 DOCX，版式尽力保留；扫描件会建议改用 OCR。",
        "PDF · DOCX · LAYOUT", "pdfzword",
        ("pdf转word", "pdf转docx"), ("pdf", "word", "docx"), 50, 1,
    ),
    ToolDef(
        "DOC-09", "pdf-password", "PDF 密码", "document", "server", "P1",
        "为 PDF 添加打开密码，或用已知密码移除保护；密码不入日志。",
        "AES-256 · ADD · REMOVE", "pdfmm",
        ("pdf密码", "加密pdf", "解密pdf"), ("pdf", "password"), 100, 1,
    ),
    # ---------- 文字 ----------
    ToolDef(
        "TXT-01", "text-count", "文本统计", "text", "local", "P0",
        "边输入边统计，也可上传 TXT、Markdown、CSV 等文本文件统计。",
        "LIVE · FILE · UNICODE", "wbjstj",
        ("字数统计", "文本统计", "统计字数", "字数", "文件字数"), ("count", "word", "file"), 10, 1,
    ),
    ToolDef(
        "TXT-03", "json-format", "JSON 格式化", "text", "local", "P0",
        "美化、压缩、校验与转义，语法出错时定位到行列。",
        "PRETTY · MINIFY · VALIDATE", "json格式化",
        ("json", "json格式化", "json校验", "json压缩"), ("json", "format", "validate"), None, 1, accepts_files=False,
    ),
    ToolDef(
        "TXT-06", "markdown-preview", "Markdown 预览", "text", "local", "P1",
        "边写边预览，支持 GFM 表格与代码块；可导出自包含 HTML。",
        "GFM · PREVIEW · HTML", "markdownyl",
        ("markdown", "md预览", "md"), ("markdown", "preview"), None, 1, accepts_files=False,
    ),
    ToolDef(
        "TXT-07", "regex-test", "正则测试", "text", "local", "P1",
        "匹配列表、分组高亮、替换预览，异常正则带超时保护。",
        "MATCH · GROUP · REPLACE", "zzcs",
        ("正则", "regex", "正则表达式"), ("regex", "replace"), None, 1, accepts_files=False,
    ),
    # ---------- 编码与生成 ----------
    ToolDef(
        "ENC-01", "base64", "Base64 编解码", "encoding", "local", "P0",
        "文本与文件编码，支持 URL-safe 与 data URI 前缀。",
        "TEXT · FILE · URL-SAFE", "base64",
        ("base64", "b64", "base64编码", "base64解码"), ("base64", "encode"), 10, 1,
    ),
    ToolDef(
        "ENC-02", "url-codec", "URL 编解码", "encoding", "local", "P0",
        "组件编码、表单编码与解码，错误位置直接指出。",
        "COMPONENT · FORM", "urlbm",
        ("url编码", "url解码", "urlencode", "urldecode"), ("url", "encode", "decode"), None, 1, accepts_files=False,
    ),
    ToolDef(
        "ENC-03", "hash", "哈希计算", "encoding", "local", "P0",
        "MD5、SHA-1、SHA-256、SHA-512，支持文本与分块读取文件。",
        "MD5 · SHA-256 · FILE", "hxjs",
        ("哈希", "md5", "sha256", "sha1", "校验和"), ("hash", "md5", "sha"), 200, 1,
    ),
    ToolDef(
        "ENC-04", "timestamp", "时间戳转换", "encoding", "local", "P0",
        "秒与毫秒时间戳、日期、时区和 ISO 8601 互转。",
        "UNIX · UTC · ISO 8601", "sjjzh",
        ("时间戳", "timestamp", "unix", "日期转换"), ("time", "unix", "timestamp"), None, 1, accepts_files=False,
    ),
    ToolDef(
        "ENC-05", "random-password", "随机与密码", "encoding", "local", "P0",
        "UUID、随机字符串或密码，只使用浏览器安全随机源。",
        "UUID · RANDOM · PASSWORD", "sjmima",
        ("uuid", "密码生成", "随机密码", "随机串"), ("uuid", "password", "random"), None, 1, accepts_files=False,
    ),
    # ---------- 二维码 ----------
    ToolDef(
        "QR-01", "qr-generate", "二维码生成", "qr", "local", "P0",
        "文本、网址、WiFi、名片、短信、邮件或电话，即输即得。",
        "URL · WIFI · VCARD", "ewmsc",
        ("二维码", "二维码生成", "qrcode", "wifi二维码"), ("qr", "qrcode", "generate"), None, 1, accepts_files=False,
    ),
    ToolDef(
        "QR-02", "qr-scan", "二维码识别", "qr", "local", "P0",
        "从图片、粘贴内容或摄像头识别二维码，图片不离开本机。",
        "IMAGE · CAMERA · LOCAL", "ewmsb",
        ("二维码识别", "扫码", "qr识别", "解读二维码"), ("qr", "scan", "decode"), 20, 1,
    ),
    ToolDef(
        "QR-03", "qr-batch", "批量二维码", "qr", "local", "P1",
        "多行文本或 CSV 一次生成多张二维码，打包为 ZIP 下载。",
        "CSV · BATCH · ZIP", "pilewm",
        ("批量二维码", "二维码批量", "批量生成二维码"), ("qr", "batch"), 2, 1, accepts_files=False,
    ),
    ToolDef(
        "QR-04", "qr-style", "二维码美化", "qr", "local", "P1",
        "自定义颜色、圆点与中心 Logo，生成前自动检查可扫性。",
        "COLOR · DOT · LOGO", "ewmms",
        ("二维码美化", "美化二维码"), ("qr", "style"), 2, 1,
    ),
    # ---------- OCR ----------
    ToolDef(
        "OCR-01", "ocr", "图片文字识别", "ocr", "server", "P0",
        "中英混排图片识别，结果可编辑、复制或导出 TXT、Markdown。",
        "中英混排 · 10 张", "tzwzsh",
        ("ocr", "图片文字识别", "扫描文字", "文字识别", "图片转文字"), ("ocr", "text", "image"), 20, 10,
    ),
    ToolDef(
        "OCR-02", "pdf-ocr", "PDF 文字识别", "ocr", "server", "P1",
        "扫描件 PDF 逐页识别，输出 TXT 或带文本层的可搜索 PDF。",
        "PDF · TXT · SEARCHABLE", "pdfwzsh",
        ("pdf识别", "pdf转文字", "扫描pdf识别"), ("pdf", "ocr"), 50, 1,
    ),
    ToolDef(
        "OCR-03", "table-ocr", "表格识别", "ocr", "server", "P1",
        "表格结构识别并导出 XLSX；合并单元格为尽力还原。",
        "TABLE · XLSX", "bgsh",
        ("表格识别", "表格转excel", "识别表格"), ("table", "excel", "ocr"), 20, 10,
    ),
    # ---------- 音视频与语音 ----------
    ToolDef(
        "AV-01", "audio-convert", "音频格式转换", "av", "server", "P1",
        "MP3、WAV、M4A、AAC、FLAC、OGG、OPUS、WMA、AIFF 互转；单文件不超过 60 分钟。",
        "MP3 · WAV · M4A · AAC · FLAC · OGG · OPUS · WMA · AIFF", "ypzh",
        ("音频转换", "音频格式转换", "mp3转wav", "ogg转mp3", "aac转mp3"), ("audio", "convert", "mp3"), 200, 1,
    ),
    ToolDef(
        "AV-02", "video-to-gif", "视频转 GIF", "av", "server", "P1",
        "截取片段生成 GIF，可调帧率、宽度与循环，实时预估体积。",
        "MP4 · MOV · MKV · AVI · GIF", "spzgif",
        ("视频转gif", "gif", "视频截取"), ("video", "gif"), 500, 1,
    ),
    ToolDef(
        "AV-03", "video-compress", "视频压缩", "av", "server", "P1",
        "三档预设或高级参数压缩，可控制编码、码率、分辨率、帧率、裁剪与音频。",
        "MP4 · H.264/H.265 · CRF · BITRATE", "spys",
        ("视频压缩", "压缩视频"), ("video", "compress"), 500, 1,
    ),
    ToolDef(
        "AV-04", "extract-audio", "提取音频", "av", "server", "P1",
        "从视频导出音频轨，可选 MP3、M4A、WAV、FLAC、AAC、OGG 等格式。",
        "MP3 · M4A · WAV · FLAC · AAC · OGG · OPUS · WMA · AIFF", "tqyp",
        ("提取音频", "视频转音频"), ("video", "audio", "extract"), 500, 1,
    ),
    ToolDef(
        "AV-05", "video-convert", "视频格式转换", "av", "server", "P1",
        "MP4、WebM、MOV、MKV、AVI、FLV、M4V、WMV、TS 互转，提示编码兼容性风险。",
        "MP4 · WEBM · MOV · MKV · AVI · FLV · M4V · WMV · TS", "spzh",
        ("视频格式转换", "视频转换"), ("video", "convert"), 500, 1,
    ),
    ToolDef(
        "AV-06", "speech-to-text", "语音转文字", "av", "server", "P1",
        "音频转可编辑文本，支持时间戳与 SRT 字幕。",
        "MP3 · WAV · M4A · AAC · FLAC · OGG · OPUS · WMA · AIFF", "yyzwz",
        ("语音转文字", "音频转文字", "录音转文字", "srt"), ("speech", "text", "audio"), 200, 1,
    ),
    ToolDef(
        "AV-07", "text-to-speech", "文字转语音", "av", "server", "P1",
        "文本合成可试听、可下载的音频，只使用内置通用音色。",
        "TEXT · MP3 · WAV", "wzzhy",
        ("文字转语音", "tts", "语音合成"), ("tts", "speech", "audio"), None, 1, accepts_files=False,
    ),
)

CODE_MAP = {tool.code: tool for tool in TOOLS}
SLUG_MAP = {tool.slug: tool for tool in TOOLS}

P0_TOOLS = tuple(tool for tool in TOOLS if tool.priority == "P0")
IMPLEMENTED_TOOLS = tuple(tool for tool in TOOLS if tool.implemented)


def categories_payload() -> list[dict]:
    return [
        {
            "key": item.key,
            "name": item.name,
            "order": item.order,
            "blurb": item.blurb,
            "total": sum(1 for tool in TOOLS if tool.category == item.key),
        }
        for item in CATEGORIES
    ]


def tool_payload(tool: ToolDef) -> dict:
    return {
        "code": tool.code,
        "slug": tool.slug,
        "name": tool.name,
        "category": tool.category,
        "category_name": CATEGORY_MAP[tool.category].name,
        "engine_type": tool.engine,
        "priority": tool.priority,
        "summary": tool.summary,
        "formats": tool.formats,
        "pinyin": tool.pinyin,
        "aliases": list(tool.aliases),
        "keywords": list(tool.keywords),
        "default_max_file_mb": tool.default_max_file_mb,
        "default_max_count": tool.default_max_count,
        "implemented": tool.implemented,
        "accepts_files": tool.accepts_files,
    }
