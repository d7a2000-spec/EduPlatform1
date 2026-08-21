
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClassRoom(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="classrooms",
    )
    name = models.CharField(max_length=100)
    level = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Section(models.Model):
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.classroom} - {self.name}"


class Subject(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="subjects",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="teachers",
    )
    employee_code = models.CharField(
        max_length=50,
        unique=True,
    )
    specialization = models.CharField(
        max_length=150,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username}"
            f" - {self.school.name}"
        )


class TeachingAssignment(models.Model):
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "teacher",
            "subject",
            "section",
        )
        ordering = [
            "teacher",
            "subject",
            "section",
        ]

    def __str__(self):
        return (
            f"{self.teacher} - "
            f"{self.subject.name} - "
            f"{self.section}"
        )


class Student(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="students",
    )
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="students",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="students",
    )
    student_code = models.CharField(
        max_length=50,
        unique=True,
    )
    first_name = models.CharField(
        max_length=100
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
    )
    last_name = models.CharField(
        max_length=100
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "last_name",
            "first_name",
        ]

    def __str__(self):
        full_name = (
            f"{self.first_name} "
            f"{self.middle_name} "
            f"{self.last_name}"
        )

        return " ".join(
            full_name.split()
        )


class GradeAssessment(models.Model):
    """
    التقييم أو الفترة الدراسية للمادة.

    مثال:

    اللغة العربية - الشهر الأول - 100
    اللغة العربية - الشهر الثاني - 100
    اللغة العربية - نصف السنة - 100
    """

    STATUS_DRAFT = "draft"
    STATUS_APPROVED = "approved"

    STATUS_CHOICES = (
        (
            STATUS_DRAFT,
            "مسودة",
        ),
        (
            STATUS_APPROVED,
            "معتمد",
        ),
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="grade_assessments",
    )

    name = models.CharField(
        max_length=150
    )

    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=100,
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = (
            "subject",
            "name",
        )
        ordering = [
            "subject",
            "order",
            "id",
        ]

    def __str__(self):
        return (
            f"{self.subject.name} - "
            f"{self.name} "
            f"({self.max_score})"
        )

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                {
                    "max_score": (
                        "الدرجة العظمى يجب أن "
                        "تكون أكبر من صفر."
                    )
                }
            )


class GradeComponent(models.Model):
    """
    مكوّن داخل تقييم محدد.

    مثال:

    الشهر الأول = 100

    قواعد وإملاء = 45
    الأدب والمطالعة = 30
    الإنشاء = 25

    المجموع = 100
    """

    assessment = models.ForeignKey(
        GradeAssessment,
        on_delete=models.CASCADE,
        related_name="components",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=150
    )

    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
    null=True,
    blank=True,
)
    

    class Meta:
        ordering = [
            "assessment",
            "order",
            "id",
        ]

    def __str__(self):
        if self.assessment:
            return (
                f"{self.assessment.subject.name} - "
                f"{self.assessment.name} - "
                f"{self.name} "
                f"({self.max_score})"
            )

        return (
            f"{self.name} "
            f"({self.max_score})"
        )

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                {
                    "max_score": (
                        "درجة المكوّن يجب أن "
                        "تكون أكبر من صفر."
                    )
                }
            )

        if self.assessment:
            if (
                self.max_score
                > self.assessment.max_score
            ):
                raise ValidationError(
                    {
                        "max_score": (
                            "درجة المكوّن لا يمكن "
                            "أن تتجاوز الدرجة العظمى "
                            "للتقييم."
                        )
                    }
                )


class StudentGrade(models.Model):
    """
    درجة طالب في مكوّن محدد.

    الطالب
        ↓
    مكوّن التقييم
        ↓
    الدرجة
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="grades",
    )

    component = models.ForeignKey(
        GradeComponent,
        on_delete=models.CASCADE,
        related_name="student_grades",
    )

    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
    null=True,
    blank=True,
)
   

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = (
            "student",
            "component",
        )
        ordering = [
            "student",
            "component",
        ]

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.component.name} - "
            f"{self.score}"
        )

    def clean(self):
        errors = {}

        if self.score < 0:
            errors["score"] = (
                "درجة الطالب لا يمكن أن تكون أقل من صفر."
            )

        if self.component_id:

            if (
                self.score
                > self.component.max_score
            ):
                errors["score"] = (
                    "درجة الطالب لا يمكن أن "
                    "تتجاوز الدرجة العظمى للمكوّن."
                )

            if (
                self.component.assessment
                and self.component.assessment.status
                == GradeAssessment.STATUS_APPROVED
            ):
                errors["score"] = (
                    "لا يمكن تعديل درجة طالب "
                    "ضمن تقييم معتمد."
                )

        if errors:
            raise ValidationError(errors)

