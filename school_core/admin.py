
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    School,
    ClassRoom,
    Section,
    Subject,
    Teacher,
    TeachingAssignment,
    Student,
    GradeAssessment,
    GradeComponent,
    StudentGrade,
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "phone",
        "email",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "phone",
    )

    list_filter = (
        "is_active",
    )


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "school",
        "level",
        "is_active",
    )

    search_fields = (
        "name",
        "school__name",
    )

    list_filter = (
        "school",
        "level",
        "is_active",
    )


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "classroom",
        "capacity",
        "is_active",
    )

    search_fields = (
        "name",
        "classroom__name",
        "classroom__school__name",
    )

    list_filter = (
        "classroom",
        "is_active",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "school",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "school__name",
    )

    list_filter = (
        "school",
        "is_active",
    )


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "school",
        "employee_code",
        "specialization",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "employee_code",
        "specialization",
        "school__name",
    )

    list_filter = (
        "school",
        "is_active",
    )


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "subject",
        "section",
        "is_active",
        "created_at",
    )

    search_fields = (
        "teacher__user__username",
        "teacher__user__first_name",
        "teacher__user__last_name",
        "subject__name",
        "section__name",
    )

    list_filter = (
        "teacher",
        "subject",
        "section",
        "is_active",
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_code",
        "first_name",
        "middle_name",
        "last_name",
        "school",
        "classroom",
        "section",
        "is_active",
    )

    search_fields = (
        "student_code",
        "first_name",
        "middle_name",
        "last_name",
        "school__name",
        "classroom__name",
        "section__name",
    )

    list_filter = (
        "school",
        "classroom",
        "section",
        "is_active",
    )


@admin.register(GradeAssessment)
class GradeAssessmentAdmin(admin.ModelAdmin):

    list_display = (
        "subject",
        "name",
        "max_score",
        "status_display",
        "components_total",
        "order",
        "is_active",
        "created_at",
    )

    search_fields = (
        "subject__name",
        "name",
    )

    list_filter = (
        "subject",
        "status",
        "is_active",
    )

    ordering = (
        "subject",
        "order",
        "id",
    )

    readonly_fields = (
        "components_total",
        "status",
        "assessment_action",
    )

    actions = (
        "approve_assessments",
        "unapprove_assessments",
    )

    def components_total(self, obj):
        if not obj or not obj.pk:
            return 0

        total = (
            obj.components
            .filter(is_active=True)
            .aggregate(total=Sum("max_score"))
            .get("total")
        )

        return total or 0

    components_total.short_description = "مجموع المكونات"

    def status_display(self, obj):
        if obj.status == GradeAssessment.STATUS_APPROVED:
            return "معتمد"

        return "مسودة"

    status_display.short_description = "الحالة"

    def assessment_action(self, obj):
        if not obj or not obj.pk:
            return "بعد حفظ التقييم ستظهر هنا إجراءات الاعتماد."

        if obj.status == GradeAssessment.STATUS_APPROVED:

            url = reverse(
                "admin:school_core_gradeassessment_unapprove",
                args=[obj.pk],
            )

            return format_html(
                '<a class="button" href="{}" '
                'style="background:#ba2121; color:white; '
                'padding:10px 18px; border-radius:5px; '
                'text-decoration:none;">'
                'إلغاء اعتماد التقييم'
                '</a>',
                url,
            )

        url = reverse(
            "admin:school_core_gradeassessment_approve",
            args=[obj.pk],
        )

        return format_html(
            '<a class="button" href="{}" '
            'style="background:#417690; color:white; '
            'padding:10px 18px; border-radius:5px; '
            'text-decoration:none;">'
            'اعتماد التقييم'
            '</a>',
            url,
        )

    assessment_action.short_description = "إجراء التقييم"

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:assessment_id>/approve/",
                self.admin_site.admin_view(
                    self.approve_single_assessment
                ),
                name="school_core_gradeassessment_approve",
            ),
            path(
                "<int:assessment_id>/unapprove/",
                self.admin_site.admin_view(
                    self.unapprove_single_assessment
                ),
                name="school_core_gradeassessment_unapprove",
            ),
        ]

        return custom_urls + urls

    def approve_single_assessment(
        self,
        request,
        assessment_id,
    ):
        try:
            assessment = GradeAssessment.objects.get(
                pk=assessment_id
            )
        except GradeAssessment.DoesNotExist:
            self.message_user(
                request,
                "التقييم غير موجود.",
                level=messages.ERROR,
            )

            return HttpResponseRedirect(
                reverse(
                    "admin:school_core_gradeassessment_changelist"
                )
            )

        total = (
            assessment.components
            .filter(is_active=True)
            .aggregate(total=Sum("max_score"))
            .get("total")
        )

        total = total or 0

        if total != assessment.max_score:
            self.message_user(
                request,
                (
                    f"لا يمكن اعتماد «{assessment}». "
                    f"مجموع المكونات = {total}، "
                    f"والدرجة العظمى = {assessment.max_score}. "
                    "يجب أن يتساويا تمامًا."
                ),
                level=messages.ERROR,
            )

            return HttpResponseRedirect(
                reverse(
                    "admin:school_core_gradeassessment_change",
                    args=[assessment.id],
                )
            )

        assessment.status = GradeAssessment.STATUS_APPROVED

        assessment.save(
            update_fields=["status"]
        )

        self.message_user(
            request,
            "تم اعتماد التقييم بنجاح.",
            level=messages.SUCCESS,
        )

        return HttpResponseRedirect(
            reverse(
                "admin:school_core_gradeassessment_change",
                args=[assessment.id],
            )
        )

    def unapprove_single_assessment(
        self,
        request,
        assessment_id,
    ):
        try:
            assessment = GradeAssessment.objects.get(
                pk=assessment_id
            )
        except GradeAssessment.DoesNotExist:
            self.message_user(
                request,
                "التقييم غير موجود.",
                level=messages.ERROR,
            )

            return HttpResponseRedirect(
                reverse(
                    "admin:school_core_gradeassessment_changelist"
                )
            )

        assessment.status = GradeAssessment.STATUS_DRAFT

        assessment.save(
            update_fields=["status"]
        )

        self.message_user(
            request,
            "تم إلغاء اعتماد التقييم بنجاح.",
            level=messages.SUCCESS,
        )

        return HttpResponseRedirect(
            reverse(
                "admin:school_core_gradeassessment_change",
                args=[assessment.id],
            )
        )

    @admin.action(description="اعتماد التقييمات المحددة")
    def approve_assessments(
        self,
        request,
        queryset,
    ):
        approved_count = 0

        for assessment in queryset:

            total = (
                assessment.components
                .filter(is_active=True)
                .aggregate(total=Sum("max_score"))
                .get("total")
            )

            total = total or 0

            if total != assessment.max_score:

                self.message_user(
                    request,
                    (
                        f"لا يمكن اعتماد «{assessment}». "
                        f"المجموع = {total}، "
                        f"الدرجة العظمى = "
                        f"{assessment.max_score}. "
                        "يجب أن يتساويا تمامًا."
                    ),
                    level=messages.ERROR,
                )

                continue

            assessment.status = (
                GradeAssessment.STATUS_APPROVED
            )

            assessment.save(
                update_fields=["status"]
            )

            approved_count += 1

        if approved_count:
            self.message_user(
                request,
                (
                    f"تم اعتماد {approved_count} "
                    "تقييم بنجاح."
                ),
                level=messages.SUCCESS,
            )

    @admin.action(description="إلغاء اعتماد التقييمات المحددة")
    def unapprove_assessments(
        self,
        request,
        queryset,
    ):
        count = queryset.filter(
            status=GradeAssessment.STATUS_APPROVED
        ).update(
            status=GradeAssessment.STATUS_DRAFT
        )

        if count:
            self.message_user(
                request,
                (
                    f"تم إلغاء اعتماد {count} "
                    "تقييم."
                ),
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "لا توجد تقييمات معتمدة ضمن التحديد.",
                level=messages.WARNING,
            )


