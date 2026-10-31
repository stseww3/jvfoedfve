import pefile, sys
for p in sys.argv[1:]:
    pe=pefile.PE(p)
    print(f"\n################ {p}")
    print("  EntryPoint RVA:", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), " TLS callbacks:", bool(pe.OPTIONAL_HEADER.DATA_DIRECTORY[9].VirtualAddress))
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            fns=[(i.name.decode() if i.name else f"ord{i.ordinal}") for i in e.imports]
            print(f"  IMPORT {e.dll.decode():28s} ({len(fns)}): {', '.join(fns)}")
    if hasattr(pe,'DIRECTORY_ENTRY_DELAY_IMPORT'):
        for e in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
            fns=[(i.name.decode() if i.name else f"ord{i.ordinal}") for i in e.imports]
            print(f"  DELAY-IMPORT {e.dll.decode()} ({len(fns)}): {', '.join(fns)}")
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
        ex=pe.DIRECTORY_ENTRY_EXPORT.symbols
        fwd=[s for s in ex if s.forwarder]
        print(f"  EXPORTS: {len(ex)} total, {len(fwd)} forwarded")
        names=[(s.name.decode() if s.name else f'ord{s.ordinal}')+(f" -> {s.forwarder.decode()}" if s.forwarder else "") for s in ex]
        print("   ", ", ".join(names[:400]))
