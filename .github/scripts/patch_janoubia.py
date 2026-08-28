from pathlib import Path
import os
import re

java = Path("appsrc/app/src/main/java/com/janoubia/sales/MainActivity.java")
manifest = Path("appsrc/app/src/main/AndroidManifest.xml")
gradle = Path("appsrc/app/build.gradle")

for f in (java, manifest, gradle):
    if not f.exists():
        raise SystemExit(f"Missing required project file: {f}")

build_number = int(os.environ["JAN_BUILD_NUMBER"])
text = java.read_text(encoding="utf-8")

text, timeout_count = re.subn(
    r'private\s+static\s+final\s+long\s+INACTIVITY_TIMEOUT_MS\s*=\s*[^;]+;',
    'private static final long INACTIVITY_TIMEOUT_MS = Long.MAX_VALUE / 4;',
    text,
    count=1,
)
if timeout_count != 1:
    raise SystemExit("INACTIVITY_TIMEOUT_MS was not found")

text = re.sub(
    r'(?m)^([ \t]*)scheduleInactivityLogout\s*\(\s*\)\s*;\s*$',
    r'\1// Automatic inactivity logout disabled.',
    text,
)

text = re.sub(
    r'public\s+class\s+MainActivity\s+extends\s+(?:Activity|AppCompatActivity|FragmentActivity)',
    'public class MainActivity extends FragmentActivity',
    text,
    count=1,
)

package_match = re.search(
    r'^package\s+[^;]+;\s*',
    text,
    flags=re.MULTILINE,
)
if not package_match:
    raise SystemExit("Package declaration not found")

required_imports = [
    "import androidx.fragment.app.FragmentActivity;",
    "import android.os.Build;",
    "import android.webkit.CookieManager;",
    "import android.webkit.WebSettings;",
    "import android.webkit.WebView;",
    "import android.webkit.WebViewClient;",
    "import android.Manifest;",
    "import android.content.pm.PackageManager;",
    "import android.location.LocationManager;",
]

missing = [i for i in required_imports if i not in text]
if missing:
    p = package_match.end()
    text = text[:p] + "\n" + "\n".join(missing) + "\n" + text[p:]

for start, end in [
    ("JAN_LOGIN_FIX_START", "JAN_LOGIN_FIX_END"),
    ("JAN_FINAL_FIELDS_START", "JAN_FINAL_FIELDS_END"),
    ("JAN_FINAL_METHODS_START", "JAN_FINAL_METHODS_END"),
    ("JAN_FINAL_CHECK_START", "JAN_FINAL_CHECK_END"),
    ("JAN_FINAL_RESUME_START", "JAN_FINAL_RESUME_END"),
    ("JAN_NATIVE_VERSION_BADGE_START", "JAN_NATIVE_VERSION_BADGE_END"),
]:
    text = re.sub(
        rf'\s*// {start}.*?// {end}\s*',
        '\n',
        text,
        flags=re.DOTALL,
    )

text = re.sub(
    r'^\s*(?:android\.webkit\.)?WebView\s+webView\s*=\s*findViewById\(R\.id\.webview\);\s*$',
    '',
    text,
    flags=re.MULTILINE,
)

APP_ENTRY = "https://xhpovyomlqnvuiwihhgm.supabase.co/functions/v1/janoubia-app"
text = re.sub(
    r'https://xhpovyomlqnvuiwihhgm\.supabase\.co/functions/v1/(?:janoubia-sales|janoubia-pwa|janoubia-secure|janoubia-app)',
    APP_ENTRY,
    text,
)

real_webview_pattern = (
    r'\bwebView\s*=\s*new\s+(?:android\.webkit\.)?WebView\s*\(\s*this\s*\)\s*;'
)
if not re.search(real_webview_pattern, text):
    raise SystemExit("Real WebView creation not found")

