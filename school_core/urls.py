from django.urls import path

from . import views


app_name = "school_core"


urlpatterns = [

    path(
        "grades/entry/",
        views.grade_entry,
        name="grade_entry",
    ),

    path(
        "grades/auto-save/",
        views.auto_save_grade,
        name="auto_save_grade",
    ),

    path(
        "grades/approve/",
        views.approve_assessment,
        name="approve_assessment",
    ),

]