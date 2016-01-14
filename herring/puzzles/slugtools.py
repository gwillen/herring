from autoslug.utils import slugify
import random


COMMON_WORDS = {
    'the', 'of', 'to', 'a', 'and', 'i', 'in', 'you', 'it', 'is', 'that',
    'for', 'on', 'with', 'was', 'this', 'be', 'he', 'are', 'as', 'have',
    'we', 'at', 'me', 'my', 'but', 'not', 'what', 'by', 'they', 'from',
    'so', 'all', 'do', 'your', 'one', 'if', 'just', 'like', 'there', 'no',
    'or', 'can', 'about', 'an', 'up', 'get', 'out', 'when', 'will',
    'who', "dont", 'his', 'more', 'she', 'has', 'which', 'now', 'how',
    'were', 'go', 'had', 'would', 'here', 'them', 'her', 'him', 'been',
    'some', 'well', 'their', 'only', 'then', 'got', 'other', 'also',
    'than', 'come', 'going', 'did', 'into', 'make', 'very', "im",
    'over', 'because', 'made', 'much', 'really', 'where', 'us', 'why',
    'way', 'could', 'our', 'even', 'too', 'its', 'being', 'am', 'may',
    'such', 'those', 'through', 'use', 'does', 'thing', 'things',
    'find', 'again', 'cant', 'around', 'between', 'ever', 'every',
    'makes', 'goes', 'went', 'heres', 'theres', 'any', 'youre', 'puzzle'
}


def title_to_slug(title):
    """
    Get a significant word or two from a puzzle title, for use as a
    clean identifier, such as for a channel name.
    """
    slug1 = slugify(title)
    parts = slug1.split('-')
    new_parts = []
    for part in parts:
        if part not in COMMON_WORDS:
            new_parts.append(part)
            if len(part) >= 5 or len(new_parts) >= 2:
                break
    if not new_parts:
        new_parts = parts[:2]
    return '-'.join(new_parts)


def puzzle_to_slug(puzzle):
    """
    Make a complete puzzle slug from a Puzzle object, such as
    'r4p9-anagrams'.
    """
    id_part = puzzle.identifier().lower()
    title_part = title_to_slug(puzzle.name)
    parts = [id_part, title_part]
    return '-'.join(parts)[:20]


def arbitrary_slug():
    """
    I tried this for a migration at one point. Don't worry about it.
    """
    return 'arbitrary-%x' % random.randrange(0, 1 << 32)
