import winsound

i = 0

while i < 10:
    winsound.Beep(32767, 500)  # 1000 Hz przez 500 ms (piknięcie)
    i = i + 1