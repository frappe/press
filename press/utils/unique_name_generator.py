# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors

import random
import string


def generate(segment_length=3, num_segments=3, separator="-"):
	# Define the character set: only lowercase letters
	characters = string.ascii_lowercase

	# Generate segments
	segments = []
	for _ in range(num_segments):
		segment = "".join(random.choice(characters) for _ in range(segment_length))
		segments.append(segment)

	# Join segments with the separator
	random_id = separator.join(segments)
	return random_id
