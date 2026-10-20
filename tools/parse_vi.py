import sys, struct

def u32(b, o): return struct.unpack(">I", b[o:o+4])[0]
def u16(b, o): return struct.unpack(">H", b[o:o+2])[0]

data = open(sys.argv[1], "rb").read()
print("file size:", len(data))

# 1) walk RSRC headers to the last one
pos = 0; last = -1
while last != pos:
    last = pos
    assert data[pos:pos+6] == b"RSRC\r\n", "missing RSRC magic at %d" % pos
    assert data[pos+8:pos+12] == b"LVIN", "not LVIN"
    assert data[pos+12:pos+16] == b"LBVW", "not LBVW"
    rsrc_off = u32(data, pos+16)
    rsrc_size = u32(data, pos+20)
    if rsrc_off > 0 and rsrc_size > 0:
        pos = rsrc_off
    else:
        break
RSRCOffset = pos
print("RSRCOffset:", RSRCOffset)

# 2) metadata right after the 24-byte header
p = RSRCOffset + 24
DataSetOffset = u32(data, p); p += 4
DataSetSize   = u32(data, p); p += 4
p += 12  # INT1,INT2,INT3
BlockInfoOffset = RSRCOffset + u32(data, p); p += 4
BlockInfoSize   = u32(data, p); p += 4
print("DataSetOffset:", DataSetOffset, "BlockInfoOffset:", BlockInfoOffset)

# 3) block table
cnt = u32(data, BlockInfoOffset) + 1
blocks = {}
q = BlockInfoOffset + 4
entries = []
for i in range(cnt):
    name = data[q:q+4].decode("latin1"); q += 4
    bcount = u32(data, q) + 1; q += 4
    infooff = BlockInfoOffset + u32(data, q); q += 4
    entries.append((name, bcount, infooff))
for name, bcount, infooff in entries:
    boff = DataSetOffset + u32(data, infooff + 12)  # after INT1,INT2,INT3
    blocks[name] = boff
print("blocks:", ", ".join(blocks.keys()))

# 4) BDPW
if "BDPW" not in blocks:
    print("\nNO BDPW block -> file is not password protected (or <5.0).")
    sys.exit(0)
boff = blocks["BDPW"]
size = u32(data, boff)            # 4-byte size prefix
content = data[boff+4: boff+4+size]
print("\nBDPW raw size:", size)
pw_md5 = content[0:16]
h1     = content[16:32]
h2     = content[32:48]
print("password_md5 :", pw_md5.hex())
print("hash_1       :", h1.hex())
print("hash_2       :", h2.hex() if len(content) >= 48 else "(none)")

# also pull LVSR library password if present
if "LVSR" in blocks:
    bo = blocks["LVSR"]; sz = u32(data, bo); c = data[bo+4:bo+4+sz]
    if len(c) >= 112:
        libpw = c[96:112]
        print("LVSR libpassword md5:", libpw.hex())
