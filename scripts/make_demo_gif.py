from pathlib import Path


OUT = Path(__file__).resolve().parent.parent / "docs" / "agent-demo.gif"
WIDTH = 960
HEIGHT = 540
SCALE = 3
BG = 0
FG = 1
DIM = 2
GREEN = 3

FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "01010", "00100", "00100", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "01100", "01000"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    ">": ["10000", "01000", "00100", "00010", "00100", "01000", "10000"],
}


def put_pixel(buf, x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        buf[y * WIDTH + x] = color


def draw_text(buf, x, y, text, color=FG):
    cursor = x
    for char in text.upper():
        glyph = FONT.get(char, FONT[" "])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    for sy in range(SCALE):
                        for sx in range(SCALE):
                            put_pixel(buf, cursor + col * SCALE + sx, y + row * SCALE + sy, color)
        cursor += 6 * SCALE


def frame(lines):
    buf = bytearray([BG]) * (WIDTH * HEIGHT)
    for y in range(40, HEIGHT - 40):
        put_pixel(buf, 34, y, GREEN)
    draw_text(buf, 60, 42, "ASTER & ROW SUPPORT AGENT", GREEN)
    draw_text(buf, 60, 82, "2-4 MINUTE DEMO COMPRESSED AS GIF", DIM)
    y = 136
    for line, color in lines:
        draw_text(buf, 60, y, line, color)
        y += 42
    return bytes(buf)


def lzw_encode(indices):
    min_code_size = 2
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    output_bits = []

    def emit(code):
        for bit in range(code_size):
            output_bits.append((code >> bit) & 1)

    # Use frequent clear codes so the stream stays simple and decoder-compatible.
    # The file is larger, but the generated demo is still small enough for a README.
    emit(clear)
    for value in indices:
        emit(value)
        emit(clear)
    emit(end)

    data = bytearray()
    current = 0
    count = 0
    for bit in output_bits:
        current |= bit << count
        count += 1
        if count == 8:
            data.append(current)
            current = 0
            count = 0
    if count:
        data.append(current)
    return bytes(data)


def write_subblocks(out, data):
    for idx in range(0, len(data), 255):
        block = data[idx:idx + 255]
        out.append(len(block))
        out.extend(block)
    out.append(0)


def main():
    OUT.parent.mkdir(exist_ok=True)
    frames = [
        [("Q: HOW LONG CAN I RETURN A BACKPACK?", FG), ("A: 30 CALENDAR DAYS FROM DELIVERY", FG), ("SOURCE: 01-RETURNS-POLICY-CURRENT.MD", DIM)],
        [("Q: WHERE IS ORD-1007?", FG), ("A: SHIPPED WITH UPS", FG), ("ETA: AUGUST 22 2026", FG), ("TOOL: ORDER LOOKUP SANITIZED", DIM)],
        [("Q: WHAT ABOUT CANADA?", FG), ("A: CANADA IS SUPPORTED", FG), ("5-9 BUSINESS DAYS AFTER DISPATCH", FG), ("DUTIES OR TAXES ARE NOT PREPAID", DIM)],
        [("Q: ARE ALL FABRICS VEGAN?", FG), ("A: SUPPLIED INFO IS INSUFFICIENT", FG), ("HUMAN CONFIRMATION RECOMMENDED", GREEN)],
        [("EVALUATION SUITE", GREEN), ("VISIBLE CASES PLUS ORIGINAL CASES", FG), ("RESULT: 21/21 PASSED", GREEN)],
    ]
    out = bytearray(b"GIF89a")
    out.extend(WIDTH.to_bytes(2, "little"))
    out.extend(HEIGHT.to_bytes(2, "little"))
    out.extend(bytes([0b10000001, 0, 0]))
    out.extend(bytes([12, 14, 18, 238, 242, 247, 132, 146, 166, 52, 211, 153]))
    out.extend(b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00")
    for lines in frames:
        out.extend(b"\x21\xf9\x04\x04")
        out.extend((220).to_bytes(2, "little"))
        out.extend(b"\x00\x00")
        out.append(0x2C)
        out.extend((0).to_bytes(2, "little"))
        out.extend((0).to_bytes(2, "little"))
        out.extend(WIDTH.to_bytes(2, "little"))
        out.extend(HEIGHT.to_bytes(2, "little"))
        out.append(0)
        out.append(2)
        write_subblocks(out, lzw_encode(frame(lines)))
    out.append(0x3B)
    OUT.write_bytes(out)
    print(OUT)


if __name__ == "__main__":
    main()
