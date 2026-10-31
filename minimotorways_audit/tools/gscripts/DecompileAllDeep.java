import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;
public class DecompileAllDeep extends GhidraScript {
    @Override public void run() throws Exception {
        String out = getScriptArgs()[0];
        Listing L = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
        int created = 0;
        for (int pass = 0; pass < 3; pass++) {
            ReferenceManager rm = currentProgram.getReferenceManager();
            AddressIterator ai = rm.getReferenceDestinationIterator(currentProgram.getMemory().getExecuteSet(), true);
            List<Address> todo = new ArrayList<>();
            while (ai.hasNext()) {
                Address a = ai.next();
                if (fm.getFunctionContaining(a) != null) continue;
                Instruction ins = L.getInstructionAt(a);
                if (ins == null) continue;
                for (Reference r : rm.getReferencesTo(a)) {
                    RefType t = r.getReferenceType();
                    if (t.isData() || t.isCall() || t.isIndirect()) { todo.add(a); break; }
                }
            }
            for (Address a : todo) { if (fm.getFunctionContaining(a) == null && createFunction(a, null) != null) created++; }
        }
        println("CREATED " + created + " extra functions at referenced code labels");
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        PrintWriter w = new PrintWriter(new FileWriter(out));
        w.println("// Ghidra pseudo-C decompilation of " + currentProgram.getName() + " (all functions incl. hook detours / thread routines)");
        int n = 0, fail = 0;
        for (Function f : fm.getFunctions(true)) {
            if (monitor.isCancelled()) break;
            DecompileResults r = d.decompileFunction(f, 180, monitor);
            w.println("\n// ===== " + f.getName() + " @ " + f.getEntryPoint() + (f.isThunk() ? " (thunk)" : "") + " =====");
            if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) { w.println(r.getDecompiledFunction().getC()); n++; }
            else { w.println("// decompilation failed: " + (r == null ? "null" : r.getErrorMessage())); fail++; }
        }
        // report any executable bytes still outside functions
        long orphan = 0;
        InstructionIterator ii = L.getInstructions(true);
        while (ii.hasNext()) { Instruction i = ii.next(); if (fm.getFunctionContaining(i.getAddress()) == null) orphan++; }
        w.println("\n// instructions outside any function after deep pass: " + orphan);
        w.close();
        println("DECOMPILED " + n + " functions, failed " + fail + ", orphan instructions " + orphan + " -> " + out);
    }
}
