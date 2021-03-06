from typing import List, Tuple, Union

from utils import safe_to_bin, field_to_string, num_hex_digits, safe_to_hex
from constants import PA_BITS
import math
import random

from simulator_errors import Errors

DEFAULT_FORMAT = 'b'


class SATP:
    mode = 0
    asid = 0  # Not used currently
    ppn = None
    ppn_isEmpty = False

    def __init__(self, mode=32, asid=0, ppn_isEmpty=False, ppn=None, isLoad=False):
        if isLoad:
            return
        self.set(mode, asid, ppn_isEmpty, ppn)

    def set(self, mode, asid, ppn_isEmpty, ppn):
        self.mode = mode
        self.asid = asid
        self.ppn = ppn
        self.ppn_isEmpty = ppn_isEmpty

    @property
    def ppn_width(self):
        return 22 if self.mode == 32 else 44

    def jsonify(self):
        return {'mode': self.mode, 'asid': self.asid, 'ppn': self.ppn}

    def __str__(self):
        return self.__format__(DEFAULT_FORMAT)

    def __format__(self, format_code=DEFAULT_FORMAT):
        mode_flags = {32: 1, 39: 8, 48: 9}.get(self.mode, 0)

        width = 32 if self.mode == 32 else 64
        asid_width = 9 if self.mode == 32 else 16
        mode_str = 'M' if self.mode == 32 else 'Mode'
        ppn_str = field_to_string(self.ppn, self.ppn_width, format_code)
        ppn_hex = '???' if self.ppn is None else hex(self.ppn)

        top_str = f'|{mode_str}|{"ASID":^{asid_width}}|{"PPN":^{self.ppn_width}}|'
        main_str = f'|{mode_flags:b}|{self.asid:0{asid_width}b}|{ppn_str}|'

        return f'SATP: (PPN={ppn_hex})\n{top_str}\n{main_str}'