login_fix = r'''

    // JAN_LOGIN_FIX_START
    WebSettings janSettings = webView.getSettings();
    janSettings.setJavaScriptEnabled(true);
    janSettings.setDomStorageEnabled(true);
    janSettings.setDatabaseEnabled(true);
    janSettings.setJavaScriptCanOpenWindowsAutomatically(true);
    janSettings.setSupportMultipleWindows(false);
    janSettings.setLoadWithOverviewMode(true);
    janSettings.setUseWideViewPort(true);
    janSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
        janSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    }

    CookieManager janCookies = CookieManager.getInstance();
    janCookies.setAcceptCookie(true);

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
        janCookies.setAcceptThirdPartyCookies(webView, false);
    }

    janCookies.flush();

    webView.addJavascriptInterface(new Object() {

        @android.webkit.JavascriptInterface
        public String getDeviceId() {
            try {
                String id = android.provider.Settings.Secure.getString(
                        getContentResolver(),
                        android.provider.Settings.Secure.ANDROID_ID
                );
                return id == null ? "" : id;
            } catch (Throwable ignored) {
                return "";
            }
        }

        @android.webkit.JavascriptInterface
        public String getDeviceLabel() {
            try {
                String manufacturer = Build.MANUFACTURER == null
                        ? ""
                        : Build.MANUFACTURER.trim();
                String model = Build.MODEL == null
                        ? ""
                        : Build.MODEL.trim();
                String label = (manufacturer + " " + model).trim();
                return label.isEmpty() ? "Android" : label;
            } catch (Throwable ignored) {
                return "Android";
            }
        }

        @android.webkit.JavascriptInterface
        public void requestLocation() {
            runOnUiThread(() -> {
                try {
                    if (
                            Build.VERSION.SDK_INT >= 23
                            && checkSelfPermission(
                                    Manifest.permission.ACCESS_FINE_LOCATION
                            ) != PackageManager.PERMISSION_GRANTED
                            && checkSelfPermission(
                                    Manifest.permission.ACCESS_COARSE_LOCATION
                            ) != PackageManager.PERMISSION_GRANTED
                    ) {
                        requestPermissions(
                                new String[]{
                                        Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION
                                },
                                4401
                        );

                        webView.evaluateJavascript(
                                "window.__janLocError&&window.__janLocError('Ø§Ø³ÙØ­ Ø¨ØµÙØ§Ø­ÙØ© Ø§ÙÙÙÙØ¹ Ø«Ù Ø§Ø¶ØºØ· ÙØ±Ø© Ø£Ø®Ø±Ù')",
                                null
                        );
                        return;
                    }

                    LocationManager lm = (LocationManager)
                            getSystemService(
                                    android.content.Context.LOCATION_SERVICE
                            );

                    if (lm == null) {
                        webView.evaluateJavascript(
                                "window.__janLocError&&window.__janLocError('ØªØ¹Ø°Ø± ØªØ´ØºÙÙ Ø®Ø¯ÙØ© Ø§ÙÙÙÙØ¹')",
                                null
                        );
                        return;
                    }

                    String provider = lm.getBestProvider(
                            new android.location.Criteria(),
                            true
                    );

                    if (provider == null) {
                        webView.evaluateJavascript(
                                "window.__janLocError&&window.__janLocError('Ø´ØºÙÙ GPS ÙØ­Ø§ÙÙ ÙØ±Ø© Ø£Ø®Ø±Ù')",
                                null
                        );
                        return;
                    }

                    final android.location.LocationListener[] holder =
                            new android.location.LocationListener[1];

                    holder[0] = new android.location.LocationListener() {
                        @Override
                        public void onLocationChanged(
                                android.location.Location loc
                        ) {
                            try {
                                lm.removeUpdates(holder[0]);
                            } catch (Throwable ignored) {}

                            String js =
                                    "window.__janLocDone&&window.__janLocDone("
                                    + loc.getLatitude()
                                    + ","
                                    + loc.getLongitude()
                                    + ","
                                    + loc.getAccuracy()
                                    + ")";

                            webView.evaluateJavascript(js, null);
                        }

                        @Override
                        public void onProviderEnabled(String provider) {}

                        @Override
                        public void onProviderDisabled(String provider) {}

                        @Override
                        public void onStatusChanged(
                                String provider,
                                int status,
                                android.os.Bundle extras
                        ) {}
                    };

                    lm.requestLocationUpdates(
                            provider,
                            0L,
                            0f,
                            holder[0],
                            android.os.Looper.getMainLooper()
                    );

                } catch (Throwable e) {
                    webView.evaluateJavascript(
                        "window.__janLocError&&window.__janLocError('ØªØ¹Ø°Ø± ØªØ­Ø¯ÙØ¯ Ø§ÙÙÙÙØ¹Ø ØªØ£ÙØ¯ ÙÙ ØªØ´ØºÙÙ GPS')",
                        null
                    );
                }
            });
        }

    }, "JanoubiaNative");
    // JAN_LOGIN_FIX_END
'''

