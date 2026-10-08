from django.utils import timezone
from rest_framework import serializers

from conciertos.captura_gira import concierto_existente, momento
from conciertos.models import Artista, Ciudad, Concierto, Recinto
from resenas.models import Reporte
from sugerencias.models import Sugerencia


# --- Para buscar y dar de alta artistas y recintos al capturar ---

class ArtistaOpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artista
        fields = ["id", "nombre", "slug", "genero"]


class RecintoOpcionSerializer(serializers.ModelSerializer):
    ciudad = serializers.SlugRelatedField(slug_field="slug", queryset=Ciudad.objects.all())
    ciudad_nombre = serializers.CharField(source="ciudad.nombre", read_only=True)

    class Meta:
        model = Recinto
        fields = ["id", "nombre", "slug", "direccion", "ciudad", "ciudad_nombre"]
        extra_kwargs = {"slug": {"read_only": True}}


# --- Capturar una gira ---

class FechaGiraSerializer(serializers.Serializer):
    recinto = serializers.PrimaryKeyRelatedField(queryset=Recinto.objects.select_related("ciudad"))
    fecha = serializers.DateField()
    hora = serializers.TimeField(required=False, allow_null=True)
    url_boletos = serializers.URLField(max_length=500, required=False, allow_blank=True)
    precio_desde = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True
    )


class GiraSerializer(serializers.Serializer):
    artista = serializers.PrimaryKeyRelatedField(queryset=Artista.objects.all())
    gira = serializers.CharField(max_length=150, required=False, allow_blank=True)
    url_boletos = serializers.URLField(max_length=500)
    imagen_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    genero = serializers.CharField(max_length=60, required=False, allow_blank=True)
    fechas = FechaGiraSerializer(many=True, allow_empty=False)

    def validate(self, datos):
        # Un error por fila, en su lugar: [{}, {"fecha": ["Ya existe..."]}, ...]
        errores, vistas, hay_error = [], set(), False
        for fila in datos["fechas"]:
            error = {}
            clave = (fila["recinto"].ciudad_id, fila["fecha"])
            if clave in vistas:
                error["fecha"] = ["Esta ciudad y día ya están en otra fila."]
            elif existente := concierto_existente(datos["artista"], fila["recinto"], fila["fecha"]):
                error["fecha"] = [f"Ya existe ese día: {existente.titulo} en {existente.recinto.nombre}."]
            vistas.add(clave)
            errores.append(error)
            hay_error = hay_error or bool(error)
        if hay_error:
            raise serializers.ValidationError({"fechas": errores})
        return datos


# --- Editar un concierto ---

class ConciertoEdicionSerializer(serializers.ModelSerializer):
    """Fecha y hora van por separado (como se capturan). En los de Ticketmaster solo se
    pueden cambiar los datos que la importación no sobrescribe cada noche."""

    artista = serializers.CharField(source="artista.nombre", read_only=True)
    recinto = serializers.PrimaryKeyRelatedField(queryset=Recinto.objects.select_related("ciudad"))
    recinto_nombre = serializers.CharField(source="recinto.__str__", read_only=True)
    fecha = serializers.DateField(write_only=True, required=False)
    hora = serializers.TimeField(write_only=True, required=False, allow_null=True)
    campos_bloqueados = serializers.SerializerMethodField()

    class Meta:
        model = Concierto
        fields = [
            "slug", "origen", "artista", "titulo", "gira", "recinto", "recinto_nombre", "fecha_hora",
            "hora_por_confirmar", "fecha", "hora", "estado", "url_boletos", "imagen_url", "genero",
            "precio_desde", "apertura_puertas", "campos_bloqueados",
        ]
        read_only_fields = ["slug", "origen", "fecha_hora", "hora_por_confirmar"]

    def get_campos_bloqueados(self, concierto):
        if concierto.origen != Concierto.Origen.TICKETMASTER:
            return []
        # Los que manda Ticketmaster, con los nombres de este formulario (fecha_hora -> fecha y hora).
        campos = [c for c in Concierto.CAMPOS_TICKETMASTER if c not in ("fecha_hora", "invitados", "artista")]
        return campos + ["fecha", "hora"]

    def validate(self, datos):
        bloqueados = set(self.get_campos_bloqueados(self.instance)) & set(datos)
        if bloqueados:
            raise serializers.ValidationError({
                campo: ["Viene de Ticketmaster: se actualiza solo cada noche."] for campo in bloqueados
            })
        if "fecha" in datos or "hora" in datos:
            local = timezone.localtime(self.instance.fecha_hora)  # lo que falte se toma de la fecha actual
            fecha = datos.pop("fecha", local.date())
            hora = datos.pop("hora", None if self.instance.hora_por_confirmar else local.time())
            datos["fecha_hora"] = momento(fecha, hora)
            datos["hora_por_confirmar"] = hora is None
        return datos


# --- Sugerencias y reportes ---

class SugerenciaRevisionSerializer(serializers.ModelSerializer):
    ciudad = serializers.CharField(source="ciudad.nombre")
    sugirio = serializers.CharField(source="usuario.first_name")
    concierto = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Sugerencia
        fields = [
            "id", "artista", "ciudad", "recinto", "fecha", "hora", "url_boletos", "comentario",
            "estado", "motivo_rechazo", "concierto", "sugirio", "creada",
        ]


class ReporteRevisionSerializer(serializers.ModelSerializer):
    motivo = serializers.CharField(source="get_motivo_display")
    reporto = serializers.CharField(source="usuario.first_name")
    texto = serializers.CharField(source="resena.texto")
    general = serializers.IntegerField(source="resena.general")
    autor = serializers.CharField(source="resena.usuario.first_name")
    concierto = serializers.SerializerMethodField()
    reportes_de_la_resena = serializers.IntegerField(read_only=True)  # anotación de la vista

    class Meta:
        model = Reporte
        fields = [
            "id", "resena", "motivo", "comentario", "reporto", "creado", "texto", "general", "autor",
            "concierto", "reportes_de_la_resena",
        ]

    def get_concierto(self, reporte):
        c = reporte.resena.concierto
        return {"slug": c.slug, "artista": c.artista.nombre, "ciudad": c.recinto.ciudad.nombre, "fecha_hora": c.fecha_hora}
