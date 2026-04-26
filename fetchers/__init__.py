"""
公司新聞爬蟲

支援的公司 (53 家)
"""

from .base import CompanyFetcher, CompanyDocument

# 上游 - 設備/材料/EDA/IP
from .asml import ASMLFetcher
from .tokyo_electron import TokyoElectronFetcher
from .lam_research import LamResearchFetcher
from .sumco import SUMCOFetcher
from .sk_siltron import SKSiltronFetcher
from .applied_materials import AppliedMaterialsFetcher
from .kla import KLAFetcher
from .screen import ScreenFetcher
from .shin_etsu import ShinEtsuFetcher
from .entegris import EntegrisFetcher
from .synopsys import SynopsysFetcher
from .cadence import CadenceFetcher
from .arm import ArmFetcher

# 中游 - 製造
from .samsung import SamsungFetcher
from .skhynix import SKHynixFetcher
from .micron import MicronFetcher
from .nanya import NanyaFetcher
from .winbond import WinbondFetcher
from .kioxia import KioxiaFetcher
from .western_digital import WesternDigitalFetcher
from .cxmt import CXMTFetcher
from .ymtc import YMTCFetcher
from .phison import PhisonFetcher
from .silicon_motion import SiliconMotionFetcher
from .macronix import MacronixFetcher
from .elite_semi import EliteSemiFetcher
from .adata import AdataFetcher
from .innodisk import InnodiskFetcher
from .tsmc import TSMCFetcher
from .intel import IntelFetcher
from .psmc import PSMCFetcher

# 中游 - 封測
from .ase import ASEFetcher
from .powertech import PowertechFetcher
from .chipmos import ChipMOSFetcher
from .amkor import AmkorFetcher

# 下游 - GPU/晶片
from .nvidia import NVIDIAFetcher
from .amd import AMDFetcher
from .broadcom import BroadcomFetcher
from .qualcomm import QualcommFetcher
from .marvell import MarvellFetcher
from .ti import TIFetcher
from .onsemi import OnsemiFetcher
from .infineon import InfineonFetcher

# 下游 - 系統/CSP
from .apple import AppleFetcher
from .dell import DellFetcher
from .hp import HPFetcher
from .lenovo import LenovoFetcher
from .supermicro import SupermicroFetcher
from .aws import AWSFetcher
from .microsoft import MicrosoftFetcher
from .google_cloud import GoogleCloudFetcher
from .meta import MetaFetcher
from .oracle import OracleFetcher

# 爬蟲對照表 (company_id -> Fetcher class)
FETCHERS = {
    # 上游 - 設備/材料/EDA/IP
    "asml": ASMLFetcher,
    "tokyo_electron": TokyoElectronFetcher,
    "lam_research": LamResearchFetcher,
    "sumco": SUMCOFetcher,
    "sk_siltron": SKSiltronFetcher,
    "applied_materials": AppliedMaterialsFetcher,
    "kla": KLAFetcher,
    "screen": ScreenFetcher,
    "shin_etsu": ShinEtsuFetcher,
    "entegris": EntegrisFetcher,
    "synopsys": SynopsysFetcher,
    "cadence": CadenceFetcher,
    "arm": ArmFetcher,
    # 中游 - 製造
    "samsung": SamsungFetcher,
    "skhynix": SKHynixFetcher,
    "micron": MicronFetcher,
    "nanya": NanyaFetcher,
    "winbond": WinbondFetcher,
    "kioxia": KioxiaFetcher,
    "western_digital": WesternDigitalFetcher,
    "cxmt": CXMTFetcher,
    "ymtc": YMTCFetcher,
    "phison": PhisonFetcher,
    "silicon_motion": SiliconMotionFetcher,
    "macronix": MacronixFetcher,
    "elite_semi": EliteSemiFetcher,
    "adata": AdataFetcher,
    "innodisk": InnodiskFetcher,
    "tsmc": TSMCFetcher,
    "intel": IntelFetcher,
    "psmc": PSMCFetcher,
    # 中游 - 封測
    "ase": ASEFetcher,
    "powertech": PowertechFetcher,
    "ptc": ChipMOSFetcher,
    "amkor": AmkorFetcher,
    # 下游 - GPU/晶片
    "nvidia": NVIDIAFetcher,
    "amd": AMDFetcher,
    "broadcom": BroadcomFetcher,
    "qualcomm": QualcommFetcher,
    "marvell": MarvellFetcher,
    "ti": TIFetcher,
    "onsemi": OnsemiFetcher,
    "infineon": InfineonFetcher,
    # 下游 - 系統/CSP
    "apple": AppleFetcher,
    "dell": DellFetcher,
    "hp": HPFetcher,
    "lenovo": LenovoFetcher,
    "supermicro": SupermicroFetcher,
    "aws": AWSFetcher,
    "microsoft": MicrosoftFetcher,
    "google": GoogleCloudFetcher,
    "meta": MetaFetcher,
    "oracle": OracleFetcher,
}
