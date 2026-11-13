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
 *     <id>.req    one line "shot <file name>.png", written by whoever wants a picture
 *     <id>.done   the picture's full path, written here once the game has saved it
 *     <id>.fail   what went wrong
 *     ready       this process's id, written once at the start
 * The game saves the picture as <game folder>/screenshots/<file name>.png.
 *
 * Nothing of the game is changed. Its jar is used as it is; only public members are used, found by
 * name at run time, so this file compiles without the game: Minecraft.getInstance(), gameDirectory,
 * gameRenderer.mainRenderTarget(), Screenshot.grab(File, String, RenderTarget, int, Consumer) and
 * Minecraft as an Executor (checked against 26.3).
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