class PTE:
    class ATTRIBUTES:
        V = 1
        R = None
        W = None
        X = None
        U = None
        G = None
        A = None
        D = None
        RSW = 0  # hardwire to 0 for now

        defined = False

        def __init__(self):
            pass

        def set(self, attributes):
            self.defined = True
            self.V = attributes & 0x1
            self.R = (attributes >> 1) & 0x1
            self.W = (attributes >> 2) & 0x1
            self.X = (attributes >> 3) & 0x1
            self.U = (attributes >> 4) & 0x1
            self.G = (attributes >> 5) & 0x1
            self.A = (attributes >> 6) & 0x1
            self.D = (attributes >> 7) & 0x1
            self.RSW = (attributes >> 8) & 0x3

        @property
        def flags(self):
            return (self.D, self.A, self.G, self.U, self.X, self.W, self.R, self.V)

        def jsonify(self):
            return dict(zip(['RSW'] + list('DAGUXWRV'), [self.RSW] + list(self.flags)))  # maybe change RSW

        def __str__(self):
            s = safe_to_bin(self.RSW, 2)
            for field in self.flags:
                s += safe_to_bin(field, 1)
            return s

    mode = 0
    address = None
    ppn = [None, None, None, None]
    # attributes = ATTRIBUTES()
    isAddrEmpty = True
    isDataEmpty = True
    mode = 0
    errorMessage = ""
    level = 0

    @property
    def widths(self):
        if self.mode == 32:
            return [10, 12]
        elif self.mode == 39:
            return [9, 9, 17]
        elif self.mode == 48:
            return [9, 9, 9, 17]
        return []

    def __init__(self, level=0, mode=32, isLoad=False):
        if isLoad:
            return
        self.mode = mode
        self.level = level
        self.ppn = [None for i in self.widths if i]
        self.attributes = self.ATTRIBUTES()
        self.content_bits = 44 if mode != 32 else 22
        self.address_bits = 34 if mode == 32 else 56

    def broadcast_ppn(self, ppn: int, start_level=0):
        for i in range(start_level):
            self.ppn[i] = 0  # leaves are zeroed below the used portion of the ppn
        for i, width in enumerate(self.widths[start_level:], start=start_level):
            if not width:
                return
            self.ppn[i] = ppn & mask(width)
            ppn >>= width  # shift off the bits that've been assigned

    # New: make it simpler to find whether it is a leaf
    @property
    def leaf(self):
        return bool(self.attributes.X or self.attributes.W or self.attributes.R)

    def finalize(self):
        ''' Finalize the PTE flags with reasonable defaults. If there's stuff
         specified within a group (= XWR, AD), you need to specify the whole
         thing or accept zeros filled in as defaults '''

        if self.attributes.V is None:
            self.attributes.V = 1

        if self.attributes.X is None and self.attributes.W is None and self.attributes.R is None:
            xwr = random.choice([0b001, 0b011, 0b100, 0b101, 0b111])
            self.attributes.X = xwr >> 2
            self.attributes.W = (xwr >> 1) & 1
            self.attributes.R = xwr & 1

        if self.attributes.D is None and self.attributes.A is None and self.leaf:
            ad = random.choice([0b00, 0b10, 0b11])
            self.attributes.A = ad >> 1
            self.attributes.D = ad & 1

        self.attributes.RSW = self.attributes.RSW or 0
        self.attributes.D = self.attributes.D or 0
        self.attributes.A = self.attributes.A or 0
        self.attributes.G = self.attributes.G or 0
        self.attributes.U = self.attributes.U or 0
        self.attributes.X = self.attributes.X or 0
        self.attributes.W = self.attributes.W or 0
        self.attributes.R = self.attributes.R or 0
        self.attributes.V = self.attributes.V or 0

    def set_pointer(self):
        ''' Clear XWR (making this a pointer entry in the table). If they're set, raises an error '''
        ''' For non-leaf PTEs, the D, A, and U bits are reserved for future use and must be cleared by software for forward compatibility. '''
        if self.leaf:
            raise Errors.UnexpectedLeaf(f'PTE is a leaf and was used as a pointer')
        if self.attributes.U or self.attributes.D or self.attributes.A:
            raise Errors.InvalidDAU(f'Found DAU = {self.attributes.D}{self.attributes.A}{self.attributes.U}')
        self.attributes.X = 0
        self.attributes.W = 0
        self.attributes.R = 0
        self.attributes.D = 0
        self.attributes.A = 0
        self.attributes.U = 0

    def assert_pointer(self):
        if self.leaf:
            raise Errors.UnexpectedLeaf(f'PTE is a leaf and was used as a pointer')

    def assert_global(self, assertion: bool) -> bool:
        if self.attributes.G:
            return True
        elif assertion:
            raise Errors.NonGlobalAfterGlobal()
        return False

    def validate_leaf(self):
        if self.attributes.V == 0:
            raise Errors.PTEMarkedInvalid()
        elif self.attributes.R == 0 and self.attributes.X == 0 and self.attributes.W == 0:
            raise Errors.LeafMarkedAsPointer()
        elif self.attributes.R == 0 and self.attributes.W == 1:
            raise Errors.WriteNoReadError()

    def data(self):
        # return None  # TODO: handle attrs so this can go through
        pte = (self.attributes.V | (self.attributes.R << 1) | (self.attributes.W << 2) | (self.attributes.X << 3) |
               (self.attributes.U << 4) | (self.attributes.G << 5) | (self.attributes.A << 6) | (self.attributes.D << 7)
               | (self.attributes.RSW << 8))

        ppn = self.get_ppn()
        if ppn is None:
            return None
        return (ppn << 10) | pte

    def get_ppn(self):
        if None in self.ppn:
            return None
        accumulated = 0
        for width, ppn in zip(reversed(self.widths), reversed(self.ppn)):
            accumulated |= ppn
            accumulated <<= width

        accumulated >>= width
        return accumulated

        # if self.mode == 32:
        #     return (self.ppn[1] << 10) | self.ppn[0]
        # elif self.mode == 39:
        #     return (self.ppn[2] << 18) | (self.ppn[1] << 9) | self.ppn[0]
        # elif self.mode == 48:
        #     return (self.ppn[3] << 27) | (self.ppn[2] << 18) | (self.ppn[1] << 9) | self.ppn[0]

    def __str__(self):
        return self.__format__(DEFAULT_FORMAT)

    def jsonify(self):
        return {
            'address': self.address,
            'ppn': self.ppn,
            'contents': self.get_ppn(),
            'data': self.data(),
            'attributes': self.attributes.jsonify()
        }

    def __format__(self, format_code=DEFAULT_FORMAT):
        data_str = f'{self.data():x}' if self.data() != None else '???'
        ppn_str = f'0x{self.get_ppn():x}' if self.get_ppn() != None else '???'
        addr_str = f'{self.address:x}' if self.address != None else '???'
        header = f'PTE: {data_str} ({ppn_str}) @{addr_str}'
        display_line = f'|RSDAGUXWRV|'
        val_line = f'|{self.attributes}|'
        for i, (width, value) in enumerate(zip(self.widths, self.ppn)):
            name = f'PPN{i}'
            display_line = f'|{name:^{width}}{display_line}'
            vs = field_to_string(value, width, format_code)
            val_line = f'|{vs}{val_line}'

        return f'{header}\n{display_line}\n{val_line}'

    def ministring(self):
        ppn_digits = num_hex_digits(self.content_bits)
        addr_digits = num_hex_digits(self.address_bits)
        return f'@{safe_to_hex(self.address, addr_digits)} -> {safe_to_hex(self.get_ppn(), ppn_digits)} ({self.attributes})'


