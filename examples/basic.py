"""Decode, inspect, modify, and encode a Nano Markup document."""

import nanomarkup

source = b"""\
..
    user..
        name Ariana
        age 12
        address|
            Lisova 20
            1111 Example City
    interests:
        cycling
        music
"""

value = nanomarkup.loads(source)
if not isinstance(value, dict):
    raise TypeError("expected a mapping root")

user = value.get("user")
interests = value.get("interests")
if not isinstance(user, dict) or not isinstance(interests, list):
    raise TypeError("document does not match the expected shape")

name = user.get("name")
age = user.get("age")
address = user.get("address")
if not isinstance(name, str) or not isinstance(age, str) or not isinstance(address, str):
    raise TypeError("user fields must be strings")

print(f"{name} is {int(age)} and likes {', '.join(map(str, interests))}.")
print(address)

user["age"] = "13"
interests.append("swimming")
print(nanomarkup.dumps(value))