@admin.register(GradeComponent)
class GradeComponentAdmin(admin.ModelAdmin):

    list_display = (
        "assessment",
        "name",
        "max_score",
        "order",
        "is_active",
        "created_at",
    )

    search_fields = (
        "assessment__subject__name",
        "assessment__name",
        "name",
    )

    list_filter = (
        "assessment",
        "is_active",
    )

    ordering = (
        "assessment",
        "order",
        "id",
    )

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        readonly = []

        if obj and obj.assessment:

            if (
                obj.assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):
                readonly = [
                    "assessment",
                    "name",
                    "max_score",
                    "order",
                    "is_active",
                ]

        return readonly

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if obj.assessment:

            if (
                obj.assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):
                raise ValidationError(
                    (
                        "لا يمكن تعديل مكوّن لتقييم "
                        "معتمد. قم بإلغاء اعتماد "
                        "التقييم أولًا."
                    )
                )

        obj.full_clean()

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def delete_model(
        self,
        request,
        obj,
    ):
        if obj.assessment:

            if (
                obj.assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):
                self.message_user(
                    request,
                    (
                        "لا يمكن حذف مكوّن من تقييم "
                        "معتمد. قم بإلغاء اعتماد "
                        "التقييم أولًا."
                    ),
                    level=messages.ERROR,
                )

                return

        super().delete_model(
            request,
            obj,
        )

    def delete_queryset(
        self,
        request,
        queryset,
    ):
        blocked = queryset.filter(
            assessment__status=(
                GradeAssessment.STATUS_APPROVED
            )
        ).exists()

        if blocked:
            self.message_user(
                request,
                (
                    "لا يمكن حذف مكونات مرتبطة "
                    "بتقييمات معتمدة. قم بإلغاء "
                    "الاعتماد أولًا."
                ),
                level=messages.ERROR,
            )

            return

        super().delete_queryset(
            request,
            queryset,
        )


@admin.register(StudentGrade)
class StudentGradeAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "student_code",
        "subject",
        "assessment",
        "component",
        "score",
        "max_score",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "student__student_code",
        "student__first_name",
        "student__middle_name",
        "student__last_name",
        "component__name",
        "component__assessment__name",
        "component__assessment__subject__name",
    )

    list_filter = (
        "component__assessment__subject",
        "component__assessment",
        "component",
    )

    ordering = (
        "student",
        "component",
    )

    def student_code(self, obj):
        return obj.student.student_code

    student_code.short_description = "رمز الطالب"

    def subject(self, obj):
        return obj.component.assessment.subject

    subject.short_description = "المادة"

    def assessment(self, obj):
        return obj.component.assessment

    assessment.short_description = "التقييم"

    def max_score(self, obj):
        return obj.component.max_score

    max_score.short_description = "الدرجة العظمى"

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        obj.full_clean()

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        if obj and obj.component:

            assessment = obj.component.assessment

            if (
                assessment
                and assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):
                return (
                    "student",
                    "component",
                    "score",
                )

        return ()

