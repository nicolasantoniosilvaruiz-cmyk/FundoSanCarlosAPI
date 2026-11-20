package cl.fundosancarlos.app;

import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

final class Api {
    static final class Error extends IOException {
        final int status;
        Error(int status, String message) { super(message); this.status = status; }
    }

    static String origin(String input) {
        try {
            URI u = URI.create(input.trim());
            String scheme = u.getScheme(), host = u.getHost();
            if (host == null || u.getPort() == 0 || u.getPort() > 65535 || u.getRawUserInfo() != null || u.getRawQuery() != null || u.getRawFragment() != null
                || !(u.getRawPath().isEmpty() || u.getRawPath().equals("/"))) throw new IllegalArgumentException();
            if (!"https".equalsIgnoreCase(scheme)
                && !("http".equalsIgnoreCase(scheme) && BuildConfig.DEBUG && ("127.0.0.1".equals(host) || privateIpv4(host)))) {
                throw new IllegalArgumentException();
            }
            return scheme.toLowerCase(Locale.ROOT) + "://" + u.getRawAuthority();
        } catch (RuntimeException e) {
            throw new IllegalArgumentException("Ingresa la dirección del servidor sin rutas. Usa HTTPS o la IP privada del PC para la prueba.");
        }
    }

    private static boolean privateIpv4(String host) {
        String[] parts = host.split("\\.");
        if (parts.length != 4) return false;
        int[] n = new int[4];
        for (int i=0;i<4;i++) {
            if (!parts[i].matches("0|[1-9][0-9]{0,2}")) return false;
            n[i]=Integer.parseInt(parts[i]);
            if (n[i]>255) return false;
        }
        return n[0]==10 || (n[0]==172 && n[1]>=16 && n[1]<=31) || (n[0]==192 && n[1]==168);
    }

    static JSONObject request(String origin, String endpoint, String token, JSONObject payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) URI.create(origin + "/api/movil/" + endpoint + "/").toURL().openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(6000);
        connection.setReadTimeout(30000);
        connection.setRequestProperty("Accept", "application/json");
        if (token != null && !token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
        try {
            if (payload != null) {
                byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);
                connection.setRequestMethod("POST");
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(bytes.length);
                try (var out = connection.getOutputStream()) { out.write(bytes); }
            }
            int status = connection.getResponseCode();
            if (status >= 300 && status < 400) throw new Error(status, "El servidor redirigió la solicitud. Revisa la dirección configurada.");
            try (InputStream in = status < 400 ? connection.getInputStream() : connection.getErrorStream()) {
                ByteArrayOutputStream body = new ByteArrayOutputStream();
                if (in != null) {
                    byte[] buffer = new byte[4096];
                    int read;
                    while ((read = in.read(buffer)) != -1) {
                        if (body.size() + read > 262144) throw new IOException("Respuesta demasiado grande.");
                        body.write(buffer, 0, read);
                    }
                }
                JSONObject json;
                try { json = new JSONObject(body.toString(StandardCharsets.UTF_8.name())); }
                catch (Exception e) { throw new Error(status, "No se recibió una respuesta de San Carlos. Revisa la dirección y que Django esté iniciado."); }
                if (status >= 400) throw new Error(status, json.optString("error", "No se pudo completar la operación."));
                return json;
            }
        } finally { connection.disconnect(); }
    }
}
