# Seed a dev database with sample rounds/puzzles (idempotent). Run via manage.py shell.
from puzzles.models import Puzzle, Round
if not Round.objects.exists():
    r1 = Round.objects.create(name='The Warehouse', number=1)
    r2 = Round.objects.create(name='The Dock', number=2)
    for n, name in enumerate(['Anagram Antics', 'Crossword Chaos', 'Logic of Lists', 'Final Warehouse Meta'], 1):
        Puzzle.objects.create(parent=r1, name=name, number=n, is_meta=name.startswith('Final'))
    for n, name in enumerate(['Shipping Containers', 'Knots and Ropes'], 1):
        Puzzle.objects.create(parent=r2, name=name, number=n)
    Puzzle.objects.filter(name='Crossword Chaos').update(answer='SOLVED', tags='wordplay')
    Puzzle.objects.filter(name='Logic of Lists').update(note='needs eyes', tags='logic, grid')
print('rounds:', Round.objects.count(), 'puzzles:', Puzzle.objects.count())
