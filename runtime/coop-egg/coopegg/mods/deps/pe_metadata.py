import struct

CODED = {
    'TypeDefOrRef': (2, [0x02, 0x01, 0x1B]),
    'HasConstant': (2, [0x04, 0x08, 0x17]),
    'HasCustomAttribute': (5, [0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x00, 0x0E, 0x17, 0x14, 0x11, 0x1A, 0x1B, 0x20, 0x23, 0x26, 0x27, 0x28, 0x2A, 0x2C, 0x2B]),
    'CustomAttributeType': (3, [None, None, 0x06, 0x0A, None]),
    'HasFieldMarshal': (1, [0x04, 0x08]),
    'HasDeclSecurity': (2, [0x02, 0x06, 0x20]),
    'MemberRefParent': (3, [0x02, 0x01, 0x1A, 0x06, 0x1B]),
    'HasSemantics': (1, [0x14, 0x17]),
    'MethodDefOrRef': (1, [0x06, 0x0A]),
    'MemberForwarded': (1, [0x04, 0x06]),
    'ResolutionScope': (2, [0x00, 0x1A, 0x23, 0x01]),
}

ROWS = {
    0x00: [2, 'S', 'G', 'G', 'G'],
    0x01: ['c:ResolutionScope', 'S', 'S'],
    0x02: [4, 'S', 'S', 'c:TypeDefOrRef', 't:0x04', 't:0x06'],
    0x03: ['t:0x04'],
    0x04: [2, 'S', 'B'],
    0x05: ['t:0x06'],
    0x06: [4, 2, 2, 'S', 'B', 't:0x08'],
    0x07: ['t:0x08'],
    0x08: [2, 2, 'S'],
    0x09: ['t:0x02', 'c:TypeDefOrRef'],
    0x0A: ['c:MemberRefParent', 'S', 'B'],
    0x0B: [2, 'c:HasConstant', 'B'],
    0x0C: ['c:HasCustomAttribute', 'c:CustomAttributeType', 'B'],
    0x0D: ['c:HasFieldMarshal', 'B'],
    0x0E: [2, 'c:HasDeclSecurity', 'B'],
    0x0F: [2, 4, 't:0x02'],
    0x10: [4, 't:0x04'],
    0x11: ['B'],
    0x12: ['t:0x02', 't:0x14'],
    0x13: ['t:0x14'],
    0x14: [2, 'S', 'c:TypeDefOrRef'],
    0x15: ['t:0x02', 't:0x17'],
    0x16: ['t:0x17'],
    0x17: [2, 'S', 'B'],
    0x18: [2, 't:0x06', 'c:HasSemantics'],
    0x19: ['t:0x02', 'c:MethodDefOrRef', 'c:MethodDefOrRef'],
    0x1A: ['S'],
    0x1B: ['B'],
    0x1C: [2, 'c:MemberForwarded', 'S', 't:0x1A'],
    0x1D: [4, 't:0x04'],
    0x1E: [4, 4],
    0x1F: [4],
    0x20: [4, 2, 2, 2, 2, 4, 'B', 'S', 'S'],
    0x21: [4],
    0x22: [4, 4, 4],
    0x23: [2, 2, 2, 2, 4, 'B', 'S', 'S', 'B'],
}


def read_metadata(path):
    try:
        with open(path, 'rb') as f:
            d = f.read()
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        if d[pe:pe + 4] != b'PE\0\0':
            return None
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        opt = pe + 24
        magic = struct.unpack_from('<H', d, opt)[0]
        dd = opt + (96 if magic == 0x10B else 112)
        cli_rva = struct.unpack_from('<I', d, dd + 14 * 8)[0]
        if not cli_rva:
            return None
        secs = []
        so = opt + optsz
        for i in range(nsec):
            vsz, va, rsz, raw = struct.unpack_from('<IIII', d, so + i * 40 + 8)
            secs.append((va, max(vsz, rsz), raw))

        def off(rva):
            for va, sz, raw in secs:
                if va <= rva < va + sz:
                    return rva - va + raw
            raise ValueError('rva')

        cli = off(cli_rva)
        md = off(struct.unpack_from('<I', d, cli + 8)[0])
        if d[md:md + 4] != b'BSJB':
            return None
        vlen = struct.unpack_from('<I', d, md + 12)[0]
        p = md + 16 + vlen + 2
        nstreams = struct.unpack_from('<H', d, p)[0]
        p += 2
        tab = None
        for _ in range(nstreams):
            so_, ss_ = struct.unpack_from('<II', d, p)
            p += 8
            end = d.index(b'\0', p)
            name = d[p:end].decode('ascii')
            p = (end + 4) & ~3
            if name in ('#~', '#-'):
                tab = md + so_
            elif name == '#Strings':
                strings = md + so_
        if tab is None:
            return None
        heaps = d[tab + 6]
        valid = struct.unpack_from('<Q', d, tab + 8)[0]
        p = tab + 24
        rows = {}
        for t in range(64):
            if valid >> t & 1:
                rows[t] = struct.unpack_from('<I', d, p)[0]
                p += 4
        hs = {'S': 4 if heaps & 1 else 2, 'G': 4 if heaps & 2 else 2, 'B': 4 if heaps & 4 else 2}

        def tsize(t):
            return 4 if rows.get(t, 0) >= 65536 else 2

        def csize(kind):
            bits, tables = CODED[kind]
            mx = max((rows.get(t, 0) for t in tables if t is not None), default=0)
            return 4 if mx >= (1 << (16 - bits)) else 2

        def width(col):
            if isinstance(col, int):
                return col
            if col in hs:
                return hs[col]
            if col.startswith('c:'):
                return csize(col[2:])
            return tsize(int(col[2:], 16))

        def cstr(idx):
            a = strings + idx
            return d[a:d.index(b'\0', a)].decode('utf-8', 'replace')

        version = None
        refs = []
        for t in range(0x24):
            if t not in rows:
                continue
            rowsz = sum(width(c) for c in ROWS[t])
            if t == 0x20:
                version = struct.unpack_from('<HHHH', d, p + 4)
            elif t == 0x23:
                for r in range(rows[t]):
                    q = p + r * rowsz + 12 + hs['B']
                    idx = int.from_bytes(d[q:q + hs['S']], 'little')
                    refs.append(cstr(idx))
            p += rows[t] * rowsz
        if version is None:
            return None
        return version, refs
    except Exception:
        return None


def assembly_version(path):
    md = read_metadata(path)
    return md[0] if md else None