text, injected = re.subn(
    '(' + real_webview_pattern + ')',
    lambda m: m.group(1) + login_fix,
    text,
    count=1,
)

if injected != 1:
    raise SystemExit("Could not inject WebView/GPS/device settings")

if "onPageFinished" in text and not re.search(
    r'onPageFinished[\s\S]{0,600}CookieManager\.getInstance\(\)\.flush',
    text,
):
    text = re.sub(
        r'(public\s+void\s+onPageFinished\s*\(\s*WebView\s+\w+\s*,\s*String\s+\w+\s*\)\s*\{)',
        r'\1\n                CookieManager.getInstance().flush();\n                webView.postDelayed(() -> applyJanoubiaPageTweaks(), 700L);',
        text,
        count=1,
    )

version_badge_block = r'''
    // JAN_NATIVE_VERSION_BADGE_START
    try {
        android.widget.TextView janVersionBadge =
                new android.widget.TextView(this);

        janVersionBadge.setText(
                "\u0627\u0644\u0625\u0635\u062f\u0627\u0631 "
                + JAN_LOCAL_BUILD
        );
        janVersionBadge.setTextSize(13f);
        janVersionBadge.setTextColor(
                android.graphics.Color.rgb(108, 76, 255)
        );
        janVersionBadge.setGravity(android.view.Gravity.CENTER);
        janVersionBadge.setTypeface(
                android.graphics.Typeface.DEFAULT,
                android.graphics.Typeface.BOLD
        );
        janVersionBadge.setPadding(20, 9, 20, 9);

        android.graphics.drawable.GradientDrawable janBadgeBg =
                new android.graphics.drawable.GradientDrawable();
        janBadgeBg.setColor(
                android.graphics.Color.argb(245, 255, 255, 255)
        );
        janBadgeBg.setCornerRadius(30f);
        janBadgeBg.setStroke(
                2,
                android.graphics.Color.argb(180, 108, 76, 255)
        );
        janVersionBadge.setBackground(janBadgeBg);

        android.widget.FrameLayout.LayoutParams janBadgeParams =
                new android.widget.FrameLayout.LayoutParams(
                        android.view.ViewGroup.LayoutParams.WRAP_CONTENT,
                        android.view.ViewGroup.LayoutParams.WRAP_CONTENT
                );
        janBadgeParams.gravity =
                android.view.Gravity.BOTTOM
                        | android.view.Gravity.START;
        janBadgeParams.setMargins(18, 18, 18, 28);

        addContentView(janVersionBadge, janBadgeParams);
        janVersionBadge.setElevation(1000f);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            janVersionBadge.setTranslationZ(1000f);
        }

        janVersionBadge.bringToFront();

        janVersionBadge.postDelayed(() -> {
            try {
                janVersionBadge.setVisibility(
                        android.view.View.VISIBLE
                );
                janVersionBadge.bringToFront();
                janVersionBadge.setElevation(1000f);
            } catch (Throwable ignored) {}
        }, 1200L);

        janVersionBadge.postDelayed(() -> {
            try {
                janVersionBadge.setVisibility(
                        android.view.View.VISIBLE
                );
                janVersionBadge.bringToFront();
                janVersionBadge.setElevation(1000f);
            } catch (Throwable ignored) {}
        }, 5000L);

    } catch (Throwable ignored) {}
    // JAN_NATIVE_VERSION_BADGE_END
'''

class_match = re.search(
    r'public\s+class\s+MainActivity\s+extends\s+FragmentActivity\s*\{',
    text,
)
if not class_match:
    raise SystemExit("MainActivity declaration not found")

fields = r'''

    // JAN_FINAL_FIELDS_START
    private static final String JAN_RELEASE_API =
            "https://api.github.com/repos/sultanhosa794-stack/janoubia-sales-app/releases/latest";
    private static final int JAN_LOCAL_BUILD = __JAN_LOCAL_BUILD__;
    private static final String JAN_PREFS =
            "janoubia_update_prefs";
    private long janUpdateDownloadId = -1L;
    private String janPendingUpdateUrl = null;
    private int janPendingUpdateVersion = -1;
    private int janUpdateDialogShownFor = -1;
    // JAN_FINAL_FIELDS_END
'''

fields = fields.replace(
    "__JAN_LOCAL_BUILD__",
    str(build_number),
)

p = class_match.end()
text = text[:p] + fields + text[p:]

