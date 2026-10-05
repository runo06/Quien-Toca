from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class Paginacion(PageNumberPagination):
    """Paginación con nombres en español: ?pagina=2 y {total, siguiente, anterior, resultados}."""

    page_query_param = "pagina"

    def get_paginated_response(self, data):
        return Response({
            "total": self.page.paginator.count,
            "siguiente": self.get_next_link(),
            "anterior": self.get_previous_link(),
            "resultados": data,
        })
