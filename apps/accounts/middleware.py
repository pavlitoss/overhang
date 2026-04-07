class OrganizationMiddleware:
    """Attaches request.org for every authenticated request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.org = None
        if request.user.is_authenticated:
            membership = (
                request.user.memberships.select_related("organization").first()
            )
            if membership:
                request.org = membership.organization
        return self.get_response(request)