class VA:
    vpn = []
    offset = None
    mode = 0
    # isEmpty = True
    errorMessage = ""

    def __init__(self, data=None, mode=32, isLoad=False):
        if isLoad:
            return
        self.mode = mode
        if data == None:
            # self.isEmpty = True
            self.vpn = [None for i in self.widths if i]
        else:
            # self.isEmpty = False
            self.set(data)

    def set(self, data=0xFFFFFFFFFFFF):
        self.offset = data & 0xFFF
        # self.mode = mode
        self.vpn = []

        if self.mode == 32:
            self.vpn.append((data >> 12) & 0x3FF)
            self.vpn.append((data >> 22) & 0x3FF)
        if self.mode == 39:
            self.vpn.append((data >> 12) & 0x1FF)
            self.vpn.append((data >> 21) & 0x1FF)
            self.vpn.append((data >> 30) & 0x1FF)
        if self.mode == 48:
            self.vpn.append((data >> 12) & 0x1FF)
            self.vpn.append((data >> 21) & 0x1FF)
            self.vpn.append((data >> 30) & 0x1FF)
            self.vpn.append((data >> 39) & 0x1FF)
        # self.isEmpty = False

    def get_big_page(self, level=3):
        big_offset = self.offset
        width = 0
        for i in range(level):
            width += self.widths[i]
            segment = self.vpn[i]
            big_offset |= segment << width
        return big_offset

    def set_big_page(self, level, data):
        self.offset = data & mask(12)
        data >>= 12
        for i in range(level):
            self.vpn[i] = data & mask(self.widths[i])
            data >>= self.widths[i]  # shift off the bits that've been assigned

    def data(self) -> Union[None, int]:
        va = None
        if None not in self.vpn and self.offset != None:
            va = self.offset
            if self.mode == 32:
                va |= (self.vpn[0] << 12) | (self.vpn[1] << 22)
            if self.mode == 39:
                va |= (self.vpn[0] << 12) | (self.vpn[1] << 21) | (self.vpn[2] << 30)
            if self.mode == 48:
                va |= (self.vpn[0] << 12) | (self.vpn[1] << 21) | (self.vpn[2] << 30) | (self.vpn[3] << 39)
        return va

    @property
    def widths(self):
        if self.mode == 32:
            return [10, 10, None, None]
        elif self.mode == 39:
            return [9, 9, 9, None]
        elif self.mode == 48:
            return [9, 9, 9, 9]
        return [None, None, None, None]

    def randomize(self):
        ''' Set random values to unset fields of the VA '''
        for i, width in enumerate(self.widths):
            if self.vpn[i] is None:
                self.vpn[i] = random.getrandbits(width)
        if self.offset is None:
            self.offset = random.getrandbits(12)

    def __str__(self):
        return self.__format__()

    def __format__(self, format_code=DEFAULT_FORMAT):
        data_str = f'{self.data():x}' if self.data() != None else '???'
        header = f'VA: {data_str}'
        display_line = f'|{"Offset":^12}|'
        val_line = f'|{field_to_string(self.offset, 12, format_code)}|'
        for i, (width, value) in enumerate(zip(self.widths, self.vpn)):
            name = f'VPN{i}'
            display_line = f'|{name:^{width}}{display_line}'
            vs = field_to_string(value, width, format_code)
            val_line = f'|{vs}{val_line}'

        return f'{header}\n{display_line}\n{val_line}'

    def jsonify(self):
        return {'data': self.data(), 'offset': self.offset, 'vpn': self.vpn}


