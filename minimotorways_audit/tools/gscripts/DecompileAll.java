import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
public class DecompileAll extends GhidraScript {
    @Override public void run() throws Exception {
        String out = getScriptArgs()[0];
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        PrintWriter w = new PrintWriter(new FileWriter(out));
        w.println("// Ghidra pseudo-C decompilation of " + currentProgram.getName());
        w.println("// image base " + currentProgram.getImageBase());
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0, fail = 0;
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            DecompileResults r = d.decompileFunction(f, 120, monitor);
            w.println("\n// ===== " + f.getName() + " @ " + f.getEntryPoint() + (f.isThunk() ? " (thunk)" : "") + " =====");
            if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) { w.println(r.getDecompiledFunction().getC()); n++; }
            else { w.println("// decompilation failed: " + (r == null ? "null" : r.getErrorMessage())); fail++; }
        }
        w.close();
        println("DECOMPILED " + n + " functions, failed " + fail + " -> " + out);
    }
}
