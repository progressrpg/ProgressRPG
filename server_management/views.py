from django.shortcuts import render
from django.views.decorators.cache import cache_page


# @cache_page(60 * 15)
def maintenance_view(request):
    profile = request.user.profile

    return render(request, "server_management/maintenance.html", {"profile": profile})
