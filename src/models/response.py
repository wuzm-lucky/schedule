from pydantic import BaseModel
from typing import List, Optional

class CommonResponse(BaseModel):
    """通用响应"""
    code: Optional[str] = 'success'
    message: Optional[str] = '成功'
    data: Optional[object] = None