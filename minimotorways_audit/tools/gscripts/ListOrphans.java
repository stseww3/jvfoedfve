import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;
public class ListOrphans extends GhidraScript {
    @Override public void run() throws Exception {
        String out = getScriptArgs()[0];
        Listing L = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
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
            for (Address a : todo) if (fm.getFunctionContaining(a) == null) createFunction(a, null);
        }
        PrintWriter w = new PrintWriter(new FileWriter(out));
        ReferenceManager rm = currentProgram.getReferenceManager();
        InstructionIterator ii = L.getInstructions(true);
        Address prevEnd = null;
        int runs = 0, count = 0;
        while (ii.hasNext()) {
            Instruction i = ii.next();
            if (fm.getFunctionContaining(i.getAddress()) != null) continue;
            count++;
            if (prevEnd == null || !i.getAddress().equals(prevEnd)) {
                runs++;
                Function before = getFunctionBefore(i.getAddress());
                StringBuilder refs = new StringBuilder();
                for (Reference r : rm.getReferencesTo(i.getAddress())) {
                    Function src = fm.getFunctionContaining(r.getFromAddress());
                    refs.append(r.getReferenceType()).append(" from ").append(r.getFromAddress()).append(src != null ? " (" + src.getName() + ")" : "").append("; ");
                }
                w.println("\n--- run at " + i.getAddress() + " (after function " + (before != null ? before.getName() + " @ " + before.getEntryPoint() + " ending " + before.getBody().getMaxAddress() : "none") + ") refs: " + (refs.length() == 0 ? "none" : refs));
            }
            w.println("  " + i.getAddress() + "  " + i.toString());
            prevEnd = i.getMaxAddress().next();
        }
        w.println("\n// orphan instructions: " + count + " in " + runs + " runs");
        w.close();
        println("ORPHANS " + count + " in " + runs + " runs -> " + out);
    }
}
