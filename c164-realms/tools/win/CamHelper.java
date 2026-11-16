import java.io.File;
import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.Executor;
import java.util.function.Consumer;

/**
 * Entry point of the picture client: starts the game as it is and, beside it, a thread through
 * which the game can be asked for its own screenshot (the picture the F2 key saves).
 *
 * Why: on a desktop that somebody is using the game's window lies behind the other windows and
 * never has the keyboard, so F2 cannot be pressed in it; and a picture taken from the window by
 * the desktop comes back black whenever the display is asleep. The game's own screenshot needs
 * neither the keyboard nor the display.
 *
 * Asked through files in the folder named by -Dc164.cam=<folder> (relative to the game folder):
 *     <id>.req    one line "shot <file name>.png", written by whoever wants a picture; or
 *                 "track <file name>.txt <seconds> [<player name>]" (see track()); or
 *                 "frames <seconds>" (see frames())
 *     <id>.done   the picture's full path, written here once the game has saved it
 *     <id>.fail   what went wrong
 *     ready       this process's id, written once at the start
 * The game saves the picture as <game folder>/screenshots/<file name>.png.
 *
 * Nothing of the game is changed. Its jar is used as it is; only public members are used, found by
 * name at run time, so this file compiles without the game: Minecraft.getInstance(), gameDirectory,
 * gameRenderer.mainRenderTarget(), Screenshot.grab(File, String, RenderTarget, int, Consumer) and
 * Minecraft as an Executor; for track() gameRenderer.mainCamera().position(), player, level.players(),
 * Entity.position(), getVehicle(), getScoreboardName() and Vec3's x, y, z; for frames()
 * Minecraft.getFps() (checked against 26.3).
 *
 * Built by build_helper.py on a machine with a JDK; the class is kept in helper/ beside this file.
 */
public final class CamHelper {
    private static final String TAG = "[c164-cam] ";

    private CamHelper() {
    }

    public static void main(String[] args) throws Exception {
        String folder = System.getProperty("c164.cam");
        if (folder != null && !folder.isEmpty()) {
            Thread watcher = new Thread(() -> watch(new File(folder).getAbsoluteFile()), "c164-cam");
            watcher.setDaemon(true);
            watcher.start();
        }
        Class.forName("net.minecraft.client.main.Main").getMethod("main", String[].class).invoke(null, (Object) args);
    }

    private static void watch(File folder) {
        folder.mkdirs();
        File[] old = folder.listFiles();
        if (old != null) {
            for (File file : old) {
                file.delete();
            }
        }
        write(folder, "ready", Long.toString(ProcessHandle.current().pid()));
        System.out.println(TAG + "watching " + folder);
        while (true) {
            try {
                File[] requests = folder.listFiles((dir, name) -> name.endsWith(".req"));
                if (requests != null) {
                    for (File request : requests) {
                        handle(folder, request);
                    }
                }
                Thread.sleep(50);
            } catch (InterruptedException e) {
                return;
            } catch (Throwable t) {
                System.out.println(TAG + "error: " + t);
            }
        }
    }

    private static void handle(File folder, File request) throws IOException {
        String name = request.getName();
        String id = name.substring(0, name.length() - ".req".length());
        String line = new String(Files.readAllBytes(request.toPath()), StandardCharsets.UTF_8).trim();
        if (!request.delete()) {
            return;                                    // still held by its writer: next round
        }
        if (line.startsWith("shot ")) {
            shot(folder, id, line.substring(5).trim());
        } else if (line.startsWith("track ")) {
            String[] parts = line.substring(6).trim().split("\\s+");
            Thread tracker = new Thread(() -> track(folder, id, parts), "c164-track");
            tracker.setDaemon(true);
            tracker.start();                           // pictures can be asked for while it runs
        } else if (line.startsWith("frames ")) {
            String seconds = line.substring(7).trim();
            Thread counter = new Thread(() -> frames(folder, id, seconds), "c164-frames");
            counter.setDaemon(true);
            counter.start();
        } else {
            answer(folder, id, "fail", "not understood: " + line);
        }
    }

