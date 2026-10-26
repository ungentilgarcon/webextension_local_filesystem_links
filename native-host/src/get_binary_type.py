import struct

IMAGE_FILE_MACHINE_I386=332
IMAGE_FILE_MACHINE_IA64=512
IMAGE_FILE_MACHINE_AMD64=34404
# source from https://stackoverflow.com/questions/1345632/determine-if-an-executable-or-library-is-32-or-64-bits-on-windows

# bat & msi not detected --> stick to previous detection method for Win32
def generateReturn(val, text):
    res = {}
    res["isBinary"] = val
    res["readable"] = text
    return res

def GetBinaryType(fileName):
    with open(fileName, "rb") as executable:
        if executable.read(2) != b"MZ":
            return generateReturn(False, "Not an EXE file")

        executable.seek(60)
        header_offset = struct.unpack("<L", executable.read(4))[0]
        executable.seek(header_offset + 4)
        machine = struct.unpack("<H", executable.read(2))[0]

    if machine == IMAGE_FILE_MACHINE_I386:
        return generateReturn(True, "IA-32 (32-bit x86)")
    if machine == IMAGE_FILE_MACHINE_IA64:
        return generateReturn(True, "IA-64 (Itanium)")
    if machine == IMAGE_FILE_MACHINE_AMD64:
        return generateReturn(True, "AMD64 (64-bit x86)")
    return generateReturn(True, "Unknown architecture")