class PA:
    ppn = []
    offset = None
    mode = 0

    def __init__(self, data=None, mode=32, isLoad=False):
        if isLoad:
            return
        self.mode = mode
        if data:
            self.set(data)
            # self.isEmpty = False
        else:
            self.ppn = [None for i in self.widths if i != None]

    def set(self, data=0x12345678):
        self.ppn = []
        self.offset = data & 0xFFF
        if self.mode == 32:
            self.ppn.append((data >> 12) & 0x3FF)
            self.ppn.append((data >> 22) & 0x3FF)
        if self.mode == 39:
            self.ppn.append((data >> 12) & 0x1FF)
            self.ppn.append((data >> 21) & 0x1FF)
            self.ppn.append((data >> 30) & 0x1FF)
        if self.mode == 48:
            self.ppn.append((data >> 12) & 0x1FF)
            self.ppn.append((data >> 21) & 0x1FF)
            self.ppn.append((data >> 30) & 0x1FF)
            self.ppn.append((data >> 39) & 0x1FFFF)
        # self.isEmpty = False

    def data(self):
        pa = None
        if None not in self.ppn and len(self.ppn):
            pa = self.offset
            if self.mode == 32:
                pa |= (self.ppn[0] << 12) | (self.ppn[1] << 22)
            if self.mode == 39:
                pa |= (self.ppn[0] << 12) | (self.ppn[1] << 21) | (self.ppn[2] << 30)
            if self.mode == 48:
                pa |= (self.ppn[0] << 12) | (self.ppn[1] << 21) | (self.ppn[2] << 30) | (self.ppn[3] << 39)
        return pa

    @property
    def widths(self) -> List[int]:
        if self.mode == 32:
            return [10, 12, None, None]
        elif self.mode == 39:
            return [9, 9, 17, None]
        elif self.mode == 48:
            return [9, 9, 9, 17]
        return [None, None, None, None]

    def __str__(self):
        return self.__format__(DEFAULT_FORMAT)

    def jsonify(self):
        return {'data': self.data(), 'ppn': self.ppn, 'offset': self.offset}

    def __format__(self, format_code=DEFAULT_FORMAT):
        data_str = f'{self.data():x}' if self.data() != None else '???'
        header = f'PA: {data_str}'
        display_line = f'|{"Offset":^12}|'
        val_line = f'|{field_to_string(self.offset, 12, format_code)}|'
        for i, (width, value) in enumerate(zip(self.widths, self.ppn)):
            name = f'PPN{i}'
            display_line = f'|{name:^{width}}{display_line}'
            vs = field_to_string(value, width, format_code)
            val_line = f'|{vs}{val_line}'

        return f'{header}\n{display_line}\n{val_line}'
