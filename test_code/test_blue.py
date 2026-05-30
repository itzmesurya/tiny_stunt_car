def classify_color(r, g, b, clear):
    if clear < 20:                                          return None
    if max(r,g,b) < 40:                                    return None
    if r > 170 and g < 60  and b < 60:                    return "RED"
    if r > 120 and g > 70  and b < 50 and r > g:          return "YELLOW"
    if g > 100 and g > r   and g > b * 2:                 return "GREEN"
    if r > 100 and g > 60  and abs(g-b) < 15 \
       and r > g and r < 140 and clear > 150:              return "PURPLE"
    if r < 80  and g > 85  and b > 85 \
       and abs(g - b) < 20 and clear > 150:               return "BLUE"
    return None

# Test your actual readings
print(classify_color( 56, 101,  98, 975))   # → BLUE
print(classify_color( 52,  94, 113, 231))   # → BLUE
print(classify_color( 56,  98, 103, 326))   # → BLUE
print(classify_color( 75,  94,  93, 180))   # → BLUE
print(classify_color(222,  39,  34, 343))   # → RED
print(classify_color(126,  90,  35, 2927))  # → YELLOW
print(classify_color( 78, 125,  43, 751))   # → GREEN
print(classify_color(115,  78,  73, 864))   # → PURPLE
print(classify_color(  0,   0,   0,  15))   # → None
# Borderline reads that should NOT trigger:
print(classify_color( 93,  98,  98,  52))   # → None (clear too low)
print(classify_color( 75,  94,  93, 180))   # → BLUE (borderline, check)