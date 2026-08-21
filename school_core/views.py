
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.http import JsonResponse
from .models import (
    Subject,
    GradeAssessment,
    GradeComponent,
    Student,
    StudentGrade,
    Teacher,
    TeachingAssignment,
)


@login_required
def grade_entry(request):

    # ==========================================
    # القوائم الأساسية
    # ==========================================

    subjects = (
        Subject.objects
        .filter(is_active=True)
        .order_by("name")
    )

    assessments = (
        GradeAssessment.objects
        .filter(is_active=True)
        .select_related("subject")
        .order_by(
            "subject",
            "order",
            "id",
        )
    )

    components = (
        GradeComponent.objects
        .filter(is_active=True)
        .select_related(
            "assessment",
            "assessment__subject",
        )
        .order_by(
            "assessment",
            "order",
            "id",
        )
    )

    # ==========================================
    # القيم المختارة
    # ==========================================

    selected_subject = (
        request.POST.get("subject")
        or request.GET.get("subject")
        or ""
    )

    selected_assessment = (
        request.POST.get("assessment")
        or request.GET.get("assessment")
        or ""
    )

    selected_component = (
        request.POST.get("component")
        or request.GET.get("component")
        or ""
    )

    # ==========================================
    # القيم الافتراضية
    # ==========================================

    students = Student.objects.none()

    selected_max_score = None

    selected_component_obj = None

    assessment_max_score = None

    existing_grades = {}

    student_totals = {}

    # ==========================================
    # بيانات المدرس
    # ==========================================

    try:

        teacher = Teacher.objects.get(
            user=request.user,
            is_active=True,
        )

    except Teacher.DoesNotExist:

        messages.error(
            request,
            "حساب المستخدم الحالي غير مرتبط بمدرس نشط.",
        )

        context = {
            "subjects": subjects,
            "assessments": assessments,
            "components": components,
            "students": students,
            "selected_subject": selected_subject,
            "selected_assessment": selected_assessment,
            "selected_component": selected_component,
            "selected_max_score": selected_max_score,
            "selected_component_obj": selected_component_obj,
            "assessment_max_score": assessment_max_score,
        }

        return render(
            request,
            "school_core/grade_entry.html",
            context,
        )

    # ==========================================
    # تحديد التقييم والمكوّن والطلاب
    # ==========================================

    if (
        selected_subject
        and selected_assessment
        and selected_component
    ):

        try:

            assessment = (
                GradeAssessment.objects
                .select_related("subject")
                .get(
                    id=selected_assessment,
                    subject_id=selected_subject,
                    is_active=True,
                )
            )

            component = (
                GradeComponent.objects
                .select_related(
                    "assessment",
                    "assessment__subject",
                )
                .get(
                    id=selected_component,
                    assessment=assessment,
                    is_active=True,
                )
            )

            selected_component_obj = component

            selected_max_score = component.max_score

            # ----------------------------------
            # شعب المدرس في المادة
            # ----------------------------------

            section_ids = (
                TeachingAssignment.objects
                .filter(
                    teacher=teacher,
                    subject=assessment.subject,
                    is_active=True,
                )
                .values_list(
                    "section_id",
                    flat=True,
                )
                .distinct()
            )

            # ----------------------------------
            # الطلاب
            # ----------------------------------

            students = (
                Student.objects
                .filter(
                    section_id__in=section_ids,
                    school=assessment.subject.school,
                    is_active=True,
                )
                .select_related(
                    "school",
                    "classroom",
                    "section",
                )
                .order_by(
                    "last_name",
                    "first_name",
                    "middle_name",
                )
            )

        except (
            GradeAssessment.DoesNotExist,
            GradeComponent.DoesNotExist,
        ):

            messages.error(
                request,
                "التقييم أو المكوّن المحدد غير صحيح.",
            )

            students = Student.objects.none()

    # ==========================================
    # حفظ الدرجات
    # ==========================================

    if request.method == "POST":

        if not (
            selected_subject
            and selected_assessment
            and selected_component
        ):

            messages.error(
                request,
                "يرجى اختيار المادة والتقييم والمكوّن.",
            )

            return redirect(
                "school_core:grade_entry"
            )

        try:

            # ----------------------------------
            # الحصول على التقييم
            # ----------------------------------

            assessment = (
                GradeAssessment.objects
                .select_related("subject")
                .get(
                    id=selected_assessment,
                    subject_id=selected_subject,
                    is_active=True,
                )
            )

            # ----------------------------------
            # الحصول على المكوّن
            # ----------------------------------

            component = (
                GradeComponent.objects
                .select_related(
                    "assessment",
                    "assessment__subject",
                )
                .get(
                    id=selected_component,
                    assessment=assessment,
                    is_active=True,
                )
            )

            # ----------------------------------
            # منع التعديل على التقييم المعتمد
            # ----------------------------------

            if (
                assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):

                messages.error(
                    request,
                    "لا يمكن تعديل درجات ضمن تقييم معتمد.",
                )

                return redirect(
                    (
                        f"/grades/entry/"
                        f"?subject={selected_subject}"
                        f"&assessment={selected_assessment}"
                        f"&component={selected_component}"
                    )
                )

            # ----------------------------------
            # شعب المدرس
            # ----------------------------------

            section_ids = (
                TeachingAssignment.objects
                .filter(
                    teacher=teacher,
                    subject=assessment.subject,
                    is_active=True,
                )
                .values_list(
                    "section_id",
                    flat=True,
                )
                .distinct()
            )

            # ----------------------------------
            # الطلاب المسموح لهم
            # ----------------------------------

            allowed_students = (
                Student.objects
                .filter(
                    section_id__in=section_ids,
                    school=assessment.subject.school,
                    is_active=True,
                )
            )

            allowed_student_ids = set(
                allowed_students.values_list(
                    "id",
                    flat=True,
                )
            )

            saved_count = 0

            # ==================================
            # حفظ الدرجات
            # ==================================

            with transaction.atomic():

                for student_id in allowed_student_ids:

                    field_name = (
                        f"score_{student_id}"
                    )

                    raw_score = request.POST.get(
                        field_name
                    )

                    # الخانة فارغة
                    if raw_score is None:
                        continue

                    raw_score = raw_score.strip()

                    if raw_score == "":
                        continue

                    # --------------------------------
                    # تحويل الدرجة إلى Decimal
                    # --------------------------------

                    try:

                        score = Decimal(
                            raw_score
                        )

                    except InvalidOperation:

                        raise ValueError(
                            "درجة غير صحيحة."
                        )

                    # --------------------------------
                    # منع الدرجة السالبة
                    # --------------------------------

                    if score < Decimal("0"):

                        raise ValueError(
                            "لا يمكن إدخال درجة أقل من صفر."
                        )

                    # --------------------------------
                    # منع تجاوز الدرجة العظمى
                    # --------------------------------

                    if score > component.max_score:

                        raise ValueError(
                            (
                                "إحدى الدرجات تتجاوز "
                                "الدرجة العظمى للمكوّن."
                            )
                        )

                    # --------------------------------
                    # الحفظ أو التحديث
                    # --------------------------------

                    StudentGrade.objects.update_or_create(
                        student_id=student_id,
                        component=component,
                        defaults={
                            "score": score,
                        },
                    )

                    saved_count += 1

            messages.success(
                request,
                f"تم حفظ {saved_count} درجة بنجاح.",
            )

        except ValueError as error:

            messages.error(
                request,
                str(error),
            )

        except (
            GradeAssessment.DoesNotExist,
            GradeComponent.DoesNotExist,
        ):

            messages.error(
                request,
                "تعذر العثور على التقييم أو المكوّن.",
            )

        return redirect(
            (
                f"/grades/entry/"
                f"?subject={selected_subject}"
                f"&assessment={selected_assessment}"
                f"&component={selected_component}"
            )
        )

    # ==========================================
    # حساب مجموع درجات التقييم
    # ==========================================

    if selected_component_obj:

        # --------------------------------------
        # مكونات التقييم
        # --------------------------------------

        assessment_components = (
            GradeComponent.objects
            .filter(
                assessment=selected_component_obj.assessment,
                is_active=True,
            )
            .order_by(
                "order",
                "id",
            )
        )

        # --------------------------------------
        # الدرجة العظمى للتقييم
        # --------------------------------------

        assessment_max_score = sum(
            (
                component_item.max_score
                for component_item
                in assessment_components
            ),
            Decimal("0"),
        )

        # --------------------------------------
        # درجات جميع مكونات التقييم
        # --------------------------------------

        grades = (
            StudentGrade.objects
            .filter(
                component__assessment=(
                    selected_component_obj.assessment
                ),
                component__is_active=True,
                student__in=students,
            )
            .values(
                "student_id",
                "component_id",
                "score",
            )
        )

        # --------------------------------------
        # الدرجة الخاصة بالمكوّن المحدد
        # --------------------------------------

        for item in grades:

            if (
                item["component_id"]
                == selected_component_obj.id
            ):

                existing_grades[
                    item["student_id"]
                ] = item["score"]

        # --------------------------------------
        # حساب مجموع الطالب
        # --------------------------------------

        for item in grades:

            student_id = item["student_id"]

            score = (
                item["score"]
                or Decimal("0")
            )

            student_totals.setdefault(
                student_id,
                Decimal("0"),
            )

            student_totals[student_id] += score

        # --------------------------------------
        # إضافة البيانات للطلاب
        # --------------------------------------

        for student in students:

            student.existing_grade = (
                existing_grades.get(
                    student.id
                )
            )

            student.total_grade = (
                student_totals.get(
                    student.id,
                    Decimal("0"),
                )
            )

    # ==========================================
    # Context
    # ==========================================

    context = {

        "subjects": subjects,

        "assessments": assessments,

        "components": components,

        "students": students,

        "selected_subject": selected_subject,

        "selected_assessment": selected_assessment,

        "selected_component": selected_component,

        "selected_max_score": selected_max_score,

        "selected_component_obj": selected_component_obj,

        "assessment_max_score": assessment_max_score,

    }

    # ==========================================
    # عرض الصفحة
    # ==========================================

    return render(
        request,
        "school_core/grade_entry.html",
        context,
    )
