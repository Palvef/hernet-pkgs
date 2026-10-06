#!/usr/bin/env python3
"""Fail closed: patch precisely one instruction within the ELF function symbol."""
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

def patch(path):
    data=bytearray(path.read_bytes())
    if data[:6] != b'\x7fELF\x02\x01': raise ValueError('Requires ELF64 little-endian')
    symbols=subprocess.check_output(['nm','-S','--defined-only',str(path)],text=True)
    candidates=[line.split() for line in symbols.splitlines() if line.split()[-1:] == ['ngx_http_geoip2_init']]
    if len(candidates)!=1: raise ValueError('Missing or ambiguous init symbol')
    address,size=int(candidates[0][0],16),int(candidates[0][1],16)
    shoff=struct.unpack_from('<Q',data,40)[0]
    shentsize,shnum=struct.unpack_from('<HH',data,58)
    offsets=[]
    for i in range(shnum):
        _,section_type,flags,addr,offset,length=struct.unpack_from('<IIQQQQ',data,shoff+i*shentsize)
        if section_type == 1 and flags & 6 == 6 and addr <= address and address+size <= addr+length and offset+length <= len(data):
            offsets.append(offset+address-addr)
    if len(offsets)!=1: raise ValueError('Cannot map function to unique file section')
    start=offsets[0]
    old=bytes.fromhex('48 81 c7 78 02 00 00'); new=bytes.fromhex('48 81 c7 e8 00 00 00')
    body=data[start:start+size]
    if body.count(old)!=1 or new in body: raise ValueError('Expected exactly one unpatched phase instruction')
    at=start+body.index(old)
    before=hashlib.sha256(data).hexdigest()
    data[at:at+len(old)]=new
    path.write_bytes(data)
    disasm=subprocess.check_output(['objdump','-d','--disassemble=ngx_http_geoip2_init',str(path)],text=True)
    if '48 81 c7 e8 00 00 00' not in disasm: raise ValueError('Post-patch disassembly mismatch')
    return dict(symbol='ngx_http_geoip2_init',virtual_address=hex(address+at-start),file_offset=hex(at),before_sha256=before,after_sha256=hashlib.sha256(data).hexdigest(),disassembly=disasm)
if __name__=='__main__':
    print(json.dumps(patch(pathlib.Path(sys.argv[1])),indent=2))
