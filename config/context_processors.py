from django.conf import settings


def branding(request):
    return {"RENTFLOW": settings.RENTFLOW, "DEBUG": settings.DEBUG}
