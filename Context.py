#!/usr/bin/python3
'''
Manages the testing context -- e.g. how much memory we have, keeping track of PTEs that have already been created, etc.
'''

import random
from typing import List, Tuple, Union, Dict
from collections import defaultdict
import json5
import json
from sty import fg, bg, ef, RgbBg, rs

from simulator_errors import Errors
from utils import safe_to_bin, safe_to_hex, rsetattr, rgetattr, addr_to_memsize, num_hex_digits
from typeutils import resolve_flag, resolve_int
from core_types import PA, PTE, SATP, VA
from constants import PT_LEVEL_MAP, MAX_PA_MAP, MODE_PAGESIZE_LEVEL_MAP, PA_BITS, PAGESIZE_INT_MAP
from Translator import TranslationWalk, InvalidTranslationWalk

from ConstraintResolver import ConstraintResolver

NullableInt = Union[int, None]

bg.set_style('orange', RgbBg(255, 150, 50))

PTE_REUSE_MAX_ATTEMPTS = 5
ADD_CASE_MAX_ATTEMPTS = 5


class Context:
    '''
    Hold our data, and make special & probabilistic test cases
    '''
    def random_address(self):
        return random.randint(self.lower_bound, self.memory_size - 1)

    def valid_address(self, value):
        return value < self.memory_size

    def num_ptes(self, pagesize: str) -> int:
        ''' Return the number of PTES for a walk with the given page size '''
        return self.levels - MODE_PAGESIZE_LEVEL_MAP[self.mode][pagesize]

    def _format_va(self, va_addr: int, colorterm=True):
        if va_addr is None:
            return '***'
        va_digits = num_hex_digits(self.mode)
        va_str = f'{va_addr:#0{va_digits}x}'
        if colorterm and self.va_reference_counter[va_addr] > 1:
            return fg.red + va_str + fg.rs
        return va_str

    def _format_pa(self, pa_addr: int, colorterm=True):
        if pa_addr is None:
            return '***'
        pa_digits = num_hex_digits(PA_BITS[self.mode])
        pa_str = f'{pa_addr:#0{pa_digits}x}'
        if colorterm and self.reference_counter[pa_addr] > 1:
            return fg.red + pa_str + fg.rs
        return pa_str

    def _tw_ministring_err(self, walk: InvalidTranslationWalk, color=True) -> str:
        ppn_width = num_hex_digits(walk.satp.ppn_width)
        # pa_str = self._format_pa(walk.pa.data(), color)
        va_str = self._format_va(walk.va.data(), color) + fg.black
        # if color and walk.pa.data() == walk.va.data(): # Color PA = VA blue bg
        #     pa_str = bg.cyan + pa_str + bg.rs
        #     va_str = bg.cyan + va_str + bg.rs
        pte_entries = ' '.join([self._format_pa(x.address, color) for x in walk.ptes])
        if walk.ptes[-1].get_ppn() is None:
            final_ppn = '???'
        else:
            final_ppn = f'{walk.ptes[-1].get_ppn():#0{ppn_width}x}'
        pte_str = f'=>{pte_entries} {final_ppn}'
        err = fg.red + f' INVALID: {walk.error_type}  ' + fg.black
        base = f'SATP: {walk.satp.ppn:#0{ppn_width}x} VA: {va_str} -> [{pte_str}] {err}'
        # return f'{bg.orange} + {fg.black} + {base} + {fg.rs} + {bg.rs}'
        return bg.orange + fg.black + base + fg.rs + bg.rs


    def _tw_ministring(self, walk: Union[TranslationWalk, InvalidTranslationWalk], color=True) -> str:
        ''' Return a compact one-line representation of the walk '''
        # satp_ppn_digits = num_to44 if walk.mode != 32 else 22
        if type(walk) == InvalidTranslationWalk:
            return self._tw_ministring_err(walk, color)
        ppn_width = num_hex_digits(walk.satp.ppn_width)
        pa_str = self._format_pa(walk.pa.data(), color)
        va_str = self._format_va(walk.va.data(), color)
        if color and walk.pa.data() == walk.va.data(): # Color PA = VA blue bg
            pa_str = bg.cyan + pa_str + bg.rs
            va_str = bg.cyan + va_str + bg.rs
        pte_entries = ' '.join([self._format_pa(x.address, color) for x in walk.ptes])
        final_ppn = f'{walk.ptes[-1].get_ppn():#0{ppn_width}x}'
        pte_str = f'=>{pte_entries} {final_ppn}'
        base = f'SATP: {walk.satp.ppn:#0{ppn_width}x} VA: {va_str} -> [{pte_str}] -> {pa_str}'
        return base

    def __init__(self, memory_size: Union[int, None], mode: int, lower_bound: int = 0, pte_min: int = 0, pte_max: int = None, global_satp: SATP = None):
        ''' Initialize a ContextManager.
        params:
        size of memory (= the max physical address allowed in the simulation + 1)
        mode = 32 / 39 / 48.
        pte_min and pte_max (int, bounds the PTE areas)
        global_satp = default SATP, will randomize if None 
        '''
        # TODO: add stuff to classes for bounded randomness issues.
        self.memory_size = memory_size or MAX_PA_MAP[mode]  # 0 is not supported here (duh)
        self.lower_bound = lower_bound
        self.mode = mode
        self.address_table = {
        }  # we'll use this to keep track of PTEs & PAs that have already been allocated and their physical addresses
        self.vas = {}
        self.pas = {}
        self.ptes: Dict[int, PTE] = {}
        # self.leaves = {}
        self.walks: List[TranslationWalk] = []
        self.levels = PT_LEVEL_MAP[mode]
        self.satps: List[SATP] = []
        self.reference_counter = defaultdict(int)
        self.va_reference_counter = defaultdict(int)
        self.pte_min = pte_min
        self.pte_max = pte_max or self.memory_size
        self.CR = ConstraintResolver(mode=mode, memory_size=self.memory_size, lower_bound=self.lower_bound, pte_min=pte_min, pte_max=pte_max)
        
        # Create a default SATP if not past parametrically. To quote RISC-V docs: This register holds the physical page number (PPN)
        # of the root page table, i.e., its supervisor physical address divided by 4 KiB. Equivalent to >> (12 = PAGESIZE)
        self.global_satp = global_satp or SATP(self.mode, asid=0, ppn=(self.CR._random_pte_address() // 4096))


    def add_walk(self, pagesize: str, va: VA, pa: PA, ptes: List[PTE], satp: SATP):
        '''
        Add a translation walk to the context.
        Meant for when it's been specced out already.
        Registers the relevant components in all the relevant lookup tables.
        '''
        walk = TranslationWalk(self.mode, pagesize, satp, va, pa, ptes)
        walk.resolve(CR=self.CR, pte_hashmap=self.ptes)
        self.vas[va.data()] = va
        self.address_table[pa.data()] = pa
        self.pas[pa.data()] = pa
        self.satps.append(satp)
        for pte in ptes:
            self.address_table[pte.address] = pte
            self.ptes[pte.address] = pte
            self.reference_counter[pte.address] += 1
        # The last one is a leaf, mark that
        # self.leaves[pte.address] = pte
        self.walks.append(walk)
        self.reference_counter[pa.data()] += 1
        self.va_reference_counter[va.data()] += 1
    
    def add_invalid_walk(self, pagesize: str, va: VA, pa: PA, ptes: List[PTE], satp: SATP):
        '''
        Add a translation walk to the context.
        Meant for when it's been specced out already.
        Registers the relevant components in all the relevant lookup tables.
        '''
        walk = InvalidTranslationWalk(self.mode, pagesize, satp, va, pa, ptes)
        walk.resolve(CR=self.CR, pte_hashmap=self.ptes)
        if va.data():
            self.vas[va.data()] = va
            self.va_reference_counter[va.data()] += 1
        # self.address_table[pa.data()] = pa
        # self.pas[pa.data()] = pa
        self.satps.append(satp)
        for pte in ptes:
            if pte.address:
                # may need more checks in terms of marking things
                self.address_table[pte.address] = pte 
                self.ptes[pte.address] = pte
                self.reference_counter[pte.address] += 1
        # The last one is a leaf, mark that
        # self.leaves[pte.address] = pte
        self.walks.append(walk)
        # self.reference_counter[pa.data()] += 1

    def add_test_case(self, same_va_pa: float = 0, reuse_pte: float = 0, aliasing: float = 0, pagesize='4K', va=None, pa=None, **kwargs):
        '''
        Add a test case, with probabilistic usage of 'Testing Knowledge' cases.
        Made in a way that in the future passing JSON into it will be easy. (Through the kwargs)
        Probabilities from 0 to 1 (float).

        TODO: Clean this up a bit. Not much that can be eliminated, but stuff should be able to be moved around and parcelled out.
        '''

        # Work out our flags
        same_va_pa: int = resolve_flag(same_va_pa)
        aliasing: int = resolve_flag(aliasing)
        reuse_pte: int = resolve_flag(reuse_pte)

        # Change (Jun26) -- clean up the SATP usage.
        # Reuse should no longer be necessary since it's the default
        satp_data = kwargs.get('satp', {})
        if type(satp_data) == int:
            satp_data = { 'ppn' : satp_data }

        if ppn := kwargs.get('satp.ppn'):
            satp_data['ppn'] = ppn

        if not satp_data:
            satp = self.global_satp
        else:
            ppn = satp_data.get('ppn')
            asid = kwargs.get('satp.asid') or satp_data.get('asid') or 0
            satp = SATP(mode=self.mode, asid=asid, ppn=ppn)        


        # Step one: create and load everything from the test case
        if type(pa) == dict:
            _pa = PA(mode=self.mode)
            _pa.offset = pa.get('offset') # unpack reflexive
            _pa.ppn = pa.get('ppn') # unpack reflexive
            pa = _pa
        if type(va) == dict:
            _va = VA(mode=self.mode)
            _va.offset = va.get('offset')

            # VA VPN causes potential issues with array copy when defined. Adjusting for that here
            _va.vpn = va.get('vpn', []).copy()
            va = _va

        if (type(pagesize) == list):
            pagesize = random.choice(pagesize)
        
        if type(pa) == PA:
            pass
        elif aliasing:  # reuse an existing PA in the system
            # -- can cause issues when used with PTE reuse, so that gets a special treatment
            pa_addr = random.sample(self.pas.keys(), 1)[0]
            pa = self.pas[pa_addr]
        elif pa in self.pas.keys():
            pa = self.pas[pa]
        else:
            pa = PA(mode=self.mode, data=pa)

        if type(va) == VA:
            pass
        else:
            if same_va_pa and pa.data():
                va = pa.data()
            if va in self.vas.keys():
                va = self.vas[va]
            else:
                va = VA(mode=self.mode, data=va)

        if same_va_pa:  # same VA and PA
            if pa.data() and va.data():
                pass
            elif pa.data():
                va.set(pa.data())
            else: # TODO: bounds checking!
                va.set(self.random_address())
                pa.set(va.data())
        


        ptes = [None] * self.num_ptes(pagesize)
        if reuse_pte:  # for now: not allowed with specifying PTE data
            
            # Two issues here:
            # (1) it has to be handled as a leaf or non-leaf accordingly
            # (2) it needs to be reachable through the SATP if it's the first level
            for i in range(PTE_REUSE_MAX_ATTEMPTS):
                random_walk = random.choice(self.walks)
                rwalk_ptes = random_walk.ptes


                max_pte_walk = len(rwalk_ptes) - 1
                leaf_index = self.num_ptes(pagesize) - 1
                selection_index = random.randint(0, max_pte_walk)

                if selection_index == max_pte_walk:
                    if max_pte_walk == leaf_index:
                        placed_location_index = leaf_index
                        if aliasing:
                            pa_addr = random_walk.pa.data() # fallback for picking a leaf
                            pa = self.pas[pa_addr]
                    else:
                        continue
                elif leaf_index == 0:
                    continue
                else:
                    placed_location_index = random.randint(0, leaf_index - 1)

                random_pte_addr = rwalk_ptes[selection_index].address
                ptes[placed_location_index] = self.ptes[random_pte_addr]
                break
            else:
                raise Errors.InvalidConstraints('Could not find a suitable PTE for reuse!')
        
        elif kwargs.get('ptes'):
            for i, pte_attrs in enumerate(kwargs.get('ptes')):
                address = resolve_int(pte_attrs.get('address'))
                if address in self.ptes.keys(): # check to make sure that we reuse, and don't double define
                    ptes[i] = self.ptes[address]
                else:
                    ptes[i] = PTE(mode=self.mode)
                    ptes[i].address = address
                    if ppns := pte_attrs.get('ppns'):
                        ptes[i].ppn = ppns

                flags = pte_attrs.get('attributes', {})

                for flag, value in flags.items():
                    setattr(ptes[i].attributes, flag, resolve_flag(value))

        # inialize all remaining undefined PTEs
        for i in range(len(ptes)):
            if ptes[i] == None:
                ptes[i] = PTE(mode=self.mode)

        if errs := kwargs.get('errors'):
            use_errs = {}
            prob = errs.get('p')
            err = False
            if prob:
                if resolve_flag(prob): # Do a distribution choice
                    errtype = random.choices(errs.get('types'), errs.get('weights'), k=1)[0]
                    for error in ('mark_invalid', 'write_no_read', 'leaf_as_pointer', 'uncleared_superpage'):
                        use_errs[error] = 0
                    use_errs[errtype] = 1
            else:
                use_errs = errs
            # V = 0

            # TODO: flex locations of bad PTE
            if resolve_flag(use_errs.get('mark_invalid')):
                err = True
                ptes[-1].attributes.V = 0
            # W=1, R=0, on the leaf
            if resolve_flag(use_errs.get('write_no_read')):
                err = True
                ptes[-1].attributes.R = 0 
                ptes[-1].attributes.W = 1
            # Global mapping followed by G=0
            # if resolve_flag(use_errs.get('global_nonglobal')):
            #     err = True
            #     ptes[-2].attributes.G = 1 
            #     ptes[-1].attributes.G = 0
            # Leaf marked as pointer
            if resolve_flag(use_errs.get('leaf_as_pointer')):
                err = True
                ptes[-1].attributes.X = 0
                ptes[-1].attributes.W = 0
                ptes[-1].attributes.R = 0 
            # Superpage has data set
            if resolve_flag(use_errs.get('uncleared_superpage')):
                err = True
                ptes[-1].ppn[0] = random.randint(10, 200)
            
            if err:
                self.add_invalid_walk(pagesize, va, pa, ptes, satp)
            else:
                self.add_walk(pagesize, va, pa, ptes, satp)
        else:
            self.add_walk(pagesize, va, pa, ptes, satp)
        
    def dump(self, filename: str):
        ''' Export the full things to a JSON '''
        with open(filename, 'w') as f:
            json.dump(self, f, default=lambda x: x.__dict__)

    def jsonify(self) -> dict:
        ''' Return a minimal JSON friendly thingy'''
        return {
            'mode': self.mode,
            'lower_bound': self.lower_bound,
            'memory_size': self.memory_size,
            'pte_min': self.pte_min, 
            'pte_max': self.pte_max, 
            'global_satp': self.global_satp.jsonify(),
            'walks': [walk.jsonify() for walk in self.walks]
        }

    def jsonify_color(self) -> dict:
        return {
            'mode': self.mode,
            'lower_bound': self.lower_bound,
            'memory_size': self.memory_size,
            'pte_min': self.pte_min, 
            'pte_max': self.pte_max,
            'global_satp': self.global_satp.jsonify(),
            'walks': [walk.jsonify_color(self.va_reference_counter, self.reference_counter) for walk in self.walks]
        }

    def __repr__(self):
        return f'<ContextManager: Sv{self.mode}, Memory Bounds: {self.lower_bound:0x}-{self.memory_size:0x}>'

    def print_dump(self, full_dump=False):
        satp_digits = num_hex_digits(44 if self.mode != 32 else 22) + 2

        print('ContextManager Trace')
        print(
            f'Mode: {self.mode}, MemSize: {self.memory_size:#x} (={addr_to_memsize(self.memory_size)}). Max VA = {2**self.mode - 1:#0x}'
        )
        print()
        if full_dump:
            print('Virtual Addresses:')
            va_digits = num_hex_digits(self.mode) + 2  # account for the 0x taking up space
            for i, va_address in enumerate(self.vas.keys()):
                print(f'{i}\t{va_address:#0{va_digits}x}')
            print()

            print('Physical Addresses:')
            pa_digits = num_hex_digits(PA_BITS[self.mode]) + 2
            for i, pa_address in enumerate(self.pas.keys()):
                print(f'{i}\t{pa_address:#0{pa_digits}x}')
            print()

            print('PTEs:')
            for i, pte in enumerate(self.ptes.values()):
                print(f'{i}\t{pte.ministring()}')
            print()

            print('SATPs:')
            for i, satp in enumerate(self.satps):
                print(f'{i}\t{satp.ppn:#0{satp_digits}x}')
            print()

        print('Walks:')
        for i, walk in enumerate(self.walks):
            print(f'{i}\t{self._tw_ministring(walk)}')
        print()


def ContextFromJSON(json_data: Union[str, dict]) -> Context:
    ''' Load a JSON5 test config '''
    if type(json_data) == str:
        filename = json_data
        with open(filename) as f:
            params = json5.load(f)
    else:
        params = json_data

    satp_data = params.get('satp', {})
    if type(satp_data) == int:
        satp_data = { 'ppn' : satp_data }

    if 'satp.ppn' in params.keys():
        satp_data['ppn'] = params['satp.ppn']
    
    if not satp_data:
        global_satp = None
    else:
        global_satp = SATP(mode=params.get('mode'), asid=satp_data.get('asid'), ppn=satp_data['ppn'])
        # ppn = params.get('satp.ppn') or satp_data.get('ppn') or 0

    mgr = Context(params.get('memory_size'), params.get('mode'), params.get('lower_bound', 0), params.get('pte_min', 0), params.get('pte_max'), global_satp)

    test_cases = params.get('test_cases', [])


    for test_case in test_cases:
        # Handle the 'special' control

        indices = []
        special_args = {}

        if special := test_case.get('special'):
            indices = set(s.get('index') for s in special)
            for case in special:
                special_args[case.get('index')] = case

        if rg := test_case.get('page_range'): # Walrus
            # We do a  mapping of the first page address
            start = rg.get('start', mgr.lower_bound)
            end   = rg.get('end', mgr.memory_size)
            step  = rg.get('step', None)
            num_pages = rg.get('num_pages', None)
            
            current_addr = start
            n_iters = 0
            while current_addr < end and (num_pages is None or n_iters < num_pages):
                if n_iters in indices:
                    use_case = {**test_case, **special_args.get(n_iters, {})}
                else:
                    use_case = test_case
                for i in range(ADD_CASE_MAX_ATTEMPTS): # how many failures we will try before we give up
                    try:
                        mgr.add_test_case(**use_case, pa=current_addr)
                        break
                    except (Errors.SuperPageNotCleared, Errors.InvalidConstraints):
                        pass
                else:
                    raise Errors.InvalidConstraints(f"Couldn't satisfy constraints after {ADD_CASE_MAX_ATTEMPTS} tries (pg range)")
                current_addr += step or PAGESIZE_INT_MAP[mgr.walks[-1].pagesize]
                n_iters += 1

        else:
            for i in range(test_case.get('repeats', 1)):
                if i in indices:
                    use_case = {**test_case, **special_args.get(i, {})}
                else:
                    use_case = test_case
                
                for _ in range(ADD_CASE_MAX_ATTEMPTS):
                    try:
                        mgr.add_test_case(**use_case)
                        break
                    except (Errors.SuperPageNotCleared, Errors.InvalidConstraints):
                        pass
                else:
                    raise Errors.InvalidConstraints(f"Couldn't satisfy constraints after {ADD_CASE_MAX_ATTEMPTS} tries (main flow)")



    return mgr

def ContextFromJSON5(json5_data: str) -> Context:
    ''' Context from a JSON5 string '''
    data = json5.loads(json5_data)
    return ContextFromJSON(data)
