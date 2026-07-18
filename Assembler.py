# data = bytes([0] * (18) * 2)

# with open(r"Data\registers.bin", "wb") as file:
#     file.write(data)

def assemble():
    with open("instructions.arc", 'r') as program:
        instructions = program.read().splitlines()
    