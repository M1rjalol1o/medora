import re
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.i18n import msg
from apps.catalog.models import Medicine

from .models import FamilyMember, IntakeLog, MedicationCourse, Prescription, PrescriptionItem
from .ocr import read_prescription
from .parser import _catalog, _find_medicine, default_times, parse

S = extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def item_dict(i):
    return {"id": i.id, "medicine_id": i.medicine_id, "name": i.name, "dose": i.dose,
            "times_per_day": i.times_per_day, "duration_days": i.duration_days, "note": i.note,
            "confidence": i.confidence,
            "medicine": {"id": i.medicine.id, "name": i.medicine.name, "dosage": i.medicine.dosage,
                         "requires_prescription": i.medicine.requires_prescription}
            if i.medicine_id else None}


def rx_dict(request, p):
    return {"id": p.id, "status": p.status, "raw_text": p.raw_text, "ocr_engine": p.ocr_engine,
            "image": request.build_absolute_uri(p.image.url) if p.image else None,
            "created_at": p.created_at, "items": [item_dict(i) for i in p.items.select_related("medicine")],
            "ocr_errors": getattr(p, "_ocr_errors", [])}


def _fill_items(p, ai_items=None):
    """ai_items — Vision AI ajratgan dorilar; bo'lmasa matn parser bilan tahlil qilinadi."""
    from apps.catalog.utils import normalize
    p.items.all().delete()
    if ai_items is not None:
        catalog = _catalog()
        rows = []
        for it in ai_items:
            med = _find_medicine(normalize(it["name"]), catalog)
            rows.append({**it, "medicine_id": med.id if med else None,
                         "name": med.name if med else it["name"],
                         "dose": it["dose"] or (med.dosage if med else "")})
    else:
        rows = parse(p.raw_text)
    for r in rows:
        PrescriptionItem.objects.create(
            prescription=p, medicine_id=r["medicine_id"], name=r["name"], dose=r["dose"],
            times_per_day=r["times_per_day"], duration_days=r["duration_days"], note=r["note"],
            confidence=r["confidence"])
    p.status = Prescription.Status.PARSED
    p.save(update_fields=["status"])


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def prescriptions(request):
    """POST multipart {image} yoki {text} — rasm OCR qilinadi va tahlil qilinadi."""
    if request.method == "GET":
        return Response([rx_dict(request, p) for p in request.user.prescriptions.prefetch_related("items")[:20]])
    image = request.FILES.get("image")
    text = (request.data.get("text") or "").strip()
    if not image and not text:
        return Response({"detail": msg(request, "image_required")}, status=400)
    p = Prescription.objects.create(user=request.user, image=image)
    ai_items = None
    if not text and image:
        p.image.open("rb")
        r = read_prescription(p.image)
        text, p.ocr_engine, ai_items = r["text"], r["engine"], r["items"]
        p._ocr_errors = r["errors"]
    else:
        p.ocr_engine = "manual"
    p.raw_text = text
    p.save()
    _fill_items(p, ai_items)
    return Response(rx_dict(request, p), status=201)


@S
@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def prescription_detail(request, pk):
    """PATCH {text} — matnni tahrirlab qayta tahlil qilish."""
    p = get_object_or_404(Prescription, pk=pk, user=request.user)
    if request.method == "PATCH" and "text" in request.data:
        p.raw_text = request.data["text"]
        p.save(update_fields=["raw_text"])
        _fill_items(p)
    return Response(rx_dict(request, p))


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def prescription_confirm(request, pk):
    """{items:[{name, dose, times:[..], duration_days, note, medicine_id}]} -> dori qabul qilish jadvali"""
    p = get_object_or_404(Prescription, pk=pk, user=request.user)
    created = []
    today = timezone.localdate()
    for it in request.data.get("items", []):
        times = [t for t in it.get("times") or [] if TIME_RE.match(str(t))] or \
            default_times(int(it.get("times_per_day") or 1))
        days = max(1, min(int(it.get("duration_days") or 5), 365))
        c = MedicationCourse.objects.create(
            user=request.user, medicine_name=str(it.get("name", ""))[:200], dose=str(it.get("dose", ""))[:60],
            times=sorted(set(times)), start_date=today, end_date=today + timedelta(days=days - 1),
            note=str(it.get("note", ""))[:200], member=_member_or_none(request, request.data.get("member")))
        created.append(course_dict(c))
    p.status = Prescription.Status.CONFIRMED
    p.save(update_fields=["status"])
    return Response(created, status=201)


def course_dict(c, today_logs=None):
    today = timezone.localdate()
    return {"id": c.id, "medicine_name": c.medicine_name, "dose": c.dose, "times": c.times,
            "start_date": c.start_date, "end_date": c.end_date, "note": c.note, "is_active": c.is_active,
            "member": c.member_id, "days_left": (c.end_date - today).days + 1,
            "taken_today": today_logs if today_logs is not None else []}


def member_dict(m):
    return {"id": m.id, "name": m.name, "relation": m.relation, "color": m.color}