    private static void shot(File folder, String id, String fileName) {
        try {
            if (!fileName.endsWith(".png") || !new File(fileName).getName().equals(fileName)) {
                answer(folder, id, "fail", "not a plain .png file name: " + fileName);
                return;
            }
            Class<?> game = Class.forName("net.minecraft.client.Minecraft");
            Object minecraft = game.getMethod("getInstance").invoke(null);
            Object renderer = minecraft == null ? null : game.getField("gameRenderer").get(minecraft);
            if (renderer == null) {
                answer(folder, id, "fail", "the game has not started yet");
                return;
            }
            File gameFolder = (File) game.getField("gameDirectory").get(minecraft);
            File picture = new File(new File(gameFolder, "screenshots"), fileName);
            picture.delete();
            Method grab = grab();
            // The game calls this from its file-writing thread once the picture is saved, or has failed.
            Consumer<Object> saved = message -> {
                if (picture.isFile()) {
                    answer(folder, id, "done", picture.getAbsolutePath());
                } else {
                    answer(folder, id, "fail", "the game could not save the picture (see its log)");
                }
            };
            // Run by the game on its drawing thread between two frames, like a key press is.
            ((Executor) minecraft).execute(() -> {
                try {
                    Object target = renderer.getClass().getMethod("mainRenderTarget").invoke(renderer);
                    grab.invoke(null, gameFolder, fileName, target, 1, saved);
                } catch (Throwable t) {
                    answer(folder, id, "fail", String.valueOf(t.getCause() != null ? t.getCause() : t));
                }
            });
        } catch (Throwable t) {
            answer(folder, id, "fail", String.valueOf(t.getCause() != null ? t.getCause() : t));
        }
    }

