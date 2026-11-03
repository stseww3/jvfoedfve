package com.dinopoloclub.minimotorways;

import android.app.Activity;
import android.content.Context;
import android.content.pm.ActivityInfo;
import android.content.res.AssetManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.graphics.RectF;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.Display;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowManager;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class MobilePortActivity extends Activity {
    static {
        try {
            System.loadLibrary("dpcPlatform");
            System.loadLibrary("decompressAudio");
        } catch (Throwable ignored) {
        }
    }

    public static native int nativeRunDpcSelfTest();
    public static native int nativeStepVehicleFix64(long gapRaw, long speedRaw, long leadSpeedRaw, long desiredSpeedRaw);
    public static native boolean nativeDecompressFlac(byte[] compressedBank, int compressedOffset, short[] decompressedOut, int sampleCount);

    private MotorwaysPortView _view;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= 28) {
            WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(lp);
        }
        _view = new MotorwaysPortView(this);
        setContentView(_view);
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (_view != null) {
            _view.onAppPaused();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        if (_view != null) {
            _view.onAppResumed();
        }
    }

    private static final class MotorwaysPortView extends View {
        private static final int GRID_COLS = 18;
        private static final int GRID_ROWS = 10;

        private final Context _ctx;
        private final Paint _paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF _tmpRect = new RectF();

        private final boolean[][] _roads = new boolean[GRID_COLS][GRID_ROWS];
        private final int[][] _buildings = new int[GRID_COLS][GRID_ROWS]; // 1=Red House, 2=Red Dest, 3=Blue House, 4=Blue Dest

        private float _camX = 0f;
        private float _camY = 0f;
        private float _zoom = 1.0f;
        private float _targetZoom = 1.0f;
        private static final float MIN_ZOOM = 0.65f;
        private static final float MAX_ZOOM = 2.60f;

        private boolean _autoZoomEnabled = true;
        private boolean _isFocusedIn = false;
        private boolean _deleteMode = false;
        private boolean _symmetricSafeArea = true;
        private int _fpsMode = 2; // 0=30, 1=60, 2=Auto (up to 90Hz on Galaxy A72)
        private int _simSpeed = 1; // 0=Pause, 1=1x, 2=2x

        private boolean _isPinching = false;
        private float _initialPinchDist = 0f;
        private float _initialPinchZoom = 1f;
        private float _pinchWorldAnchorX = 0f;
        private float _pinchWorldAnchorY = 0f;

        private float _touchStartX = 0f;
        private float _touchStartY = 0f;
        private long _touchStartTime = 0L;
        private boolean _touchDragged = false;

        private int _cursorX = GRID_COLS / 2;
        private int _cursorY = GRID_ROWS / 2;
        private String _inputSourceLabel = "Touch";
        private String _controllerName = "None";

        private int _tripsCompleted = 0;
        private int _roadsBuiltCount = 0;
        private int _dpcSelfTestStatus = 0;
        private boolean _flacDecodedOk = false;
        private short[] _decodedChimePcm;

        private final boolean[] _achUnlocked = new boolean[5];
        private final String[] _achTitles = new String[] {
            "First Road Built",
            "First Commute Completed",
            "Pinch Zoom Explorer",
            "Controller Connected",
            "Metropolis (10 Trips)"
        };
        private String _activeToast = null;
        private long _toastUntilMs = 0L;

        private float _carProgressRed = 0f;
        private float _carProgressBlue = 0.5f;
        private long _lastFrameNs = System.nanoTime();
        private float _measuredFps = 60f;
        private int _safeLeft = 0, _safeTop = 0, _safeRight = 0, _safeBottom = 0;

        private final List<RectF> _hudButtons = new ArrayList<>();

        public MotorwaysPortView(Context context) {
            super(context);
            _ctx = context;
            setFocusable(true);
            setFocusableInTouchMode(true);
            requestFocus();

            initDefaultMap();
            runNativeSelfTests();
            loadAtomicSave();
        }

        private void initDefaultMap() {
            for (int x = 0; x < GRID_COLS; x++) {
                for (int y = 0; y < GRID_ROWS; y++) {
                    _roads[x][y] = false;
                    _buildings[x][y] = 0;
                }
            }
            _buildings[3][2] = 1;  // Red House
            _buildings[14][2] = 2; // Red Destination
            _buildings[3][7] = 3;  // Blue House
            _buildings[14][7] = 4; // Blue Destination

            for (int x = 3; x <= 14; x++) {
                _roads[x][2] = true;
                _roads[x][7] = true;
            }
            _roadsBuiltCount = 24;
        }

        private void runNativeSelfTests() {
            try {
                _dpcSelfTestStatus = nativeRunDpcSelfTest();
            } catch (Throwable t) {
                _dpcSelfTestStatus = -99;
            }
            try {
                AssetManager am = _ctx.getAssets();
                try (InputStream is = am.open("Sounds/48000/chime.bytes")) {
                    ByteArrayOutputStream bos = new ByteArrayOutputStream();
                    byte[] buf = new byte[4096];
                    int r;
                    while ((r = is.read(buf)) > 0) bos.write(buf, 0, r);
                    byte[] bank = bos.toByteArray();
                    int sampleCount = 9895;
                    short[] out = new short[sampleCount];
                    if (nativeDecompressFlac(bank, 0, out, sampleCount)) {
                        _flacDecodedOk = true;
                        _decodedChimePcm = out;
                    }
                }
            } catch (Throwable ignored) {
            }
        }

        private void playChime() {
            if (_decodedChimePcm == null) return;
            final short[] pcm = _decodedChimePcm;
            new Thread(() -> {
                try {
                    AudioTrack track = new AudioTrack.Builder()
                        .setAudioAttributes(new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_GAME)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build())
                        .setAudioFormat(new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(48000)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build())
                        .setBufferSizeInBytes(pcm.length * 2)
                        .setTransferMode(AudioTrack.MODE_STATIC)
                        .build();
                    track.write(pcm, 0, pcm.length);
                    track.play();
                    Thread.sleep(250);
                    track.release();
                } catch (Throwable ignored) {
                }
            }).start();
        }

        private void vibrateLight() {
            try {
                Vibrator v = (Vibrator) _ctx.getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null && v.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= 26) {
                        v.vibrate(VibrationEffect.createOneShot(12, 80));
                    } else {
                        v.vibrate(12);
                    }
                }
            } catch (Throwable ignored) {
            }
        }

        private void unlockAchievement(int index) {
            if (index < 0 || index >= _achUnlocked.length || _achUnlocked[index]) return;
            _achUnlocked[index] = true;
            _activeToast = _achTitles[index];
            _toastUntilMs = System.currentTimeMillis() + 3200L;
            playChime();
            saveAtomic();
        }

        public void onAppPaused() {
            saveAtomic();
        }

        public void onAppResumed() {
            detectControllers();
            invalidate();
        }

        private void detectControllers() {
            int[] ids = InputDevice.getDeviceIds();
            _controllerName = "None";
            for (int id : ids) {
                InputDevice dev = InputDevice.getDevice(id);
                if (dev == null) continue;
                int sources = dev.getSources();
                if ((sources & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD ||
                    (sources & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK) {
                    _controllerName = dev.getName();
                    break;
                }
            }
        }

        private void saveAtomic() {
            File dir = _ctx.getFilesDir();
            File primary = new File(dir, "motorways_mobile_save.txt");
            File tmp = new File(dir, "motorways_mobile_save.txt.tmp");
            File bak = new File(dir, "motorways_mobile_save.txt.bak");
            try {
                StringBuilder sb = new StringBuilder();
                sb.append("TRIPS=").append(_tripsCompleted).append('\n');
                sb.append("AUTOZOOM=").append(_autoZoomEnabled ? 1 : 0).append('\n');
                sb.append("FPSMODE=").append(_fpsMode).append('\n');
                sb.append("SYMSAFE=").append(_symmetricSafeArea ? 1 : 0).append('\n');
                sb.append("ACH=");
                for (boolean b : _achUnlocked) sb.append(b ? '1' : '0');
                sb.append('\n');
                sb.append("ROADS=");
                for (int x = 0; x < GRID_COLS; x++) {
                    for (int y = 0; y < GRID_ROWS; y++) {
                        sb.append(_roads[x][y] ? '1' : '0');
                    }
                }
                sb.append('\n');

                try (FileOutputStream fos = new FileOutputStream(tmp)) {
                    fos.write(sb.toString().getBytes(StandardCharsets.UTF_8));
                    fos.getFD().sync();
                }
                if (primary.exists()) {
                    copyFile(primary, bak);
                    primary.delete();
                }
                tmp.renameTo(primary);
            } catch (Throwable ignored) {
            }
        }

        private void loadAtomicSave() {
            File dir = _ctx.getFilesDir();
            File primary = new File(dir, "motorways_mobile_save.txt");
            File bak = new File(dir, "motorways_mobile_save.txt.bak");
            if (!parseSaveFile(primary)) {
                parseSaveFile(bak);
            }
        }

        private boolean parseSaveFile(File f) {
            if (f == null || !f.exists()) return false;
            try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    if (line.startsWith("TRIPS=")) _tripsCompleted = Integer.parseInt(line.substring(6));
                    else if (line.startsWith("AUTOZOOM=")) _autoZoomEnabled = "1".equals(line.substring(9));
                    else if (line.startsWith("FPSMODE=")) _fpsMode = Integer.parseInt(line.substring(8));
                    else if (line.startsWith("SYMSAFE=")) _symmetricSafeArea = "1".equals(line.substring(8));
                    else if (line.startsWith("ACH=")) {
                        String s = line.substring(4);
                        for (int i = 0; i < Math.min(s.length(), _achUnlocked.length); i++) {
                            _achUnlocked[i] = s.charAt(i) == '1';
                        }
                    } else if (line.startsWith("ROADS=")) {
                        String s = line.substring(6);
                        int idx = 0;
                        int cnt = 0;
                        for (int x = 0; x < GRID_COLS; x++) {
                            for (int y = 0; y < GRID_ROWS; y++) {
                                if (idx < s.length()) {
                                    _roads[x][y] = s.charAt(idx++) == '1';
                                    if (_roads[x][y]) cnt++;
                                }
                            }
                        }
                        _roadsBuiltCount = cnt;
                    }
                }
                return true;
            } catch (Throwable t) {
                return false;
            }
        }

        private static void copyFile(File src, File dst) {
            try (FileInputStream in = new FileInputStream(src); FileOutputStream out = new FileOutputStream(dst)) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                out.getFD().sync();
            } catch (Throwable ignored) {
            }
        }

        private float baseTileSize() {
            int w = Math.max(getWidth(), 1);
            int h = Math.max(getHeight(), 1);
            return Math.min((w - 160f) / GRID_COLS, (h - 220f) / GRID_ROWS);
        }

        private float screenToWorldX(float sx) {
            float cx = getWidth() * 0.5f;
            return _camX + (sx - cx) / _zoom;
        }

        private float screenToWorldY(float sy) {
            float cy = getHeight() * 0.5f;
            return _camY + (sy - cy) / _zoom;
        }

        private int screenToTileX(float sx) {
            float ts = baseTileSize();
            float wx = screenToWorldX(sx);
            float gridW = GRID_COLS * ts;
            return (int) Math.floor((wx + gridW * 0.5f) / ts);
        }

        private int screenToTileY(float sy) {
            float ts = baseTileSize();
            float wy = screenToWorldY(sy);
            float gridH = GRID_ROWS * ts;
            return (int) Math.floor((wy + gridH * 0.5f) / ts);
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            _inputSourceLabel = "Touch";
            int action = event.getActionMasked();
            int pointerCount = event.getPointerCount();

            if (pointerCount >= 2) {
                float x0 = event.getX(0), y0 = event.getY(0);
                float x1 = event.getX(1), y1 = event.getY(1);
                float midX = (x0 + x1) * 0.5f;
                float midY = (y0 + y1) * 0.5f;
                float dist = (float) Math.hypot(x1 - x0, y1 - y0);

                if (!_isPinching) {
                    _isPinching = true;
                    _initialPinchDist = Math.max(dist, 16f);
                    _initialPinchZoom = _zoom;
                    _pinchWorldAnchorX = screenToWorldX(midX);
                    _pinchWorldAnchorY = screenToWorldY(midY);
                } else if (dist >= 16f) {
                    float scale = dist / _initialPinchDist;
                    _zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, _initialPinchZoom * scale));
                    _targetZoom = _zoom;
                    _camX = _pinchWorldAnchorX - (midX - getWidth() * 0.5f) / _zoom;
                    _camY = _pinchWorldAnchorY - (midY - getHeight() * 0.5f) / _zoom;
                    _isFocusedIn = _zoom > 1.15f;
                    unlockAchievement(2); // Pinch Zoom Explorer
                }
                invalidate();
                return true;
            }

            if (action == MotionEvent.ACTION_DOWN) {
                _isPinching = false;
                _touchStartX = event.getX();
                _touchStartY = event.getY();
                _touchStartTime = System.currentTimeMillis();
                _touchDragged = false;

                if (handleHudButtonTap(_touchStartX, _touchStartY)) {
                    invalidate();
                    return true;
                }
                return true;
            } else if (action == MotionEvent.ACTION_MOVE && !_isPinching) {
                float x = event.getX();
                float y = event.getY();
                float slop = 12f * (getResources().getDisplayMetrics().density);
                if (Math.hypot(x - _touchStartX, y - _touchStartY) > slop) {
                    _touchDragged = true;
                }
                if (_touchDragged) {
                    int tx = screenToTileX(x);
                    int ty = screenToTileY(y);
                    if (tx >= 0 && tx < GRID_COLS && ty >= 0 && ty < GRID_ROWS) {
                        _cursorX = tx;
                        _cursorY = ty;
                        boolean nextVal = !_deleteMode;
                        if (_roads[tx][ty] != nextVal && _buildings[tx][ty] == 0) {
                            _roads[tx][ty] = nextVal;
                            _roadsBuiltCount += nextVal ? 1 : -1;
                            vibrateLight();
                            unlockAchievement(0);
                        }
                    }
                    invalidate();
                }
                return true;
            } else if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
                if (!_isPinching && !_touchDragged && (System.currentTimeMillis() - _touchStartTime) < 600L) {
                    float x = event.getX();
                    float y = event.getY();
                    int tx = screenToTileX(x);
                    int ty = screenToTileY(y);
                    if (tx >= 0 && tx < GRID_COLS && ty >= 0 && ty < GRID_ROWS) {
                        _cursorX = tx;
                        _cursorY = ty;
                        // TouchCameraAction single-tap behavior with Touch Auto-Zoom toggle
                        if (!_isFocusedIn) {
                            _isFocusedIn = true;
                            _camX = screenToWorldX(x);
                            _camY = screenToWorldY(y);
                            if (_autoZoomEnabled) {
                                _targetZoom = 1.65f;
                            }
                        } else {
                            _isFocusedIn = false;
                            _camX = 0f;
                            _camY = 0f;
                            _targetZoom = 1.0f;
                        }
                    }
                }
                _isPinching = false;
                invalidate();
                return true;
            }
            return super.onTouchEvent(event);
        }

        private boolean handleHudButtonTap(float x, float y) {
            for (int i = 0; i < _hudButtons.size(); i++) {
                if (_hudButtons.get(i).contains(x, y)) {
                    vibrateLight();
                    switch (i) {
                        case 0: // Draw / Delete mode
                            _deleteMode = !_deleteMode;
                            break;
                        case 1: // Touch Auto-Zoom toggle
                            _autoZoomEnabled = !_autoZoomEnabled;
                            saveAtomic();
                            break;
                        case 2: // FPS mode (30 / 60 / Auto)
                            _fpsMode = (_fpsMode + 1) % 3;
                            saveAtomic();
                            break;
                        case 3: // Sim Speed (Pause / 1x / 2x)
                            _simSpeed = (_simSpeed + 1) % 3;
                            break;
                        case 4: // Symmetric Cutout SafeArea toggle
                            _symmetricSafeArea = !_symmetricSafeArea;
                            saveAtomic();
                            break;
                        case 5: // Save & Audio Chime Test
                            saveAtomic();
                            playChime();
                            break;
                    }
                    return true;
                }
            }
            return false;
        }

        @Override
        public boolean onKeyDown(int keyCode, KeyEvent event) {
            if ((event.getSource() & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD ||
                (event.getSource() & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK ||
                (event.getSource() & InputDevice.SOURCE_DPAD) == InputDevice.SOURCE_DPAD) {
                detectControllers();
                _inputSourceLabel = _controllerName.toLowerCase().contains("kishi") ? "Razer Kishi V2" : "Controller";
                unlockAchievement(3);
            }

            switch (keyCode) {
                case KeyEvent.KEYCODE_DPAD_LEFT:
                    _cursorX = Math.max(0, _cursorX - 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_DPAD_RIGHT:
                    _cursorX = Math.min(GRID_COLS - 1, _cursorX + 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_DPAD_UP:
                    _cursorY = Math.max(0, _cursorY - 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_DPAD_DOWN:
                    _cursorY = Math.min(GRID_ROWS - 1, _cursorY + 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_A:
                case KeyEvent.KEYCODE_DPAD_CENTER:
                    if (_buildings[_cursorX][_cursorY] == 0) {
                        _roads[_cursorX][_cursorY] = !_deleteMode;
                        vibrateLight();
                        unlockAchievement(0);
                    }
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_B:
                case KeyEvent.KEYCODE_BACK:
                    _isFocusedIn = false;
                    _targetZoom = 1.0f;
                    _camX = 0f;
                    _camY = 0f;
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_X:
                    _deleteMode = !_deleteMode;
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_Y:
                case KeyEvent.KEYCODE_BUTTON_THUMBR:
                    _isFocusedIn = !_isFocusedIn;
                    _targetZoom = _isFocusedIn ? 1.65f : 1.0f;
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_L1:
                    _simSpeed = Math.max(0, _simSpeed - 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_R1:
                    _simSpeed = Math.min(2, _simSpeed + 1);
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_START:
                    _fpsMode = (_fpsMode + 1) % 3;
                    saveAtomic();
                    invalidate();
                    return true;
                case KeyEvent.KEYCODE_BUTTON_SELECT:
                    _autoZoomEnabled = !_autoZoomEnabled;
                    saveAtomic();
                    invalidate();
                    return true;
            }
            return super.onKeyDown(keyCode, event);
        }

        @Override
        public boolean onGenericMotionEvent(MotionEvent event) {
            if ((event.getSource() & InputDevice.SOURCE_JOYSTICK) != 0 && event.getAction() == MotionEvent.ACTION_MOVE) {
                detectControllers();
                _inputSourceLabel = _controllerName.toLowerCase().contains("kishi") ? "Razer Kishi V2" : "Controller";
                unlockAchievement(3);

                float rx = event.getAxisValue(MotionEvent.AXIS_Z);
                float ry = event.getAxisValue(MotionEvent.AXIS_RZ);
                if (Math.hypot(rx, ry) > 0.2f) {
                    _camX += rx * 18f / _zoom;
                    _camY += ry * 18f / _zoom;
                }
                float lt = Math.max(event.getAxisValue(MotionEvent.AXIS_LTRIGGER), event.getAxisValue(MotionEvent.AXIS_BRAKE));
                float rt = Math.max(event.getAxisValue(MotionEvent.AXIS_RTRIGGER), event.getAxisValue(MotionEvent.AXIS_GAS));
                if (rt > 0.3f) _targetZoom = Math.min(MAX_ZOOM, _targetZoom + 0.04f);
                if (lt > 0.3f) _targetZoom = Math.max(MIN_ZOOM, _targetZoom - 0.04f);
                invalidate();
                return true;
            }
            return super.onGenericMotionEvent(event);
        }

        private void updateSafeAreaInsets() {
            _safeLeft = 0;
            _safeTop = 0;
            _safeRight = 0;
            _safeBottom = 0;
            if (Build.VERSION.SDK_INT >= 28) {
                WindowInsets insets = getRootWindowInsets();
                if (insets != null && insets.getDisplayCutout() != null) {
                    _safeLeft = insets.getDisplayCutout().getSafeInsetLeft();
                    _safeRight = insets.getDisplayCutout().getSafeInsetRight();
                    _safeTop = insets.getDisplayCutout().getSafeInsetTop();
                    _safeBottom = insets.getDisplayCutout().getSafeInsetBottom();
                }
            }
            // Simulate 72px punch-hole inset if device has no cutout so symmetric toggle is always visible
            if (_safeLeft == 0 && _safeRight == 0) {
                _safeLeft = 48;
            }
            if (_symmetricSafeArea) {
                int maxH = Math.max(_safeLeft, _safeRight);
                _safeLeft = maxH;
                _safeRight = maxH;
            }
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            long nowNs = System.nanoTime();
            float dt = Math.min(0.1f, Math.max(0.001f, (nowNs - _lastFrameNs) * 1e-9f));
            _lastFrameNs = nowNs;
            _measuredFps = _measuredFps * 0.9f + (1f / dt) * 0.1f;

            _zoom += (_targetZoom - _zoom) * Math.min(1f, dt * 10f);

            int w = getWidth();
            int h = getHeight();
            updateSafeAreaInsets();

            // Background (Mini Motorways warm paper palette)
            canvas.drawColor(Color.rgb(244, 241, 234));

            // Draw world grid & road network
            float ts = baseTileSize();
            float gridW = GRID_COLS * ts;
            float gridH = GRID_ROWS * ts;

            canvas.save();
            canvas.translate(w * 0.5f, h * 0.5f);
            canvas.scale(_zoom, _zoom);
            canvas.translate(-_camX, -_camY);

            float startX = -gridW * 0.5f;
            float startY = -gridH * 0.5f;

            // Grid lines
            _paint.setStyle(Paint.Style.STROKE);
            _paint.setStrokeWidth(1.5f / _zoom);
            _paint.setColor(Color.rgb(220, 216, 206));
            for (int x = 0; x <= GRID_COLS; x++) {
                float gx = startX + x * ts;
                canvas.drawLine(gx, startY, gx, startY + gridH, _paint);
            }
            for (int y = 0; y <= GRID_ROWS; y++) {
                float gy = startY + y * ts;
                canvas.drawLine(startX, gy, startX + gridW, gy, _paint);
            }

            // Road tiles
            _paint.setStyle(Paint.Style.FILL);
            _paint.setColor(Color.rgb(78, 84, 92));
            for (int x = 0; x < GRID_COLS; x++) {
                for (int y = 0; y < GRID_ROWS; y++) {
                    if (_roads[x][y]) {
                        float rx = startX + x * ts + ts * 0.12f;
                        float ry = startY + y * ts + ts * 0.12f;
                        _tmpRect.set(rx, ry, rx + ts * 0.76f, ry + ts * 0.76f);
                        canvas.drawRoundRect(_tmpRect, ts * 0.2f, ts * 0.2f, _paint);
                    }
                }
            }

            // Houses and Destinations
            for (int x = 0; x < GRID_COLS; x++) {
                for (int y = 0; y < GRID_ROWS; y++) {
                    int b = _buildings[x][y];
                    if (b == 0) continue;
                    float bx = startX + x * ts + ts * 0.08f;
                    float by = startY + y * ts + ts * 0.08f;
                    _tmpRect.set(bx, by, bx + ts * 0.84f, by + ts * 0.84f);
                    _paint.setColor((b == 1 || b == 2) ? Color.rgb(228, 76, 65) : Color.rgb(52, 132, 212));
                    canvas.drawRoundRect(_tmpRect, ts * 0.18f, ts * 0.18f, _paint);
                    _paint.setColor(Color.WHITE);
                    _paint.setTextSize(ts * 0.36f);
                    _paint.setTextAlign(Paint.Align.CENTER);
                    String label = (b == 1 || b == 3) ? "H" : "D";
                    canvas.drawText(label, bx + ts * 0.42f, by + ts * 0.55f, _paint);
                }
            }

            // Vehicles moving along Row 2 (Red) and Row 7 (Blue)
            if (_simSpeed > 0) {
                float speedMult = (_simSpeed == 2) ? 1.8f : 0.9f;
                _carProgressRed += dt * speedMult;
                if (_carProgressRed >= 1f) {
                    _carProgressRed -= 1f;
                    _tripsCompleted++;
                    unlockAchievement(1);
                    if (_tripsCompleted >= 10) unlockAchievement(4);
                }
                _carProgressBlue += dt * speedMult * 0.85f;
                if (_carProgressBlue >= 1f) {
                    _carProgressBlue -= 1f;
                    _tripsCompleted++;
                }
            }

            drawCarOnRow(canvas, startX, startY, ts, 2, _carProgressRed, Color.rgb(255, 110, 95));
            drawCarOnRow(canvas, startX, startY, ts, 7, _carProgressBlue, Color.rgb(85, 165, 245));

            // Controller / Touch Focus Cursor
            _paint.setStyle(Paint.Style.STROKE);
            _paint.setStrokeWidth(3.5f / _zoom);
            _paint.setColor(Color.rgb(245, 166, 35));
            float cx = startX + _cursorX * ts + 2f;
            float cy = startY + _cursorY * ts + 2f;
            _tmpRect.set(cx, cy, cx + ts - 4f, cy + ts - 4f);
            canvas.drawRoundRect(_tmpRect, ts * 0.15f, ts * 0.15f, _paint);

            canvas.restore();

            // Safe-Area Outline (Samsung Galaxy A72 20:9 punch-hole cutout protection)
            _paint.setStyle(Paint.Style.STROKE);
            _paint.setStrokeWidth(2f);
            _paint.setColor(Color.argb(110, 46, 160, 67));
            canvas.drawRect(_safeLeft, _safeTop, w - _safeRight, h - _safeBottom, _paint);

            // Top HUD Bar inside Safe Area
            drawHud(canvas, w, h);

            // Achievement Toast Overlay
            if (_activeToast != null && System.currentTimeMillis() < _toastUntilMs) {
                float tw = Math.min(w - _safeLeft - _safeRight - 40f, 560f);
                float th = 68f;
                float tx = _safeLeft + (w - _safeLeft - _safeRight - tw) * 0.5f;
                float ty = h - _safeBottom - th - 18f;
                _paint.setStyle(Paint.Style.FILL);
                _paint.setColor(Color.argb(230, 32, 38, 46));
                _tmpRect.set(tx, ty, tx + tw, ty + th);
                canvas.drawRoundRect(_tmpRect, 18f, 18f, _paint);
                _paint.setColor(Color.rgb(255, 212, 71));
                _paint.setTextSize(26f);
                _paint.setTextAlign(Paint.Align.CENTER);
                canvas.drawText("Achievement Unlocked: " + _activeToast, tx + tw * 0.5f, ty + 43f, _paint);
            }

            // Schedule next frame according to FPS cap (30 / 60 / Auto 90Hz)
            long delayMs = (_fpsMode == 0) ? 33L : (_fpsMode == 1 ? 16L : 11L);
            postInvalidateDelayed(delayMs);
        }

        private void drawCarOnRow(Canvas canvas, float startX, float startY, float ts, int row, float progress, int color) {
            float x0 = startX + 3.5f * ts;
            float x1 = startX + 14.5f * ts;
            float cx = x0 + (x1 - x0) * progress;
            float cy = startY + (row + 0.5f) * ts;
            _paint.setStyle(Paint.Style.FILL);
            _paint.setColor(color);
            canvas.drawCircle(cx, cy, ts * 0.24f, _paint);
        }

        private void drawHud(Canvas canvas, int w, int h) {
            _hudButtons.clear();
            float pad = 12f;
            float barX = _safeLeft + pad;
            float barY = _safeTop + pad;
            float availW = (w - _safeLeft - _safeRight) - pad * 2f;

            String[] labels = new String[] {
                _deleteMode ? "Mode: DELETE (X)" : "Mode: DRAW (X)",
                "Auto-Zoom: " + (_autoZoomEnabled ? "ON" : "OFF"),
                "FPS: " + (_fpsMode == 0 ? "30" : (_fpsMode == 1 ? "60" : "Auto (90Hz)")),
                "Speed: " + (_simSpeed == 0 ? "Paused" : (_simSpeed == 1 ? "1x" : "2x")),
                "SafeArea: " + (_symmetricSafeArea ? "Symmetric" : "Raw Cutout"),
                "Save + Audio Test"
            };

            float btnW = (availW - (labels.length - 1) * 10f) / labels.length;
            float btnH = 56f;

            for (int i = 0; i < labels.length; i++) {
                float bx = barX + i * (btnW + 10f);
                RectF r = new RectF(bx, barY, bx + btnW, barY + btnH);
                _hudButtons.add(r);
                _paint.setStyle(Paint.Style.FILL);
                _paint.setColor(Color.argb(225, 44, 52, 64));
                canvas.drawRoundRect(r, 12f, 12f, _paint);
                _paint.setColor(Color.WHITE);
                _paint.setTextSize(Math.min(20f, btnW * 0.11f));
                _paint.setTextAlign(Paint.Align.CENTER);
                canvas.drawText(labels[i], r.centerX(), r.centerY() + 7f, _paint);
            }

            // Status telemetry strip
            int unlockedCount = 0;
            for (boolean b : _achUnlocked) if (b) unlockedCount++;
            String status = String.format(
                "Trips: %d  |  Zoom: %.2fx (%s)  |  Input: %s  |  Achievements: %d/%d  |  Res: %dx%d (Safe L:%d R:%d)  |  dpcPlatform:%s  FLAC:%s  |  %.0f FPS",
                _tripsCompleted, _zoom, _isFocusedIn ? "Focused" : "Overview",
                _inputSourceLabel, unlockedCount, _achUnlocked.length,
                w, h, _safeLeft, _safeRight,
                (_dpcSelfTestStatus == 1 ? "OK" : "ERR"),
                (_flacDecodedOk ? "OK" : "ERR"),
                _measuredFps);

            _paint.setStyle(Paint.Style.FILL);
            _paint.setColor(Color.rgb(60, 66, 74));
            _paint.setTextSize(18f);
            _paint.setTextAlign(Paint.Align.LEFT);
            canvas.drawText(status, barX + 4f, barY + btnH + 26f, _paint);
        }
    }
}
