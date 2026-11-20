package cl.fundosancarlos.app;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;

final class PushAndroid {
    static final String CHANNEL = "alertas_agua";

    static boolean configure(Context ctx) {
        if (ctx.getString(R.string.fcm_app_id).isEmpty()) return false;
        if (FirebaseApp.getApps(ctx).isEmpty()) {
            FirebaseApp.initializeApp(ctx, new FirebaseOptions.Builder()
                .setApplicationId(ctx.getString(R.string.fcm_app_id))
                .setGcmSenderId(ctx.getString(R.string.fcm_sender_id))
                .setProjectId(ctx.getString(R.string.fcm_project_id))
                .setApiKey(ctx.getString(R.string.fcm_api_key)).build());
        }
        return true;
    }

    static void createChannel(Context ctx) {
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Alertas de agua", NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription("Avisos cuando el agua baja del nivel configurado");
        channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
        ctx.getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    static boolean allowed(Context ctx) {
        if (Build.VERSION.SDK_INT >= 33 && ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            return false;
        NotificationManager manager = ctx.getSystemService(NotificationManager.class);
        NotificationChannel channel = manager.getNotificationChannel(CHANNEL);
        return manager.areNotificationsEnabled() && (channel == null || channel.getImportance() != NotificationManager.IMPORTANCE_NONE);
    }

    static void show(Context ctx, String id, String title, String body) {
        createChannel(ctx);
        if (!allowed(ctx)) return;
        Intent intent = new Intent(ctx, MainActivity.class).putExtra("pantalla","agua")
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent click = PendingIntent.getActivity(ctx, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(ctx, CHANNEL).setSmallIcon(R.drawable.ic_water)
            .setContentTitle(title).setContentText(body).setStyle(new Notification.BigTextStyle().bigText(body))
            .setCategory(Notification.CATEGORY_STATUS).setAutoCancel(true).setVisibility(Notification.VISIBILITY_PUBLIC)
            .setContentIntent(click).build();
        ctx.getSystemService(NotificationManager.class).notify("agua-" + id, 1, notification);
    }
}
