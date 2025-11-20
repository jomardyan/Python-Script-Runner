#!/usr/bin/env python3
# (C) Hayk Jomardyan - iCredit 2025
import sys
import os
CRC_TABLE = [
    0, 1996959894, -301047508, -1727442502, 124634137, 1886057615, -379345611,
    -1637575261, 249268274, 2044508324, -522852066, -1747789432, 162941995,
    2125561021, -407360249, -1866523247, 498536548, 1789927666, -205950648,
    -2067906082, 450548861, 1843258603, -187386543, -2083289657, 325883990,
    1684777152, -43845254, -1973040660, 335633487, 1661365465, -99664541,
    -1928851979, 997073096, 1281953886, -715111964, -1570279054, 1006888145,
    1258607687, -770865667, -1526024853, 901097722, 1119000684, -608450090,
    -1396901568, 853044451, 1172266101, -589951537, -1412350631, 651767980,
    1373503546, -925412992, -1076862698, 565507253, 1454621731, -809855591,
    -1195530993, 671266974, 1594198024, -972236366, -1324619484, 795835527,
    1483230225, -1050600021, -1234817731, 1994146192, 31158534, -1731059524,
    -271249366, 1907459465, 112637215, -1614814043, -390540237, 2013776290,
    251722036, -1777751922, -519137256, 2137656763, 141376813, -1855689577,
    -429695999, 1802195444, 476864866, -2056965928, -228458418, 1812370925,
    453092731, -2113342271, -183516073, 1706088902, 314042704, -1950435094,
    -54949764, 1658658271, 366619977, -1932296973, -69972891, 1303535960,
    984961486, -1547960204, -725929758, 1256170817, 1037604311, -1529756563,
    -740887301, 1131014506, 879679996, -1385723834, -631195440, 1141124467,
    855842277, -1442165665, -586318647, 1342533948, 654459306, -1106571248,
    -921952122, 1466479909, 544179635, -1184443383, -832445281, 1591671054,
    702138776, -1328506846, -942167884, 1504918807, 783551873, -1212326853,
    -1061524307, -306674912, -1698712650, 62317068, 1957810842, -355121351,
    -1647151185, 81470997, 1943803523, -480048366, -1805370492, 225274430,
    2053790376, -468791541, -1828061283, 167816743, 2097651377, -267414716,
    -2029476910, 503444072, 1762050814, -144550051, -2140837941, 426522225,
    1852507879, -19653770, -1982649376, 282753626, 1742555852, -105259153,
    -1900089351, 397917763, 1622183637, -690576408, -1580100738, 953729732,
    1340076626, -776247311, -1497606297, 1068828381, 1219638859, -670225446,
    -1358292148, 906185462, 1090812512, -547295293, -1469587627, 829329135,
    1181335161, -882789492, -1134132454, 628085408, 1382605366, -871598187,
    -1156888829, 570562233, 1426400815, -977650754, -1296233688, 733239954,
    1555261956, -1026031705, -1244606671, 752459403, 1541320221, -1687895376,
    -328994266, 1969922972, 40735498, -1677130071, -351390145, 1913087877,
    83908371, -1782625662, -491226604, 2075208622, 213261112, -1831694693,
    -438977011, 2094854071, 198958881, -2032938284, -237706686, 1759359992,
    534414190, -2118248755, -155638181, 1873836001, 414664567, -2012718362,
    -15766928, 1711684554, 285281116, -1889165569, -127750551, 1634467795,
    376229701, -1609899400, -686959890, 1308918612, 956543938, -1486412191,
    -799009033, 1231636301, 1047427035, -1362007478, -640263460, 1088359270,
    936918000, -1447252397, -558129467, 1202900863, 817233897, -1111625188,
    -893730166, 1404277552, 615818150, -1160759803, -841546093, 1423857449,
    601450431, -1285129682, -1000256840, 1567103746, 711928724, -1274298825,
    -1022587231, 1510334235, 755167117
]

crc = 0xFFFFFFFF

def init_crc():
    """Initialize the CRC value."""
    global crc
    crc = 0xFFFFFFFF