check_block = r'''
    // JAN_FINAL_CHECK_START
    syncJanoubiaInstalledBuildMarker();
    webView.postDelayed(() -> checkJanoubiaUpdate(), 1800L);
    webView.postDelayed(() -> applyJanoubiaPageTweaks(), 5000L);
    webView.postDelayed(() -> applyJanoubiaPageTweaks(), 8000L);
    // JAN_FINAL_CHECK_END
'''

marker = re.search(r'\bloadAppHtml\s*\(\s*\)\s*;', text)

if marker:
    end = marker.end()
    text = (
        text[:end]
        + "\n"
        + version_badge_block
        + "\n"
        + check_block
        + text[end:]
    )
elif "setContentView(root);" in text:
    text = text.replace(
        "setContentView(root);",
        "setContentView(root);\n"
        + version_badge_block
        + "\n"
        + check_block,
        1,
    )
else:
    raise SystemExit("Safe insertion point for update check not found")

resume_block = r'''
    // JAN_FINAL_RESUME_START
    if (
            janPendingUpdateUrl != null
            && (
                    Build.VERSION.SDK_INT < Build.VERSION_CODES.O
                    || getPackageManager().canRequestPackageInstalls()
            )
    ) {
        String pending = janPendingUpdateUrl;
        int pendingVersion = janPendingUpdateVersion;
        janPendingUpdateUrl = null;
        janPendingUpdateVersion = -1;

        new android.os.Handler(
                android.os.Looper.getMainLooper()
        ).postDelayed(
                () -> startJanoubiaUpdate(
                        pendingVersion,
                        pending
                ),
                500L
        );
    }
    // JAN_FINAL_RESUME_END
'''

text, resume_count = re.subn(
    r'(protected\s+void\s+onResume\s*\(\s*\)\s*\{\s*super\.onResume\s*\(\s*\)\s*;)',
    r'\1\n' + resume_block,
    text,
    count=1,
)

if resume_count != 1:
    raise SystemExit("onResume insertion point not found")

