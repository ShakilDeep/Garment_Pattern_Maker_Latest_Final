"""Garment tools (CAD-03): darts, slash-and-spread, fullness, pleats and tucks, fold and unfold.

Each tool is a pure change of one piece. The ones that open the outline share `opening.py`: cut the edge
exactly (`split_join.split_edge`), then turn or shift the run of outline on one side of the cut, carrying
the marks inside it. New ids are derived from a caller's prefix, so every size of a style gets the same ids.
"""
