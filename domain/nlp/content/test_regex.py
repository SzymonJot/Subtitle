import regex as re

original_regex = re.compile(
    r"""
    (?<!\b(?:dr|prof|mr|mrs|ms|st|jr|sr|e\.g|i\.e|no|np|tj|kap|art|al)\.) # Abbreviations
    (?<=\.|!|\?)                                                          # Split after . ! ?
    \s+                                                                   # Followed by whitespace
    (?=[A-Z0-9"'])                                                        # Lookahead: Next char is usually Upper or Value (optional, strict)
    """,
    re.IGNORECASE | re.VERBOSE,
)

new_regex = re.compile(
    r"""
    (?<!\b(?:dr|prof|mr|mrs|ms|st|jr|sr|e\.g|i\.e|no|np|tj|kap|art|al)\.) # Abbreviations
    (?<=\.|!|\?)                                                          # Split after . ! ?
    \s+                                                                   # Followed by whitespace
    (?=[A-Z0-9"'-])                                                       # Lookahead: ADDED DASH HERE
    """,
    re.IGNORECASE | re.VERBOSE,
)

text = "Allt tycks leda till honom. Även stackars Innocens."

# Write to file
with open("test_output.txt", "w", encoding="utf-8") as f:
    f.write("Original split:\n")
    for s in original_regex.split(text):
        f.write(f"  - {s}\n")
    f.write("\nNew split:\n")
    for s in new_regex.split(text):
        f.write(f"  - {s}\n")
