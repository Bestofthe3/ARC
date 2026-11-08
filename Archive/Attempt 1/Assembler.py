import os

# data = bytes([0] * (18) * 2)
#
# with open(r"Data\registers.bin", "wb") as file:
#     file.write(data)

def assemble(path_to_file: str):
    # Creates a new file with the code compiled into machine language.
    with (open(path_to_file, 'r') as instr, open("Data/disk.bin", 'r') as disk,
            open("Data/memory.bin", 'r') as mem, open("Data/registers.bin", 'r') as reg):
        instructions = [item.upper() for item in instr.read().splitlines()]
        disk = disk.read().splitlines()
        memory = mem.read().splitlines()
        registers = reg.read().splitlines()

    machine_code = []
    for instr_idx, instruction in enumerate(instructions):
        if not instruction:
            continue

        # Turning the instructions into machine code
        for idx, token in enumerate(instruction.split()):
            if idx == 1:
                match token:
                    case 'NOP':
                        machine_code += '0000000000000000'
                    # Continue here..
    
    with open("Data/machine_code.bin", 'w') as comp_code:
        comp_code.write(machine_code)


if __name__ == "__main__":
    assemble("instructions.arc")
