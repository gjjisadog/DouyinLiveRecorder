"""Core enums."""

from enum import Enum


class Platform(str, Enum):
    UNKNOWN = "unknown"
    DIRECT = "direct"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"
    KUAISHOU = "kuaishou"
    HUYA = "huya"
    DOUYU = "douyu"
    YY = "yy"
    BILIBILI = "bilibili"
    NETEASE_CC = "netease_cc"
    QIANDUREBO = "qiandurebo"
    PANDATV = "pandatv"
    BAIDU = "baidu"
    SHOWROOM = "showroom"
    CHZZK = "chzzk"


class TaskStatus(str, Enum):
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class OutputFormat(str, Enum):
    TS = "ts"
    MKV = "mkv"
    FLV = "flv"
    MP4 = "mp4"
    MP3 = "mp3"
    M4A = "m4a"
