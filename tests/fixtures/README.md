# Maintained offline test fixtures

`stress/cases.jsonl` and its authored EML bytes exercise reader, coverage, budget and transport failure cases. They are migrated byte-for-byte from the historical 24-case stress suite and are not part of the 60 measured benchmark cases. The current negative tests consume them, so they remain live test inputs. Their original versions are recoverable from the history ZIP.

`regression_replies.json` retains only the original C12/S02 model rows used by current quote-alignment and repair regressions. Each group records the old source file path and hash. Tests no longer require entire historical run directories. Saved output text is not edited or presented as new model inference.