    /**
     * "track <file name>.txt <seconds> [<player name>]": for that many seconds what moves is
     * written down, with the time in milliseconds since the start: a line "C t x y z" whenever the
     * game's camera stands somewhere else than a moment before (once a frame while it moves),
     * "P t x y z vx vy vz" whenever this client's own player does (once a tick; v is what it rides,
     * NaN when it rides nothing) and "O t x y z vx vy vz" for the player of that name as this
     * client has it. The file is written into the asking folder and named in the answer.
     */
    private static void track(File folder, String id, String[] parts) {
        try {
            String fileName = parts[0];
            if (parts.length < 2 || !fileName.endsWith(".txt") || !new File(fileName).getName().equals(fileName)) {
                answer(folder, id, "fail", "track <file name>.txt <seconds> [<player name>]");
                return;
            }
            double seconds = Math.min(120.0, Double.parseDouble(parts[1]));
            String other = parts.length > 2 ? parts[2] : null;
            Class<?> game = Class.forName("net.minecraft.client.Minecraft");
            Object minecraft = game.getMethod("getInstance").invoke(null);
            Object renderer = game.getField("gameRenderer").get(minecraft);
            Object camera = renderer.getClass().getMethod("mainCamera").invoke(renderer);
            Method cameraAt = camera.getClass().getMethod("position");
            StringBuilder out = new StringBuilder();
            double[] lastCamera = null;
            double[] lastOwn = null;
            double[] lastOther = null;
            long start = System.nanoTime();
            while (System.nanoTime() - start < (long) (seconds * 1e9)) {
                double t = (System.nanoTime() - start) / 1e6;
                try {
                    double[] now = xyz(cameraAt.invoke(camera));
                    if (differs(now, lastCamera)) {
                        note(out, "C", t, now);
                        lastCamera = now;
                    }
                    Object player = game.getField("player").get(minecraft);
                    if (player != null) {
                        double[] own = withVehicle(player);
                        if (differs(own, lastOwn)) {
                            note(out, "P", t, own);
                            lastOwn = own;
                        }
                    }
                    Object level = other == null ? null : game.getField("level").get(minecraft);
                    if (level != null) {
                        for (Object one : (Iterable<?>) level.getClass().getMethod("players").invoke(level)) {
                            if (other.equals(one.getClass().getMethod("getScoreboardName").invoke(one))) {
                                double[] theirs = withVehicle(one);
                                if (differs(theirs, lastOther)) {
                                    note(out, "O", t, theirs);
                                    lastOther = theirs;
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    out.append("# ").append(e).append('\n');   // the game changed a list under our hands: next round
                }
                Thread.sleep(2);
            }
            File file = new File(folder, fileName);
            Files.write(file.toPath(), out.toString().getBytes(StandardCharsets.UTF_8));
            answer(folder, id, "done", file.getAbsolutePath());
        } catch (Throwable t) {
            answer(folder, id, "fail", String.valueOf(t.getCause() != null ? t.getCause() : t));
        }
    }

    /**
     * "frames <seconds>": the game's own count of the frames it drew in the second before (the
     * number F3 shows, Minecraft.getFps()), read once a second for that long; the answer is the
     * readings, in the order read.
     */
    private static void frames(File folder, String id, String asked) {
        try {
            double seconds = Math.min(120.0, Double.parseDouble(asked));
            Class<?> game = Class.forName("net.minecraft.client.Minecraft");
            Object minecraft = game.getMethod("getInstance").invoke(null);
            Method count = game.getMethod("getFps");
            StringBuilder out = new StringBuilder();
            long start = System.nanoTime();
            while (System.nanoTime() - start < (long) (seconds * 1e9)) {
                Thread.sleep(1000);
                out.append(count.invoke(minecraft)).append(' ');
            }
            answer(folder, id, "done", out.toString().trim());
        } catch (Throwable t) {
            answer(folder, id, "fail", String.valueOf(t.getCause() != null ? t.getCause() : t));
        }
    }

    private static double[] xyz(Object vector) throws ReflectiveOperationException {
        Class<?> kind = vector.getClass();
        return new double[] {kind.getField("x").getDouble(vector), kind.getField("y").getDouble(vector),
                             kind.getField("z").getDouble(vector)};
    }

    /** Where an entity is and where what it rides is (NaN three times when it rides nothing). */
    private static double[] withVehicle(Object entity) throws ReflectiveOperationException {
        double[] at = xyz(entity.getClass().getMethod("position").invoke(entity));
        Object vehicle = entity.getClass().getMethod("getVehicle").invoke(entity);
        double[] on = vehicle == null ? new double[] {Double.NaN, Double.NaN, Double.NaN}
                : xyz(vehicle.getClass().getMethod("position").invoke(vehicle));
        return new double[] {at[0], at[1], at[2], on[0], on[1], on[2]};
    }

    private static boolean differs(double[] now, double[] before) {
        if (before == null) {
            return true;
        }
        for (int i = 0; i < now.length; i++) {
            if (Double.compare(now[i], before[i]) != 0) {
                return true;
            }
        }
        return false;
    }

    private static void note(StringBuilder out, String kind, double t, double[] values) {
        out.append(kind).append(' ').append(String.format(java.util.Locale.ROOT, "%.1f", t));
        for (double value : values) {
            out.append(' ').append(String.format(java.util.Locale.ROOT, "%.4f", value));
        }
        out.append('\n');
    }

    private static Method grab() throws ClassNotFoundException {
        for (Method method : Class.forName("net.minecraft.client.Screenshot").getMethods()) {
            Class<?>[] takes = method.getParameterTypes();
            if (method.getName().equals("grab") && takes.length == 5 && takes[0] == File.class
                    && takes[1] == String.class && takes[3] == int.class && takes[4] == Consumer.class) {
                return method;
            }
        }
        throw new IllegalStateException("this game has no Screenshot.grab(File, String, target, int, Consumer)");
    }

    private static void answer(File folder, String id, String kind, String text) {
        write(folder, id + "." + kind, text);
        System.out.println(TAG + id + " " + kind + ": " + text);
    }

    /** The file appears under its name only when it is complete. */
    private static void write(File folder, String name, String text) {
        try {
            File part = new File(folder, name + ".part");
            Files.write(part.toPath(), text.getBytes(StandardCharsets.UTF_8));
            Files.move(part.toPath(), new File(folder, name).toPath(), StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            System.out.println(TAG + "cannot write " + name + ": " + e);
        }
    }
}
