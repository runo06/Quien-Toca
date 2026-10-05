from django.contrib import admin

from .models import Artista, Ciudad, Concierto, PrecioZona, Recinto

admin.site.site_header = "¿Quién toca? · Administración"
admin.site.site_title = "¿Quién toca?"


@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "slug", "radio_km", "es_predeterminada"]
    prepopulated_fields = {"slug": ["nombre"]}


@admin.register(Recinto)
class RecintoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "ciudad", "id_ticketmaster"]
    list_filter = ["ciudad"]
    search_fields = ["nombre"]  # también lo usa el autocompletado del concierto
    readonly_fields = ["id_ticketmaster"]


@admin.register(Artista)
class ArtistaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "genero", "id_ticketmaster"]
    search_fields = ["nombre"]
    readonly_fields = ["id_ticketmaster"]


class PrecioZonaInline(admin.TabularInline):
    model = PrecioZona
    extra = 1


@admin.register(Concierto)
class ConciertoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "artista", "ciudad", "fecha_hora", "estado", "origen"]
    list_filter = ["origen", "estado", "recinto__ciudad", "fecha_hora"]
    list_select_related = ["artista", "recinto__ciudad"]  # evita una consulta por fila
    search_fields = ["titulo", "artista__nombre", "recinto__nombre"]
    date_hierarchy = "fecha_hora"
    autocomplete_fields = ["artista", "invitados", "recinto"]
    inlines = [PrecioZonaInline]
    fieldsets = [
        (None, {"fields": ["titulo", "slug", "artista", "invitados", "recinto", "gira", "genero"]}),
        ("Fecha", {"fields": ["fecha_hora", "hora_por_confirmar", "apertura_puertas", "estado"]}),
        ("Boletos", {"fields": ["url_boletos", "precio_desde", "moneda", "imagen_url"]}),
        ("Origen", {"fields": ["origen", "id_ticketmaster", "importado_en", "creado_en", "actualizado_en"]}),
    ]

    @admin.display(description="ciudad", ordering="recinto__ciudad__nombre")
    def ciudad(self, obj):
        return obj.recinto.ciudad

    def get_readonly_fields(self, request, obj=None):
        campos = ["origen", "id_ticketmaster", "importado_en", "creado_en", "actualizado_en"]
        if obj and obj.origen == Concierto.Origen.TICKETMASTER:
            # La importación nocturna los sobrescribiría: mejor no dejarlos editar.
            campos += list(Concierto.CAMPOS_TICKETMASTER)
        return campos

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        concierto = form.instance
        if concierto.precio_desde is None:
            minimo = concierto.precios.order_by("precio").values_list("precio", flat=True).first()
            if minimo is not None:
                concierto.precio_desde = minimo
                concierto.save(update_fields=["precio_desde"])
