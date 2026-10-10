from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..explainer import DISCLAIMER, explain, sanitize
from ..models import User
from ..schemas import ExplainIn, ExplainOut

router = APIRouter(prefix="/explain", tags=["error explanation"])


@router.post("", response_model=ExplainOut)
def explain_error(data: ExplainIn, user: User = Depends(get_current_user)):
    # We do not store the log. We clean it, explain it, and return it.
    clean = sanitize(data.log)
    return ExplainOut(sanitized_log=clean, results=explain(clean), disclaimer=DISCLAIMER)