methods = r'''

    // JAN_FINAL_METHODS_START

    private android.content.SharedPreferences janPrefs() {
        return getSharedPreferences(JAN_PREFS, MODE_PRIVATE);
    }

    private long janPackageLastUpdateTime() {
        try {
            return getPackageManager()
                    .getPackageInfo(getPackageName(), 0)
                    .lastUpdateTime;
        } catch (Throwable ignored) {
            return 0L;
        }
    }

    private int janPackageBuild() {
        int best = JAN_LOCAL_BUILD;

        try {
            android.content.pm.PackageInfo pi =
                    getPackageManager()
                            .getPackageInfo(getPackageName(), 0);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                best = Math.max(
                        best,
                        (int) Math.min(
                                Integer.MAX_VALUE,
                                pi.getLongVersionCode()
                        )
                );
            } else {
                best = Math.max(best, pi.versionCode);
            }

            if (pi.versionName != null) {
                java.util.regex.Matcher m =
                        java.util.regex.Pattern
                                .compile("(\\d+)$")
                                .matcher(pi.versionName);

                if (m.find()) {
                    best = Math.max(
                            best,
                            Integer.parseInt(m.group(1))
                    );
                }
            }

        } catch (Throwable ignored) {}

        best = Math.max(
                best,
                janPrefs().getInt("confirmed_build", 0)
        );

        return best;
    }

    private void syncJanoubiaInstalledBuildMarker() {
        try {
            android.content.SharedPreferences p = janPrefs();

            int target =
                    p.getInt("pending_target_build", -1);

            long before =
                    p.getLong("pending_before_update_time", 0L);

            long now =
                    janPackageLastUpdateTime();

            if (target > 0 && now > before) {
                p.edit()
                        .putInt(
                                "confirmed_build",
                                Math.max(target, JAN_LOCAL_BUILD)
                        )
                        .remove("pending_target_build")
                        .remove("pending_before_update_time")
                        .apply();

            } else if (
                    JAN_LOCAL_BUILD
                            > p.getInt("confirmed_build", 0)
            ) {
                p.edit()
                        .putInt(
                                "confirmed_build",
                                JAN_LOCAL_BUILD
                        )
                        .apply();
            }

        } catch (Throwable ignored) {}
    }

    private void applyJanoubiaPageTweaks() {
        try {
            webView.evaluateJavascript(
                    "(function(){try{"
                    + "var target='\\u0645\\u0648\\u0638\\u0641\\u064a\\u0646 \\u0627\\u0644\\u062c\\u0646\\u0648\\u0628\\u064a\\u0629';"
                    + "var all=document.querySelectorAll('body *');"
                    + "for(var i=0;i<all.length;i++){"
                    + "var e=all[i];"
                    + "var text=(e.innerText||e.textContent||'').replace(/\\\\s+/g,' ').trim();"
                    + "if(text.indexOf(target)===-1)continue;"
                    + "var candidate=e;"
                    + "for(var p=e,step=0;p&&p!==document.body&&step<5;p=p.parentElement,step++){"
                    + "var r=p.getBoundingClientRect();"
                    + "if(r.top>=-30&&r.top<360&&r.height>=20&&r.height<=200&&r.width>=window.innerWidth*.5){candidate=p;}"
                    + "}"
                    + "candidate.style.setProperty('display','none','important');"
                    + "candidate.style.setProperty('height','0','important');"
                    + "candidate.style.setProperty('min-height','0','important');"
                    + "candidate.style.setProperty('margin','0','important');"
                    + "candidate.style.setProperty('padding','0','important');"
                    + "break;"
                    + "}"
                    + "}catch(e){}})();",
                    null
            );
        } catch (Throwable ignored) {}
    }

    private void checkJanoubiaUpdate() {
        new Thread(() -> {
            java.net.HttpURLConnection connection = null;

            try {
                java.net.URL u =
                        new java.net.URL(JAN_RELEASE_API);

                connection =
                        (java.net.HttpURLConnection)
                                u.openConnection();

                connection.setConnectTimeout(8000);
                connection.setReadTimeout(8000);
                connection.setUseCaches(false);
                connection.setRequestProperty(
                        "Cache-Control",
                        "no-cache"
                );
                connection.setRequestProperty(
                        "Pragma",
                        "no-cache"
                );
                connection.setRequestProperty(
                        "Accept",
                        "application/vnd.github+json"
                );
                connection.setRequestProperty(
                        "User-Agent",
                        "Janoubia-Sales-App"
                );

                if (connection.getResponseCode() != 200) {
                    return;
                }

                java.io.BufferedReader br =
                        new java.io.BufferedReader(
                                new java.io.InputStreamReader(
                                        connection.getInputStream(),
                                        java.nio.charset.StandardCharsets.UTF_8
                                )
                        );

                StringBuilder body = new StringBuilder();
                String line;

                while ((line = br.readLine()) != null) {
                    body.append(line);
                }

                br.close();

                java.util.regex.Matcher tag =
                        java.util.regex.Pattern
                                .compile(
                                        "\\\"tag_name\\\"\\s*:\\s*\\\"v(\\d+)\\\""
                                )
                                .matcher(body.toString());

                if (!tag.find()) return;

                int remoteVersion =
                        Integer.parseInt(tag.group(1));

                int localVersion =
                        janPackageBuild();

                if (remoteVersion <= localVersion) return;
                if (remoteVersion == janUpdateDialogShownFor) return;

                java.util.regex.Matcher asset =
                        java.util.regex.Pattern
                                .compile(
                                        "\\\"browser_download_url\\\"\\s*:\\s*\\\"([^\\\"]+\\.apk)\\\""
                                )
                                .matcher(body.toString());

                if (!asset.find()) return;

                String apkUrl =
                        asset.group(1).replace("\\/", "/");

                janUpdateDialogShownFor = remoteVersion;

                runOnUiThread(
                        () -> showJanoubiaUpdate(
                                remoteVersion,
                                apkUrl
                        )
                );

            } catch (Throwable ignored) {

            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }

        }).start();
    }

    private void showJanoubiaUpdate(
            int version,
            String apkUrl
    ) {
        if (isFinishing()) return;

        new android.app.AlertDialog.Builder(this)
                .setTitle(
                        "\u064a\u0648\u062c\u062f \u062a\u062d\u062f\u064a\u062b \u062c\u062f\u064a\u062f"
                )
                .setMessage(
                        "\u064a\u062a\u0648\u0641\u0631 \u062a\u062d\u062f\u064a\u062b \u062c\u062f\u064a\u062f \u0644\u0645\u0628\u064a\u0639\u0627\u062a \u062c\u0646\u0648\u0628\u064a\u0629 2."
                )
                .setCancelable(true)
                .setNegativeButton(
                        "\u0644\u0627\u062d\u0642\u0627\u064b",
                        null
                )
                .setPositiveButton(
                        "\u062a\u062d\u062f\u064a\u062b",
                        (dialog, which) ->
                                startJanoubiaUpdate(
                                        version,
                                        apkUrl
                                )
                )
                .show();
    }

    private void startJanoubiaUpdate(
            int version,
            String apkUrl
    ) {
        try {
            if (
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                    && !getPackageManager()
                        .canRequestPackageInstalls()
            ) {
                janPendingUpdateUrl = apkUrl;
                janPendingUpdateVersion = version;

                android.content.Intent settingsIntent =
                        new android.content.Intent(
                                android.provider.Settings
                                        .ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                android.net.Uri.parse(
                                        "package:"
                                        + getPackageName()
                                )
                        );

                startActivity(settingsIntent);
                return;
            }

            janPrefs().edit()
                    .putInt(
                            "pending_target_build",
                            version
                    )
                    .putLong(
                            "pending_before_update_time",
                            janPackageLastUpdateTime()
                    )
                    .apply();

            android.app.DownloadManager dm =
                    (android.app.DownloadManager)
                            getSystemService(
                                    android.content.Context.DOWNLOAD_SERVICE
                            );

            if (dm == null) return;

            android.app.DownloadManager.Request request =
                    new android.app.DownloadManager.Request(
                            android.net.Uri.parse(apkUrl)
                    );

            request.setTitle(
                    "\u062a\u062d\u062f\u064a\u062b \u0645\u0628\u064a\u0639\u0627\u062a \u062c\u0646\u0648\u0628\u064a\u0629 2"
            );

            request.setDescription(
                    "\u062c\u0627\u0631\u064a \u062a\u0646\u0632\u064a\u0644 \u0627\u0644\u062a\u062d\u062f\u064a\u062b..."
            );

            request.setMimeType(
                    "application/vnd.android.package-archive"
            );

            request.setNotificationVisibility(
                    android.app.DownloadManager.Request
                            .VISIBILITY_VISIBLE_NOTIFY_COMPLETED
            );

            String janUpdateFileName =
                    "Janoubia-Sales-Update-v"
                    + version
                    + ".apk";

            try {
                java.io.File janDownloads =
                        getExternalFilesDir(
                                android.os.Environment.DIRECTORY_DOWNLOADS
                        );

                if (janDownloads != null) {
                    java.io.File sameVersion =
                            new java.io.File(
                                    janDownloads,
                                    janUpdateFileName
                            );

                    if (sameVersion.exists()) {
                        sameVersion.delete();
                    }

                    java.io.File legacyUpdater =
                            new java.io.File(
                                    janDownloads,
                                    "Janoubia-Sales-Update.apk"
                            );

                    if (legacyUpdater.exists()) {
                        legacyUpdater.delete();
                    }
                }

            } catch (Throwable ignored) {}

            request.setDestinationInExternalFilesDir(
                    this,
                    android.os.Environment.DIRECTORY_DOWNLOADS,
                    janUpdateFileName
            );

            janUpdateDownloadId = dm.enqueue(request);

            final android.content.BroadcastReceiver receiver =
                    new android.content.BroadcastReceiver() {
                        @Override
                        public void onReceive(
                                android.content.Context context,
                                android.content.Intent intent
                        ) {
                            long id =
                                    intent.getLongExtra(
                                            android.app.DownloadManager
                                                    .EXTRA_DOWNLOAD_ID,
                                            -1L
                                    );

                            if (id != janUpdateDownloadId) return;

                            try {
                                android.net.Uri uri =
                                        dm.getUriForDownloadedFile(id);

                                if (uri == null) {
                                    android.widget.Toast
                                            .makeText(
                                                    MainActivity.this,
                                                    "\u062a\u0639\u0630\u0631 \u062a\u0646\u0632\u064a\u0644 \u0627\u0644\u062a\u062d\u062f\u064a\u062b. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
                                                    android.widget.Toast.LENGTH_LONG
                                            )
                                            .show();
                                    return;
                                }

                                android.content.Intent install =
                                        new android.content.Intent(
                                                android.content.Intent.ACTION_VIEW
                                        );

                                install.setDataAndType(
                                        uri,
                                        "application/vnd.android.package-archive"
                                );

                                install.addFlags(
                                        android.content.Intent
                                                .FLAG_GRANT_READ_URI_PERMISSION
                                );

                                install.addFlags(
                                        android.content.Intent
                                                .FLAG_ACTIVITY_NEW_TASK
                                );

                                startActivity(install);

                            } finally {
                                try {
                                    unregisterReceiver(this);
                                } catch (Throwable ignored) {}
                            }
                        }
                    };

            android.content.IntentFilter filter =
                    new android.content.IntentFilter(
                            android.app.DownloadManager
                                    .ACTION_DOWNLOAD_COMPLETE
                    );

            if (Build.VERSION.SDK_INT >= 33) {
                registerReceiver(
                        receiver,
                        filter,
                        android.content.Context.RECEIVER_NOT_EXPORTED
                );
            } else {
                registerReceiver(receiver, filter);
            }

        } catch (Throwable ignored) {}
    }

    // JAN_FINAL_METHODS_END
'''

