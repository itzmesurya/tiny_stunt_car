def classify_color(r, g, b, clear):
    if clear < 20:                                          return None
    if max(r,g,b) < 40:                                    return None
    if r > 170 and g < 60  and b < 60:                    return "RED"
    if r > 120 and g > 70  and b < 50 and r > g:          return "YELLOW"
    if g > 100 and g > r   and g > b*2:                   return "GREEN"
    if r > 100 and g > 60  and abs(g-b) < 15 \
       and r > g and r < 140 and clear > 150:              return "PURPLE"
    if clear > 2000 and r > 95 and g > 85 \
       and abs(r-g) < 20 and b < 70:                      return "WHITE"
    return None

# Test your actual readings
print(classify_color(105, 94, 51, 4366))   # should print WHITE
print(classify_color(222, 39, 34,  343))   # should print RED
print(classify_color(126, 90, 35, 2927))   # should print YELLOW
print(classify_color( 78,125, 43,  751))   # should print GREEN
print(classify_color(115, 78, 73,  864))   # should print PURPLE
print(classify_color(  0,  0,  0,   15))   # should print None