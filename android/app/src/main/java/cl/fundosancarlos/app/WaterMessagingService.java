package cl.fundosancarlos.app;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;
import org.json.JSONObject;

public final class WaterMessagingService extends FirebaseMessagingService {
    @Override public void onMessageReceived(RemoteMessage message) {
        try (LocalStore store = new LocalStore(this)) {
            if (!store.wantsPush() || store.token().isEmpty()) return;
            var notification = message.getNotification();
            if (notification != null) {
                PushAndroid.show(this, message.getData().getOrDefault("alerta_id", "nivel"),
                    notification.getTitle(), notification.getBody());
            }
        }
    }

    @Override public void onNewToken(String token) {
        try (LocalStore store = new LocalStore(this)) {
            String session = store.token();
            if (store.wantsPush() && !session.isEmpty()) {
                Api.request(store.origin(), "notificaciones", session, new JSONObject().put("token",token));
            }
        } catch (Exception ignored) { /* Se vuelve a sincronizar al abrir la app. */ }
    }
}