def solve_crc(data: bytes) -> int:
    """Update the global CRC value with the given bytes.
    
    This function mimics the C loop:
       for each byte b:
         crc = CRC_TABLE[(crc ^ b) & 0xff] ^ (crc >> 8)
    """
    global crc
    for b in data:
        index = (crc ^ b) & 0xFF
        crc = (CRC_TABLE[index] ^ (crc >> 8)) & 0xFFFFFFFF
    return crc

def set_crc(new_crc: int) -> int:
    """Set the global CRC value to new_crc, returning the old value."""
    global crc
    old = crc
    crc = new_crc
    return old

def print_header():

    print()  # newline
    print("CRC iCredit  - Program do obliczania sumy kontrolnej CRC32")
    print("-----------------------------------------------------")

def print_usage():
    """Print a usage message when the wrong number of arguments is supplied."""
    print()
    print("Nieodpowiednia liczba argumentow")
    print("Argumentem programu jest nazwa pliku (.FWD)")

def process_file(file_path: str) -> str:
    """
    Process the FWD file:
      1. Read the file using encoding iso8859-2.
      2. Remove the trailing newline (CR LF or LF) if present.
      3. Calculate the CRC32 checksum using the provided algorithm.
      4. Append the file with the calculated CRC32 value (in lowercase hex, without '0x' prefix).
      5. Save the file.
    Returns the CRC32 checksum as a string.
    """
    # Read file in text mode with iso8859-2 encoding, preserving newlines. (according BIK rules)
    with open(file_path, 'r', encoding='iso8859-2', newline='') as f:
        content = f.read()
    
    # Remove the trailing newline if it exists.
    if content.endswith("\r\n"):
        content = content[:-2]
    elif content.endswith("\n"):
        content = content[:-1]
    
    # Encode content to bytes using iso8859-2 for CRC calculation.
    data_bytes = content.encode('iso8859-2')
    
    # Calculate CRC32 checksum using the provided algorithm.
    init_crc()
    solve_crc(data_bytes)
    
    # Format the checksum as 8-digit lowercase hexadecimal (without 0x prefix).
    crc_str = "{:08x}".format(crc)
    
    # Append the checksum to the content.
    new_content = content + crc_str
    
    # Save the updated content back to the file using iso8859-2 encoding.
    with open(file_path, 'w', encoding='iso8859-2', newline='') as f:
        f.write(new_content)
    
    return crc_str

def run_gui():
    """Run the GUI interface to select a FWD file and display the CRC32 checksum."""
    import tkinter as tk
    from tkinter import filedialog, messagebox
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window.
    root.attributes("-topmost", True)
    
    # Open file selection dialog filtering for .FWD files.
    file_path = filedialog.askopenfilename(
        title="Wybierz plik FWD",
        filetypes=[("Pliki FWD", "*.FWD"), ("Pliki FWD", "*.fwd"), ("Wszystkie pliki", "*.*")]
    )
    
    if not file_path:
        messagebox.showerror("Blad", "Nie wybrano pliku!", parent=root)
        sys.exit(-1)
    
    try:
        crc_str = process_file(file_path)
        messagebox.showinfo("CRC32", "CRC32 pliku = {}".format(crc_str),parent=root,)
    except Exception as e:
        messagebox.showerror("Blad", "Wystapil blad:\n{}".format(e), parent=root)
        sys.exit(-1)

def main():
    print_header()
    
    # Determine if running in CLI or GUI mode.
    if len(sys.argv) == 2:
        # CLI mode: file path provided as command-line argument.
        filename = sys.argv[1]
        print("Nazwa pliku:", filename)
        if not os.path.isfile(filename):
            print("Blad: Plik nie istnieje:", filename)
            sys.exit(-1)
        try:
            crc_str = process_file(filename)
            print("\nCRC32 pliku = {}".format(crc_str))
        except Exception as e:
            print("Wystapil blad:", e)
            sys.exit(-1)
    elif len(sys.argv) == 1:
        # No command-line argument: launch GUI.
        run_gui()
    else:
        print_usage()
        sys.exit(-1)

if __name__ == '__main__':
    main()
