"""
Root URL configuration for Research Marketplace.
All app URLs are namespaced under /api/v1/.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include([
        path("auth/",          include("apps.users.urls",        namespace="auth")),
        path("profiles/",      include("apps.profiles.urls",     namespace="profiles")),
        path("projects/",      include("apps.projects.urls",     namespace="projects")),
        path("proposals/",     include("apps.proposals.urls",    namespace="proposals")),
        path("payments/",      include("apps.payments.urls",     namespace="payments")),
        path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

# Customize Admin Panel
admin.site.site_header = "Research Marketplace Admin"
admin.site.site_title = "RM Admin"
admin.site.index_title = "پنل مدیریت پلتفرم"
