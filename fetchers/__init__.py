"""
公司新聞爬蟲

支援的公司 (19 家)：

上游 - 設備/材料：
- ASML (Playwright)
- Tokyo Electron (Playwright)
- Lam Research (Playwright)
- SUMCO (Playwright)
- SK Siltron (無獨立新聞頁面)

中游 - 製造/封測：
- Samsung (RSS)
- SK hynix (Playwright)
- Micron (Playwright)
- 南亞科技 (Playwright)
- 華邦電子 (Playwright)
- 日月光 (Playwright)
- 力成科技 (Playwright)
- 南茂科技 (Playwright)

下游 - 客戶：
- NVIDIA (RSS)
- AMD (RSS)
- Apple (RSS)
- AWS (Playwright)
- Microsoft (Playwright)
- Google Cloud (Playwright)
"""

from .base import CompanyFetcher, CompanyDocument

# 上游 - 設備/材料
from .asml import ASMLFetcher
from .tokyo_electron import TokyoElectronFetcher
from .lam_research import LamResearchFetcher
from .sumco import SUMCOFetcher
from .sk_siltron import SKSiltronFetcher

# 中游 - 製造
from .samsung import SamsungFetcher
from .skhynix import SKHynixFetcher
from .micron import MicronFetcher
from .nanya import NanyaFetcher
from .winbond import WinbondFetcher

# 中游 - 封測
from .ase import ASEFetcher
from .powertech import PowertechFetcher
from .chipmos import ChipMOSFetcher

# 下游 - 客戶
from .nvidia import NVIDIAFetcher
from .amd import AMDFetcher
from .apple import AppleFetcher
from .aws import AWSFetcher
from .microsoft import MicrosoftFetcher
from .google_cloud import GoogleCloudFetcher

__all__ = [
    "CompanyFetcher",
    "CompanyDocument",
    # 上游
    "ASMLFetcher",
    "TokyoElectronFetcher",
    "LamResearchFetcher",
    "SUMCOFetcher",
    "SKSiltronFetcher",
    # 中游 - 製造
    "SamsungFetcher",
    "SKHynixFetcher",
    "MicronFetcher",
    "NanyaFetcher",
    "WinbondFetcher",
    # 中游 - 封測
    "ASEFetcher",
    "PowertechFetcher",
    "ChipMOSFetcher",
    # 下游
    "NVIDIAFetcher",
    "AMDFetcher",
    "AppleFetcher",
    "AWSFetcher",
    "MicrosoftFetcher",
    "GoogleCloudFetcher",
]

# 爬蟲對照表 (company_id -> Fetcher class)
FETCHERS = {
    # 上游 - 設備/材料
    "asml": ASMLFetcher,
    "tokyo_electron": TokyoElectronFetcher,
    "lam_research": LamResearchFetcher,
    "sumco": SUMCOFetcher,
    "sk_siltron": SKSiltronFetcher,
    # 中游 - 製造
    "samsung": SamsungFetcher,
    "skhynix": SKHynixFetcher,
    "micron": MicronFetcher,
    "nanya": NanyaFetcher,
    "winbond": WinbondFetcher,
    # 中游 - 封測
    "ase": ASEFetcher,
    "powertech": PowertechFetcher,
    "ptc": ChipMOSFetcher,  # 南茂科技
    # 下游 - 客戶
    "nvidia": NVIDIAFetcher,
    "amd": AMDFetcher,
    "apple": AppleFetcher,
    "aws": AWSFetcher,
    "microsoft": MicrosoftFetcher,
    "google": GoogleCloudFetcher,
}
