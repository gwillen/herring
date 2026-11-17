from puzzles import site_settings


def site(request):
    """The dashboard settings, for the page header and menu (team name, hunt site link, menu notes)."""
    return {'site': site_settings.current()}
