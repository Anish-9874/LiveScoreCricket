import hmac
import json
import re

from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import MatchState

IMG_KEY = re.compile(r"^(L[01]|P[01]_\d{1,2})$")  # L0/L1 = logos, P0_3 = team 0, player 3
MAX_IMG_CHARS = 600_000


def index(request, mode="control"):
    """mode='control' -> scoring buttons + board.  mode='display' -> board only."""
    return render(request, "index.html", {"mode": mode})


def _pin_ok(request):
    pin = settings.CONTROL_PIN
    if not pin:
        return True  # no PIN configured (fine for local testing only)
    sent = request.headers.get("X-Control-Pin", "")
    return hmac.compare_digest(sent.encode(), pin.encode())


def _json_body(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else None
    except ValueError:
        return None


@csrf_exempt  # protected by the control PIN header instead of a CSRF cookie
@require_http_methods(["GET", "POST"])
def state_api(request):
    if request.method == "POST":
        if not _pin_ok(request):
            return JsonResponse({"error": "bad pin"}, status=403)
        data = _json_body(request)
        if data is None or not isinstance(data.get("state"), dict):
            return JsonResponse({"error": "bad request"}, status=400)
        MatchState.objects.get_or_create(pk=1)
        MatchState.objects.filter(pk=1).update(
            state=data["state"],
            version=F("version") + 1,
            by=str(data.get("client", ""))[:40],
            state_at=timezone.now(),
        )
        v = MatchState.objects.values_list("version", flat=True).get(pk=1)
        return JsonResponse({"v": v})

    # GET: tiny reply unless something changed since the version the client has
    def _int(name):
        try:
            return int(request.GET.get(name, -1))
        except ValueError:
            return -1

    have_v, have_iv, me = _int("v"), _int("iv"), request.GET.get("c", "")
    row = MatchState.objects.defer("state", "images").filter(pk=1).first()
    out = {"v": 0, "iv": 0, "pin_required": bool(settings.CONTROL_PIN)}
    if row is None:  # nothing saved yet
        if have_v != 0:
            out["state"] = None
        return JsonResponse(out)
    out["v"], out["iv"] = row.version, row.img_version
    if have_v != row.version:
        if row.by and row.by == me:
            out["mine"] = True  # my own write: no need to send it back
        else:
            out["state"] = row.state
            out["age"] = (timezone.now() - row.state_at).total_seconds() if row.state_at else 999
    if have_iv != row.img_version:
        out["images"] = row.images
    return JsonResponse(out)


@csrf_exempt
@require_http_methods(["POST"])
def images_api(request):
    if not _pin_ok(request):
        return JsonResponse({"error": "bad pin"}, status=403)
    data = _json_body(request)
    new = data.get("set") if data else None
    if not isinstance(new, dict):
        return JsonResponse({"error": "bad request"}, status=400)
    clean = {
        k: v for k, v in new.items()
        if IMG_KEY.match(k) and isinstance(v, str)
        and v.startswith("data:image/") and len(v) <= MAX_IMG_CHARS
    }
    if not clean:
        return JsonResponse({"error": "no valid images"}, status=400)
    row, _ = MatchState.objects.get_or_create(pk=1)
    imgs = dict(row.images or {})
    imgs.update(clean)
    row.images = imgs
    row.img_version += 1
    row.save(update_fields=["images", "img_version"])  # never touches the score fields
    return JsonResponse({"iv": row.img_version})
