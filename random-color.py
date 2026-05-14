import random
colors = ['red', 'blue', 'green', 'yellow']

print(f"Single pick: {random.choice(colors)}")
print(f"Two unique picks: {random.sample(colors, 2)}")