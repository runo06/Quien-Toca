from django.contrib import admin, messages
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from . import moderacion
from .models import Reporte, Resena


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ["resumen", "autor", "concierto", "general", "reportes_pendientes", "oculta", "creada"]
    list_filter = ["oculta", "general", "creada"]
    list_select_related = ["usuario", "concierto__artista"]
    search_fields = ["texto", "usuario__first_name", "usuario__email", "concierto__titulo", "concierto__artista__nombre"]
    readonly_fields = ["usuario", "concierto", "asistio", "creada", "editada"]
    fields = ["usuario", "concierto", "general", "show", "sonido", "puntualidad", "recinto", "texto", "asistio", "oculta", "creada", "editada"]
    actions = ["ocultar", "mostrar"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_pendientes=Count("reportes", filter=Q(reportes__estado=Reporte.Estado.PENDIENTE))
        )

    def has_add_permission(self, request):
        return False  # las reseñas las escribe la gente en la página

    @admin.display(description="reseña")
    def resumen(self, resena):
        return Truncator(resena.texto).chars(70)

    @admin.display(description="autor", ordering="usuario__first_name")
    def autor(self, resena):
        return f"{resena.usuario.first_name} <{resena.usuario.email}>"

    @admin.display(description="reportes pendientes", ordering="n_pendientes")
    def reportes_pendientes(self, resena):
        return resena.n_pendientes or "—"

    @admin.action(description="Ocultar las reseñas seleccionadas")
    def ocultar(self, request, queryset):
        queryset.update(oculta=True)

    @admin.action(description="Volver a mostrar las reseñas seleccionadas")
    def mostrar(self, request, queryset):
        queryset.update(oculta=False)


class SoloPendientes(admin.SimpleListFilter):
    """Por defecto se ven los pendientes: es la bandeja de trabajo."""

    title = "estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return [*Reporte.Estado.choices, ("todos", "Todos")]

    def choices(self, changelist):
        for valor, nombre in self.lookup_choices:
            yield {
                "selected": (self.value() or Reporte.Estado.PENDIENTE) == valor,
                "query_string": changelist.get_query_string({self.parameter_name: valor}),
                "display": nombre,
            }

    def queryset(self, request, queryset):
        valor = self.value() or Reporte.Estado.PENDIENTE
        return queryset if valor == "todos" else queryset.filter(estado=valor)


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ["texto_de_la_resena", "motivo", "comentario", "quien_reporta", "creado", "estado", "resena_oculta"]
    list_filter = [SoloPendientes, "motivo"]
    list_select_related = ["resena__usuario", "usuario"]
    readonly_fields = ["enlace_resena", "texto_completo", "usuario", "motivo", "comentario", "creado", "revisado"]
    fields = ["enlace_resena", "texto_completo", "motivo", "comentario", "usuario", "estado", "creado", "revisado"]
    actions = ["aceptar", "descartar"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="reseña reportada")
    def texto_de_la_resena(self, reporte):
        return Truncator(reporte.resena.texto).chars(80)

    @admin.display(description="reportó")
    def quien_reporta(self, reporte):
        return reporte.usuario.email

    @admin.display(description="reseña oculta", boolean=True)
    def resena_oculta(self, reporte):
        return reporte.resena.oculta

    @admin.display(description="reseña")
    def enlace_resena(self, reporte):
        url = reverse("admin:resenas_resena_change", args=[reporte.resena_id])
        return format_html('<a href="{}">{}</a>', url, reporte.resena)

    @admin.display(description="texto de la reseña")
    def texto_completo(self, reporte):
        return reporte.resena.texto

    @admin.action(description="Aceptar: ocultar la reseña")
    def aceptar(self, request, queryset):
        ocultas, resueltos = moderacion.aceptar(queryset)
        self.message_user(request, f"{ocultas} reseña(s) ocultas; {resueltos} reporte(s) resueltos.", messages.SUCCESS)

    @admin.action(description="Descartar: la reseña está bien")
    def descartar(self, request, queryset):
        n = moderacion.descartar(queryset)
        self.message_user(request, f"{n} reporte(s) descartados.", messages.SUCCESS)
