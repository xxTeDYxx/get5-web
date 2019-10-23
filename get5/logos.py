import glob
import os


_logos = set()


def get_pano_dir():
    return os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), 'static', 'resource', 'csgo', 'materials', 'panorama', 'images', 'tournaments', 'teams'))


def get_logo_dir():
    return os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), 'static', 'resource', 'csgo', 'resource', 'flash', 'econ', 'tournaments', 'teams'))


def initialize_logos():
    global _logos
    logo_path = get_logo_dir()
    pano_logo_path = get_pano_dir()
    for filename in glob.glob(os.path.join(logo_path, '*.png')):
        team_tag_filename = os.path.basename(filename)
        # Remove the extension
        team_tag = os.path.splitext(team_tag_filename)[0]
        _logos.add(team_tag)

    for filename in glob.glob(os.path.join(pano_logo_path, '*.svg')):
        team_tag_filename = os.path.basename(filename)
        # Remove the extension
        team_tag = os.path.splitext(team_tag_filename)[0]
        if not has_logo(team_tag):
            _logos.add(team_tag)


def add_new_logo(tag):
    global _logos
    if not has_logo(tag):
        _logos.add(tag)


def has_logo(tag):
    return tag in _logos


def get_logo_choices():
    list = [('', 'None')] + [(x, x) for x in _logos]
    return sorted(list, key=lambda x: x[0])


def get_logo_img(tag):
    if has_logo(tag) and os.path.isfile(os.path.join(get_logo_dir(), '{}.png'.format(tag))):
        return '/static/resource/csgo/resource/flash/econ/tournaments/teams/{}.png'.format(tag)
    elif has_logo(tag) and os.path.isfile(os.path.join(get_pano_dir(), '{}.svg'.format(tag))):
        return '/static/resource/csgo/materials/panorama/images/tournaments/teams/{}.svg'.format(tag)
    else:
        return None