@login_required
def auto_save_grade(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "طريقة الطلب غير صحيحة.",
            },
            status=405,
        )

    try:

        student_id = request.POST.get("student_id")
        component_id = request.POST.get("component_id")
        raw_score = request.POST.get("score")

        if not student_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "لم يتم تحديد الطالب.",
                },
                status=400,
            )

        if not component_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "لم يتم تحديد المكوّن.",
                },
                status=400,
            )

        if raw_score is None or raw_score.strip() == "":
            return JsonResponse(
                {
                    "success": False,
                    "message": "الدرجة فارغة.",
                },
                status=400,
            )

        try:

            score = Decimal(
                raw_score.strip()
            )

        except InvalidOperation:

            return JsonResponse(
                {
                    "success": False,
                    "message": "الدرجة غير صحيحة.",
                },
                status=400,
            )

        if score < Decimal("0"):

            return JsonResponse(
                {
                    "success": False,
                    "message": "لا يمكن إدخال درجة سالبة.",
                },
                status=400,
            )

        component = (
            GradeComponent.objects
            .select_related(
                "assessment",
                "assessment__subject",
            )
            .get(
                id=component_id,
                is_active=True,
            )
        )

        if score > component.max_score:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"الدرجة يجب ألا تتجاوز "
                        f"{component.max_score}."
                    ),
                },
                status=400,
            )

        assessment = component.assessment

        if (
            assessment.status
            == GradeAssessment.STATUS_APPROVED
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": "هذا التقييم معتمد ولا يمكن تعديله.",
                },
                status=400,
            )

        student = (
            Student.objects
            .filter(
                id=student_id,
                is_active=True,
            )
            .first()
        )

        if not student:

            return JsonResponse(
                {
                    "success": False,
                    "message": "الطالب غير موجود.",
                },
                status=404,
            )

        grade, created = (
            StudentGrade.objects
            .update_or_create(
                student=student,
                component=component,
                defaults={
                    "score": score,
                },
            )
        )

        return JsonResponse(
            {
                "success": True,
                "message": "تم الحفظ.",
                "score": str(grade.score),
                "student_id": student.id,
                "component_id": component.id,
            }
        )

    except GradeComponent.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "المكوّن غير موجود.",
            },
            status=404,
        )

    except Exception as error:

        return JsonResponse(
            {
                "success": False,
                "message": str(error),
            },
            status=500,
        )
