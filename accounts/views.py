
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render


def login_view(request):

    if request.user.is_authenticated:
        return redirect("school_core:grade_entry")

    error = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            login(
                request,
                user,
            )

            next_url = request.GET.get(
                "next"
            )

            if next_url:
                return redirect(next_url)

            return redirect(
                "school_core:grade_entry"
            )

        error = (
            "اسم المستخدم أو كلمة المرور غير صحيحة."
        )

    return render(
        request,
        "accounts/login.html",
        {
            "error": error,
        },
    )
