package cl.fundosancarlos.app;

import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class LocalStore extends SQLiteOpenHelper {
    private static final String ALIAS = "san-carlos.session.v1";
    private final SharedPreferences prefs;

    LocalStore(Context context) {
        super(context, "san-carlos-cache.db", null, 1);
        prefs = context.getSharedPreferences("san-carlos", Context.MODE_PRIVATE);
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE panel (scope TEXT PRIMARY KEY, json TEXT NOT NULL)");
    }
    @Override public void onUpgrade(SQLiteDatabase db, int from, int to) {}

    String origin() { return prefs.getString("origin", ""); }
    String user() { return prefs.getString("user", ""); }
    boolean automaticPushAllowed() { return !prefs.getBoolean("push_opt_out", false); }
    void automaticPushAllowed(boolean value) { prefs.edit().putBoolean("push_opt_out", !value).apply(); }
    boolean wantsPush() { return prefs.getBoolean("push", false); }
    void wantsPush(boolean value) { prefs.edit().putBoolean("push", value).apply(); }

    void saveSession(String origin, String user, String token) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key());
        cipher.updateAAD((origin + "|" + user).getBytes(StandardCharsets.UTF_8));
        String iv = Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP);
        String encrypted = Base64.encodeToString(cipher.doFinal(token.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
        if (!prefs.edit().putString("origin", origin).putString("user", user)
                .putString("token", iv + "." + encrypted).putBoolean("push", false).commit()) {
            throw new IllegalStateException("No se pudo guardar la sesión en el teléfono.");
        }
    }

    String token() {
        String saved = prefs.getString("token", "");
        if (saved.isEmpty()) return "";
        try {
            String[] parts = saved.split("\\.", 2);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)));
            cipher.updateAAD((origin() + "|" + user()).getBytes(StandardCharsets.UTF_8));
            return new String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), StandardCharsets.UTF_8);
        } catch (Exception e) { return ""; }
    }

    private SecretKey key() throws Exception {
        synchronized (LocalStore.class) {
            KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
            ks.load(null);
            if (ks.containsAlias(ALIAS)) return (SecretKey) ks.getKey(ALIAS, null);
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            return generator.generateKey();
        }
    }

    void savePanel(JSONObject data) {
        ContentValues v = new ContentValues();
        v.put("scope", origin() + "|" + user());
        v.put("json", data.toString());
        getWritableDatabase().insertWithOnConflict("panel", null, v, SQLiteDatabase.CONFLICT_REPLACE);
    }

    JSONObject cachedPanel() {
        try (var cursor = getReadableDatabase().query("panel", new String[]{"json"}, "scope=?",
                new String[]{origin() + "|" + user()}, null, null, null)) {
            if (cursor.moveToFirst()) return new JSONObject(cursor.getString(0));
        } catch (Exception ignored) {}
        return null;
    }

    void clearSession() {
        prefs.edit().remove("token").remove("user").remove("push").apply();
        getWritableDatabase().delete("panel", null, null);
    }
}