def approve_assessment(request):

    if request.method != "POST":
        return redirect("school_core:grade_entry")

    selected_subject = request.POST.get("subject")
    selected_assessment = request.POST.get("assessment")
    selected_component = request.POST.get("component")

    try:

        teacher = Teacher.objects.get(
            user=request.user,
            is_active=True,
        )

        assessment = GradeAssessment.objects.get(
            id=selected_assessment,
            subject_id=selected_subject,
            is_active=True,
        )

        # التأكد أن المدرس يدرّس هذه المادة
        assignment_exists = TeachingAssignment.objects.filter(
            teacher=teacher,
            subject=assessment.subject,
            is_active=True,
        ).exists()

        if not assignment_exists:

            messages.error(
                request,
                "ليس لديك صلاحية اعتماد هذا التقييم.",
            )

            return redirect(
                (
                    f"/grades/entry/"
                    f"?subject={selected_subject}"
                    f"&assessment={selected_assessment}"
                    f"&component={selected_component}"
                )
            )

        # اعتماد التقييم
        assessment.status = GradeAssessment.STATUS_APPROVED
        assessment.save(update_fields=["status"])

        messages.success(
            request,
            "تم اعتماد التقييم بنجاح، ولا يمكن تعديل درجاته بعد الآن.",
        )

    except Teacher.DoesNotExist:

        messages.error(
            request,
            "حساب المدرس غير مرتبط بمدرس فعال.",
        )

    except GradeAssessment.DoesNotExist:

        messages.error(
            request,
            "التقييم غير موجود أو غير صالح.",
        )

    return redirect(
        (
            f"/grades/entry/"
            f"?subject={selected_subject}"
            f"&assessment={selected_assessment}"
            f"&component={selected_component}"
        )
    )