last_brace = text.rfind('}')
if last_brace < 0:
    raise SystemExit("MainActivity closing brace not found")

text = text[:last_brace] + methods + "\n" + text[last_brace:]
java.write_text(text, encoding="utf-8")

m = manifest.read_text(encoding="utf-8")

manifest_match = re.search(
    r'<manifest\b[^>]*>',
    m,
    flags=re.DOTALL,
)

if not manifest_match:
    raise SystemExit("Android manifest opening tag not found")

required_permissions = [
    "android.permission.INTERNET",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
]

missing_permissions = [
    perm
    for perm in required_permissions
    if perm not in m
]

if missing_permissions:
    insertion = "".join(
        '\n    <uses-permission android:name="'
        + perm
        + '" />'
        for perm in missing_permissions
    )

    pos = manifest_match.end()
    m = m[:pos] + insertion + m[pos:]

manifest.write_text(m, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")

g, vc = re.subn(
    r'versionCode\s+\d+',
    f'versionCode {build_number}',
    g,
    count=1,
)

g, vn = re.subn(
    r'versionName\s+["\'][^"\']+["\']',
    f'versionName "2.{build_number}"',
    g,
    count=1,
)

if vc != 1 or vn != 1:
    raise SystemExit("Could not set versionCode/versionName")

gradle.write_text(g, encoding="utf-8")

final = java.read_text(encoding="utf-8")
manifest_final = manifest.read_text(encoding="utf-8")

checks = {
    "five-minute logout disabled":
        "Long.MAX_VALUE / 4" in final,

    "JavaScript enabled":
        "setJavaScriptEnabled(true)" in final,

    "DOM storage enabled":
        "setDomStorageEnabled(true)" in final,

    "cookies enabled":
        "setAcceptCookie(true)" in final,

    "secure app endpoint":
        "functions/v1/janoubia-app" in final,

    "native device id":
        "getDeviceId()" in final
        and "ANDROID_ID" in final,

    "native device label":
        "getDeviceLabel()" in final,

    "GPS native bridge":
        "requestLocation()" in final
        and "JanoubiaNative" in final,

    "GPS fine permission":
        "android.permission.ACCESS_FINE_LOCATION"
        in manifest_final,

    "GPS coarse permission":
        "android.permission.ACCESS_COARSE_LOCATION"
        in manifest_final,

    "update checker present":
        "checkJanoubiaUpdate" in final,

    "robust local build present":
        "janPackageBuild" in final
        and "confirmed_build" in final,

    "five-second header hide present":
        "5000L" in final
        and "evaluateJavascript" in final,

    "native version badge present":
        "JAN_NATIVE_VERSION_BADGE_START" in final,

    "version badge forced front":
        "bringToFront" in final
        and "setElevation(1000f)" in final,

    "unique updater filename present":
        "Janoubia-Sales-Update-v" in final,

    "legacy updater cleanup present":
        "legacyUpdater" in final,

    "install success marker present":
        "pending_before_update_time" in final,

    "page tweak helper present":
        "applyJanoubiaPageTweaks" in final,

    "update downloader present":
        "DownloadManager" in final,

    "update install permission":
        "REQUEST_INSTALL_PACKAGES" in manifest_final,

    "no broken R.id.webview":
        "R.id.webview" not in final,
}

failed = [name for name, ok in checks.items() if not ok]

for name, ok in checks.items():
    print(f"{name}: {'OK' if ok else 'FAILED'}")

if failed:
    raise SystemExit(
        "FINAL VALIDATION FAILED: "
        + ", ".join(failed)
    )

print("All Janoubia GPS/device/update checks passed.")
