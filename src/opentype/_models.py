from __future__ import annotations

from typing import Optional

import pydantic
from pydantic import ConfigDict, PrivateAttr


class BaseModel(pydantic.BaseModel):
    """Base of every response model. Unknown fields are kept, so a newer server
    never breaks an older SDK, and the request id travels with the object."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    _request_id: Optional[str] = PrivateAttr(default=None)
