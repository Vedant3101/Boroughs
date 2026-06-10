"""Project-wide pagination — client can request page_size up to a hard cap."""
from rest_framework.pagination import PageNumberPagination


class BoroughsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
