from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .aprobar import aprobar, rechazar
from .models import Sugerencia


class PorEstado(admin.SimpleListFilter):
    """Por defecto se ven las pendientes: es la bandeja de trabajo."""

    title = "estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return [*Sugerencia.Estado.choices, ("todas", "Todas")]

    def choices(self, changelist):
        for valor, nombre in self.lookup_choices:
            yield {
                "selected": (self.value() or Sugerencia.Estado.PENDIENTE) == valor,
                "query_string": changelist.get_query_string({self.parameter_name: valor}),
                "display": nombre,
            }

    def queryset(self, request, queryset):
        valor = self.value() or Sugerencia.Estado.PENDIENTE
        return queryset if valor == "todas" else queryset.filter(estado=valor)


@admin.register(Sugerencia)
class SugerenciaAdmin(admin.ModelAdmin):
    list_display = ["artista", "recinto", "ciudad", "fecha", "hora", "boletos", "quien", "creada", "estado"]
    list_filter = [PorEstado, "ciudad"]
    list_select_related = ["ciudad", "usuario"]
    search_fields = ["artista", "recinto", "usuario__email"]
    # Puedes corregir el nombre del artista o del recinto antes de aprobar.
    fields = [
        "artista", "ciudad", "recinto", "fecha", "hora", "url_boletos", "comentario",
        "quien", "estado", "motivo_rechazo", "enlace_concierto", "creada", "revisada",
    ]
    readonly_fields = ["quien", "estado", "enlace_concierto", "creada", "revisada"]
    actions = ["aprobar_seleccionadas", "rechazar_seleccionadas"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="sugirió")
    def quien(self, sugerencia):
        return f"{sugerencia.usuario.first_name} <{sugerencia.usuario.email}>"

    @admin.display(description="boletos")
    def boletos(self, sugerencia):
        return format_html('<a href="{}" target="_blank" rel="noopener">abrir</a>', sugerencia.url_boletos)

    @admin.display(description="concierto")
    def enlace_concierto(self, sugerencia):
        if not sugerencia.concierto_id:
            return "—"
        url = reverse("admin:conciertos_concierto_change", args=[sugerencia.concierto_id])
        return format_html('<a href="{}">{}</a>', url, sugerencia.concierto)

    @admin.action(description="Aprobar: crear el concierto")
    def aprobar_seleccionadas(self, request, queryset):
        for sugerencia in queryset:
            concierto = aprobar(sugerencia)
            url = reverse("admin:conciertos_concierto_change", args=[concierto.pk])
            self.message_user(
                request, format_html('Aprobada: <a href="{}">{}</a> (revisa imagen y precios).', url, concierto), messages.SUCCESS
            )

    @admin.action(description="Rechazar (escribe antes el motivo en cada una, si quieres)")
    def rechazar_seleccionadas(self, request, queryset):
        sugerencias = list(queryset)  # se leen ya: al rechazarlas dejan de ser "pendientes"
        for sugerencia in sugerencias:
            rechazar(sugerencia)
        self.message_user(request, f"{len(sugerencias)} sugerencia(s) rechazadas.", messages.SUCCESS)