def adherence(courses, days=7):
    """Oxirgi `days` kunda (bugungacha) rejalashtirilgan qabullarning necha foizi ichilgan."""
    today = timezone.localdate() - timedelta(days=1)
    planned = taken = 0
    for c in courses:
        start = max(c.start_date, today - timedelta(days=days - 1))
        end = min(c.end_date, today)
        n_days = (end - start).days + 1
        if n_days <= 0:
            continue
        planned += n_days * len(c.times)
        taken += c.logs.filter(date__gte=start, date__lte=end, status="taken").count()
    return {"planned": planned, "taken": taken, "percent": round(taken * 100 / planned) if planned else None}


def _member_or_none(request, value):
    if value in (None, "", "me", 0, "0"):
        return None
    return get_object_or_404(FamilyMember, pk=value, user=request.user)


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def family(request):
    """Oila a'zolari. POST {name, relation, color}"""
    if request.method == "POST":
        name = str(request.data.get("name", "")).strip()[:60]
        if not name:
            return Response({"detail": msg(request, "bad_value", f="name")}, status=400)
        m = FamilyMember.objects.create(user=request.user, name=name,
                                        relation=str(request.data.get("relation", ""))[:30],
                                        color=str(request.data.get("color") or "#FF8A65")[:9])
        return Response(member_dict(m), status=201)
    return Response([member_dict(m) for m in request.user.family.all()])


@S
@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def family_detail(request, pk):
    get_object_or_404(FamilyMember, pk=pk, user=request.user).delete()
    return Response(status=204)


@S
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def health_stats(request):
    """Har bir a'zo uchun 7 kunlik intizom foizi + tugayotgan kurslar (qayta buyurtma taklifi)."""
    today = timezone.localdate()
    active = request.user.courses.filter(is_active=True, end_date__gte=today).prefetch_related("logs")
    people = [{"id": None, "name": request.user.first_name or request.user.username, "relation": "me",
               "color": "#0FB389"}] + [member_dict(m) for m in request.user.family.all()]
    for p in people:
        mine = [c for c in active if c.member_id == p["id"]]
        p["active_courses"] = len(mine)
        p["adherence"] = adherence(mine)
    ending = [course_dict(c) for c in active if (c.end_date - today).days <= 1]
    return Response({"people": people, "ending_soon": ending, "adherence": adherence(list(active))})


@S
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def courses(request):
    """GET — faol jadvallar (bugun ichilganlari bilan). POST — qo'lda qo'shish."""
    if request.method == "POST":
        d = request.data
        times = [t for t in d.get("times") or [] if TIME_RE.match(str(t))]
        if not d.get("medicine_name") or not times:
            return Response({"detail": msg(request, "bad_value", f="medicine_name/times")}, status=400)
        today = timezone.localdate()
        days = max(1, min(int(d.get("duration_days") or 7), 365))
        c = MedicationCourse.objects.create(user=request.user, medicine_name=d["medicine_name"][:200],
                                            dose=str(d.get("dose", ""))[:60], times=sorted(set(times)),
                                            start_date=today, end_date=today + timedelta(days=days - 1),
                                            note=str(d.get("note", ""))[:200],
                                            member=_member_or_none(request, d.get("member")))
        return Response(course_dict(c), status=201)
    today = timezone.localdate()
    qs = request.user.courses.filter(is_active=True, end_date__gte=today)
    if "member" in request.GET:
        m = request.GET["member"]
        qs = qs.filter(member__isnull=True) if m in ("", "me", "0") else qs.filter(member_id=m)
    logs = {}
    for l in IntakeLog.objects.filter(course__in=qs, date=today):
        logs.setdefault(l.course_id, []).append({"time": l.time, "status": l.status})
    return Response([course_dict(c, logs.get(c.id, [])) for c in qs])


@S
@api_view(["PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def course_detail(request, pk):
    c = get_object_or_404(MedicationCourse, pk=pk, user=request.user)
    if request.method == "DELETE":
        c.is_active = False
        c.save(update_fields=["is_active"])
        return Response(status=204)
    times = request.data.get("times")
    if times is not None:
        times = [t for t in times if TIME_RE.match(str(t))]
        if times:
            c.times = sorted(set(times))
    for f in ("dose", "note", "medicine_name"):
        if f in request.data:
            setattr(c, f, str(request.data[f])[:200])
    c.save()
    return Response(course_dict(c))


@S
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def course_log(request, pk):
    """{time:"08:00", status:"taken"|"skipped"} — bugungi qabul belgilanadi."""
    c = get_object_or_404(MedicationCourse, pk=pk, user=request.user)
    t = str(request.data.get("time", ""))
    if not TIME_RE.match(t):
        return Response({"detail": msg(request, "bad_value", f="time")}, status=400)
    IntakeLog.objects.update_or_create(course=c, date=timezone.localdate(), time=t,
                                       defaults={"status": request.data.get("status", "taken")})
    return Response({"ok": True})


@S
@api_view(["GET"])
def medicine_lookup(request, pk):
    m = get_object_or_404(Medicine, pk=pk)
    return Response({"id": m.id, "name": m.name, "dosage": m.dosage})
